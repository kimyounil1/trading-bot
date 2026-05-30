#!/usr/bin/env python3
"""Agent review orchestration (Cursor-first, optional Gemini CLI implementer).

Default usage: implement in Cursor, then --run-codex-review only.
Optional: --run-gemini for legacy headless Gemini CLI implementation.

This script does not invoke Cursor automatically. It collects review packets and
can run Codex in read-only mode against them.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "reports" / "agent_pipeline"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the agent review pipeline (Cursor-first; optional --run-gemini)."
    )
    task = parser.add_mutually_exclusive_group()
    task.add_argument("--task", help="Task prompt to give Gemini CLI.")
    task.add_argument("--task-file", type=Path, help="Path to a task prompt file.")
    parser.add_argument("--run-id", help="Stable run id. Defaults to timestamp.")
    parser.add_argument(
        "--run-gemini",
        action="store_true",
        help="Run Gemini CLI headlessly before generating the review packet.",
    )
    parser.add_argument(
        "--run-codex-review",
        action="store_true",
        help="Run Codex in read-only mode against the generated review packet.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=1,
        help="Maximum number of Gemini -> Codex iterations. Default 1.",
    )
    parser.add_argument(
        "--continue-from-codex-todo",
        type=Path,
        help="Path to a Codex-generated TODO file to use as the next Gemini task.",
    )
    parser.add_argument(
        "--scoped-review",
        action="store_true",
        default=True,
        help="Use scoped Codex review (default: True). Avoids full diff on large changes.",
    )
    parser.add_argument(
        "--max-changed-files",
        type=int,
        default=10,
        help="Stop loop if changed file count exceeds this threshold. Default 10.",
    )
    parser.add_argument(
        "--gemini-approval-mode",
        default="auto_edit",
        choices=["default", "auto_edit", "plan", "yolo"],
        help="Gemini CLI approval mode. Avoid yolo unless externally sandboxed.",
    )
    parser.add_argument("--gemini-model", help="Optional Gemini model name.")
    parser.add_argument("--codex-model", help="Optional Codex model name.")
    parser.add_argument(
        "--codex-reasoning-effort",
        default="low",
        choices=["low", "medium", "high"],
        help="Reasoning effort for Codex model. Default 'low' to save tokens.",
    )
    parser.add_argument(
        "--codex-timeout-seconds",
        type=int,
        default=240,
        help="Timeout for the Codex review step.",
    )
    parser.add_argument(
        "--ignore-artifacts",
        action="store_true",
        help="Allow Codex review when models/logs are in the diff (pass closure).",
    )
    parser.add_argument(
        "--balanced-pass",
        action="store_true",
        help="Run AGY pytest slice, then post-workflow + Codex scoped review.",
    )
    parser.add_argument(
        "--agy-prompt",
        type=Path,
        default=Path("prompts/agy/phase20_portfolio_gate.md"),
        help="AGY task file copied into the run directory (with --balanced-pass).",
    )
    parser.add_argument(
        "--agy-test-paths",
        default="tests/test_portfolio_backtest_gate.py",
        help="Comma-separated pytest paths for the AGY slice.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned commands without running Gemini, Codex, or tests.",
    )
    return parser.parse_args()


def shell_join(args: list[str]) -> str:
    return " ".join(shlex.quote(str(arg)) for arg in args)


def read_task(args: argparse.Namespace) -> str:
    if args.task:
        return args.task
    if args.task_file:
        return args.task_file.read_text(encoding="utf-8")
    return ""


def run_command(
    args: list[str],
    *,
    log_path: Path,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
    stdout_copy_path: Path | None = None,
    dry_run: bool = False,
) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command_text = shell_join(args)
    if dry_run:
        log_path.write_text(f"$ {command_text}\nDRY RUN\n", encoding="utf-8")
        print(f"[dry-run] {command_text}")
        return 0

    result = subprocess.run(
        args,
        cwd=ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        check=False,
    )
    if stdout_copy_path is not None:
        stdout_copy_path.write_text(result.stdout, encoding="utf-8")
    log_path.write_text(
        "\n".join(
            [
                f"$ {command_text}",
                f"exit_code={result.returncode}",
                "",
                "## stdout",
                result.stdout,
                "",
                "## stderr",
                result.stderr,
            ]
        ),
        encoding="utf-8",
    )
    return result.returncode


def gemini_prompt(task_text: str) -> str:
    return f"""You are Gemini CLI implementing work in this trading-bot repository.

Task:
{task_text}

Follow GEMINI.md. Do not commit, push, deploy, edit secrets, or place live
trades. When done, leave a concise handoff summary with changed files, tests
run, tests not run, assumptions, and areas Codex should review carefully.
"""


def codex_prompt(packet_path: Path, todo_path: Path) -> str:
    return f"""Review the implementation work using this packet:
{packet_path}

Follow AGENTS.md (Codex review-only section) and docs/agent_review_harness.md.
You are the reviewer/planner, not the implementation agent. Do not edit files.
Lead with findings, verify the test logs, identify residual risk, and produce a
concrete next plan for Cursor (or Gemini CLI if the packet says implementation_agent=gemini).

Label tasks with [Cursor], [Gemini], or [Either] when helpful.

At the end, include a section titled exactly:
# NEXT_TODO

That section should be suitable to save as:
{todo_path}
"""


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def check_stop_conditions(
    out_dir: Path,
    max_changed_files: int,
    history: list[dict],
    *,
    ignore_artifacts: bool = False,
) -> str | None:
    changed_files_path = out_dir / "changed_files.txt"
    if changed_files_path.exists():
        changed_files = changed_files_path.read_text(encoding="utf-8").splitlines()
        if len(changed_files) > max_changed_files:
            return f"Too many changed files: {len(changed_files)} > {max_changed_files}"

        artifacts = [
            f
            for f in changed_files
            if any(p in f for p in ["models/", "logs/", "reports/", ".pytest_cache/"])
        ]
        if artifacts and not ignore_artifacts:
            return f"Generated artifacts detected in diff (excluded from review loop): {artifacts}"

        sensitive = [
            f
            for f in changed_files
            if f == ".env"
            or "secret" in f.lower()
            or "config/portfolio_config.json" in f
            or f.startswith(".git/")
        ]
        if sensitive:
            return f"Sensitive files touched: {sensitive}"

    summary_path = out_dir / "summary.json"
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if summary.get("overall_status") == "fail":
                curr_fail = (
                    summary.get("gemini_review_harness_exit_code"),
                    summary.get("runtime_harness_exit_code"),
                )
                if history:
                    last_summary_path = Path(history[-1]["output_dir"]) / "summary.json"
                    if last_summary_path.exists():
                        last_summary = json.loads(last_summary_path.read_text(encoding="utf-8"))
                        last_fail = (
                            last_summary.get("gemini_review_harness_exit_code"),
                            last_summary.get("runtime_harness_exit_code"),
                        )
                        if curr_fail == last_fail and any(c != 0 and c is not None for c in curr_fail):
                            return f"Same failing check twice (exit codes {curr_fail})"
        except (json.JSONDecodeError, KeyError):
            pass

    return None


def main() -> int:
    args = parse_args()
    base_run_id = args.run_id or dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    
    task_text = read_task(args)
    if args.continue_from_codex_todo:
        if args.continue_from_codex_todo.exists():
            task_text = args.continue_from_codex_todo.read_text(encoding="utf-8")
        else:
            print(f"Codex TODO file not found: {args.continue_from_codex_todo}", file=sys.stderr)
            return 2

    if args.run_gemini and not task_text.strip():
        print("--run-gemini requires --task, --task-file, or --continue-from-codex-todo", file=sys.stderr)
        return 2
    if args.gemini_approval_mode == "yolo":
        print("Refusing Gemini yolo mode in this orchestrator.", file=sys.stderr)
        return 2

    if args.balanced_pass:
        args.run_codex_review = True
        args.ignore_artifacts = True
        pre_dir = REPORT_ROOT / (args.run_id or dt.datetime.now().strftime("%Y%m%dT%H%M%S"))
        pre_dir.mkdir(parents=True, exist_ok=True)
        if args.agy_prompt.is_file():
            (pre_dir / "AGY_TASK.md").write_text(
                args.agy_prompt.read_text(encoding="utf-8"), encoding="utf-8"
            )
        agy_env = os.environ.copy()
        agy_env["AGY_PROMPT"] = str(args.agy_prompt)
        agy_env["AGY_TEST_PATHS"] = args.agy_test_paths.replace(",", " ")
        print("--- Balanced pass: AGY pytest slice ---")
        agy_code = run_command(
            ["bash", "scripts/run_agy_slice.sh"],
            log_path=pre_dir / "agy_slice.log",
            env=agy_env,
            dry_run=args.dry_run,
        )
        if agy_code != 0:
            print(f"AGY slice failed with exit code {agy_code}", file=sys.stderr)
            return agy_code
        os.environ.setdefault("IMPLEMENTATION_AGENT", "cursor+agy")

    history: list[dict] = []
    
    for i in range(args.max_iterations):
        iteration_run_id = f"{base_run_id}_it{i}" if args.max_iterations > 1 else base_run_id
        out_dir = REPORT_ROOT / iteration_run_id
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n--- Iteration {i+1}/{args.max_iterations} (Run ID: {iteration_run_id}) ---")
        (out_dir / "TASK.md").write_text(task_text, encoding="utf-8")

        gemini_code = None
        if args.run_gemini:
            gemini_args = [
                "gemini",
                "--skip-trust",
                "--approval-mode",
                args.gemini_approval_mode,
                "--prompt",
                gemini_prompt(task_text),
            ]
            if args.gemini_model:
                gemini_args[1:1] = ["--model", args.gemini_model]
            gemini_code = run_command(
                gemini_args,
                log_path=out_dir / "gemini_cli.log",
                dry_run=args.dry_run,
            )
        elif args.dry_run:
            print("[dry-run] skipping Gemini CLI; no --run-gemini flag")

        env = os.environ.copy()
        env["RUN_ID"] = iteration_run_id
        if args.run_gemini:
            env["IMPLEMENTATION_AGENT"] = "gemini"
        else:
            env.setdefault("IMPLEMENTATION_AGENT", "cursor")
        post_code = run_command(
            ["bash", "scripts/run_cursor_post_workflow.sh"],
            log_path=out_dir / "post_workflow_command.log",
            env=env,
            dry_run=args.dry_run,
        )

        # Check stop conditions after Gemini + Post-workflow
        stop_reason = check_stop_conditions(
            out_dir,
            args.max_changed_files,
            history,
            ignore_artifacts=args.ignore_artifacts,
        )
        if stop_reason:
            print(f"STOP CONDITION: {stop_reason}")
            break

        codex_code = None
        codex_output = out_dir / "CODEX_REVIEW_AND_TODO.md"
        codex_todo = out_dir / "NEXT_TODO.codex.md"
        if args.run_codex_review:
            packet_path = out_dir / "review_packet.md"
            if args.scoped_review:
                # Scoped review: prioritize the packet and avoid --uncommitted on artifacts
                codex_args = [
                    "codex",
                    "--ask-for-approval", "never",
                    "--sandbox", "read-only",
                    "review",
                    str(packet_path),
                ]
            else:
                codex_args = [
                    "codex",
                    "--ask-for-approval", "never",
                    "--sandbox", "read-only",
                    "review",
                    "--uncommitted",
                ]
            
            if args.codex_model:
                codex_args.extend(["--model", args.codex_model])
            
            # Pass reasoning effort override to Codex (defaults to 'low' to save tokens)
            codex_args.extend(["-c", f"model_reasoning_effort=\"{args.codex_reasoning_effort}\""])
            
            try:
                codex_code = run_command(
                    codex_args,
                    log_path=out_dir / "codex_review_command.log",
                    timeout=args.codex_timeout_seconds,
                    stdout_copy_path=codex_output,
                    dry_run=args.dry_run,
                )
            except subprocess.TimeoutExpired:
                codex_code = 124
                timeout_message = (
                    f"Codex review timed out after {args.codex_timeout_seconds} seconds.\n"
                    f"Review packet remains available at {packet_path}\n"
                )
                (out_dir / "codex_review_command.log").write_text(timeout_message, encoding="utf-8")
                codex_output.write_text(timeout_message, encoding="utf-8")
                print(f"STOP CONDITION: Codex review timeout")
                break

            if codex_code == 0 and codex_output.exists():
                # Extract TODO for next iteration
                review_content = codex_output.read_text(encoding="utf-8")
                todo_marker = None
                for marker in ("# NEXT_TODO\n", "# NEXT_TODO for Cursor\n", "# NEXT_TODO for Gemini CLI\n"):
                    if marker in review_content:
                        todo_marker = marker
                        break
                if todo_marker:
                    todo_content = review_content.split(todo_marker)[-1].strip()
                    codex_todo.write_text(todo_content, encoding="utf-8")
                    task_text = todo_content  # Feed into next iteration
                else:
                    # If no NEXT_TODO section, we might want to stop or use the whole output
                    codex_todo.write_text(review_content, encoding="utf-8")
        elif args.dry_run:
            print("[dry-run] skipping Codex review; no --run-codex-review flag")

        summary = {
            "run_id": iteration_run_id,
            "output_dir": str(out_dir),
            "gemini_exit_code": gemini_code,
            "post_workflow_exit_code": post_code,
            "codex_review_exit_code": codex_code,
            "review_packet": str(out_dir / "review_packet.md"),
            "draft_todo": str(out_dir / "NEXT_TODO.md"),
            "codex_todo": str(codex_todo) if codex_todo.exists() else None,
        }
        write_json(out_dir / "orchestrator_summary.json", summary)
        history.append(summary)

        if not args.run_codex_review:
            # If we don't run codex, we can't get the next task automatically
            break
        if codex_code != 0:
            print(f"Codex review failed with exit code {codex_code}. Stopping loop.")
            break

    last_out_dir = Path(history[-1]["output_dir"]) if history else out_dir
    print(f"\nFinal Orchestrator output: {last_out_dir}")
    if history:
        last_codex_todo = Path(history[-1]["codex_todo"]) if history[-1].get("codex_todo") else None
        if last_codex_todo and last_codex_todo.exists():
            print(f"Last Codex TODO: {last_codex_todo}")

    exit_codes = []
    for h in history:
        exit_codes.extend([h["gemini_exit_code"], h["post_workflow_exit_code"], h["codex_review_exit_code"]])
    exit_codes = [code for code in exit_codes if code is not None]
    return 1 if any(code != 0 for code in exit_codes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
