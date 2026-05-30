#!/usr/bin/env python3
"""Summarize planned vs actual agent workload for token balancing."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TODO_PATH = ROOT / "TODO.md"
REPORT_ROOT = ROOT / "reports" / "agent_pipeline"
HISTORY_PATH = ROOT / "logs" / "agent_workload_history.csv"

AGENT_TAGS = ("cursor", "agy", "codex", "gemini", "manual")
TAG_RE = re.compile(r"\[(cursor|agy|codex|gemini)\]", re.IGNORECASE)
TODO_LABEL_RE = re.compile(r"`\[(Cursor|AGY|Gemini|Either)\]`", re.IGNORECASE)
OPEN_ITEM_RE = re.compile(r"^- \[([ xX])\]\s+(.*)$")


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def parse_todo(path: Path) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {
        agent: {"open": 0, "done": 0} for agent in ("cursor", "agy", "gemini", "either", "unlabeled")
    }
    if not path.is_file():
        return counts

    for line in path.read_text().splitlines():
        m = OPEN_ITEM_RE.match(line)
        if not m:
            continue
        done = m.group(1).lower() == "x"
        body = m.group(2)
        label_m = TODO_LABEL_RE.search(body)
        if label_m:
            agent = label_m.group(1).lower()
        elif "[agy]" in body.lower() and "검토" in body:
            agent = "agy"
        else:
            agent = "unlabeled"
        key = "done" if done else "open"
        counts[agent][key] += 1
    return counts


def git_commit_stats(since: str | None) -> dict[str, dict[str, float]]:
    commit_sep = "@@@COMMIT@@@"
    args = ["log", "--numstat", f"--format={commit_sep}%n%H%x00%s", "--no-merges"]
    if since:
        args.append(f"--since={since}")
    try:
        raw = _git(*args)
    except subprocess.CalledProcessError:
        return {a: {"commits": 0, "files": 0, "lines_added": 0, "lines_deleted": 0} for a in AGENT_TAGS}

    stats: dict[str, dict[str, float]] = defaultdict(
        lambda: {"commits": 0, "files": 0, "lines_added": 0, "lines_deleted": 0}
    )
    unlabeled = {"commits": 0, "files": 0, "lines_added": 0, "lines_deleted": 0}

    for block in raw.split(commit_sep) if raw else []:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        header = lines[0]
        if "\x00" not in header:
            continue
        _, subject = header.split("\x00", 1)
        tag_m = TAG_RE.search(subject)
        agent = tag_m.group(1).lower() if tag_m else None

        added = deleted = files = 0
        for ln in lines[1:]:
            parts = ln.split("\t")
            if len(parts) != 3:
                continue
            a, d, _path = parts
            if a == "-" or d == "-":
                continue
            files += 1
            added += int(a)
            deleted += int(d)

        bucket = stats[agent] if agent else unlabeled
        bucket["commits"] += 1
        bucket["files"] += files
        bucket["lines_added"] += added
        bucket["lines_deleted"] += deleted

    stats["unlabeled"] = unlabeled
    return dict(stats)


def codex_review_runs(since: str | None = None) -> int:
    """Count completed Codex reviews (one NEXT_TODO.codex.md per invocation)."""
    if not REPORT_ROOT.is_dir():
        return 0
    count = 0
    for path in REPORT_ROOT.glob("*/NEXT_TODO.codex.md"):
        if since:
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                if since_dt.tzinfo is None:
                    since_dt = since_dt.replace(tzinfo=timezone.utc)
                if mtime < since_dt:
                    continue
            except ValueError:
                pass
        count += 1
    return count


def pipeline_runs() -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    if not REPORT_ROOT.is_dir():
        return dict(counts)
    for packet in REPORT_ROOT.glob("*/review_packet.md"):
        text = packet.read_text(errors="replace")
        impl = "unknown"
        for line in text.splitlines():
            if line.startswith("## Implementation Agent"):
                continue
            if impl == "unknown" and line.strip() and not line.startswith("#"):
                impl = line.strip().lower()
                break
        counts[impl] += 1
    return dict(counts)


def pct(part: float, total: float) -> float:
    return round(100.0 * part / total, 1) if total else 0.0


def build_report(since: str | None) -> dict:
    todo = parse_todo(TODO_PATH)
    git_stats = git_commit_stats(since)
    pipeline = pipeline_runs()

    planned_open = sum(todo[a]["open"] for a in todo)
    planned_by_agent = {
        a: todo[a]["open"] for a in ("cursor", "agy", "gemini", "either", "unlabeled")
    }

    agents_all = [*AGENT_TAGS, "unlabeled"]
    git_commits_total = sum(git_stats.get(a, {}).get("commits", 0) for a in agents_all)
    git_lines_total = sum(
        git_stats.get(a, {}).get("lines_added", 0) + git_stats.get(a, {}).get("lines_deleted", 0)
        for a in agents_all
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "since": since,
        "planned_todo_open": planned_by_agent,
        "planned_todo_open_total": planned_open,
        "planned_todo_pct": {
            k: pct(v, planned_open) for k, v in planned_by_agent.items() if planned_open
        },
        "todo_done_open": {a: todo[a] for a in todo},
        "git": git_stats,
        "git_commit_share_pct": {
            a: pct(git_stats.get(a, {}).get("commits", 0), git_commits_total) for a in agents_all
        },
        "git_line_share_pct": {
            a: pct(
                git_stats.get(a, {}).get("lines_added", 0)
                + git_stats.get(a, {}).get("lines_deleted", 0),
                git_lines_total,
            )
            for a in agents_all
        },
        "pipeline_implementation_agent_runs": pipeline,
        "codex_review_runs_total": codex_review_runs(),
        "codex_review_runs_since": codex_review_runs(since) if since else None,
    }


def print_human(report: dict) -> None:
    print("=== Agent workload report ===")
    print(f"Generated: {report['generated_at']}")
    if report.get("since"):
        print(f"Git since: {report['since']}")

    print("\n-- Planned (TODO open items) --")
    for agent, n in sorted(report["planned_todo_open"].items(), key=lambda x: -x[1]):
        if n:
            pct_v = report["planned_todo_pct"].get(agent, 0)
            print(f"  {agent:10} {n:3} items  ({pct_v}%)")

    print("\n-- Actual (git commits by message tag [cursor]/[agy]/...) --")
    for agent in (*AGENT_TAGS, "unlabeled"):
        g = report["git"].get(agent, {})
        if not g.get("commits"):
            continue
        print(
            f"  {agent:10} commits={int(g['commits']):3}  "
            f"lines+/-={int(g['lines_added'])+int(g['lines_deleted']):5}  "
            f"({report['git_commit_share_pct'].get(agent, 0)}% commits, "
            f"{report['git_line_share_pct'].get(agent, 0)}% lines)"
        )

    if report["pipeline_implementation_agent_runs"]:
        print("\n-- Pipeline runs (review_packet implementation agent) --")
        for agent, n in report["pipeline_implementation_agent_runs"].items():
            print(f"  {agent:10} {n} runs")

    codex_total = report.get("codex_review_runs_total", 0)
    codex_since = report.get("codex_review_runs_since")
    if codex_total:
        print("\n-- Codex reviews (NEXT_TODO.codex.md count; target ~15-20% of passes) --")
        print(f"  all_time     {codex_total} runs")
        if codex_since is not None and report.get("since"):
            print(f"  since filter {codex_since} runs  (git --since={report['since']})")
        git_commits = sum(
            report["git"].get(a, {}).get("commits", 0)
            for a in (*AGENT_TAGS, "unlabeled")
        )
        if git_commits:
            print(
                f"  ratio        {pct(codex_since or codex_total, git_commits)}% "
                f"codex runs / git commits (rough)"
            )
        print("  Tip: use SKIP_CODEX=1 for follow-ups — docs/codex_review_policy.md")

    print("\nTip: tag commits e.g. `feat(test): golden backtest [agy]`")
    print("     re-run: PYTHONPATH=. .venv/bin/python scripts/agent_workload_report.py --record")


def append_history(report: dict) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not HISTORY_PATH.is_file()
    row = {
        "timestamp": report["generated_at"],
        "since": report.get("since") or "",
        "todo_open_cursor": report["planned_todo_open"].get("cursor", 0),
        "todo_open_agy": report["planned_todo_open"].get("agy", 0),
        "git_commits_cursor": int(report["git"].get("cursor", {}).get("commits", 0)),
        "git_commits_agy": int(report["git"].get("agy", {}).get("commits", 0)),
        "git_lines_cursor": int(report["git"].get("cursor", {}).get("lines_added", 0))
        + int(report["git"].get("cursor", {}).get("lines_deleted", 0)),
        "git_lines_agy": int(report["git"].get("agy", {}).get("lines_added", 0))
        + int(report["git"].get("agy", {}).get("lines_deleted", 0)),
    }
    with HISTORY_PATH.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            w.writeheader()
        w.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", default="2026-05-01", help="Git log start (default: 2026-05-01)")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    parser.add_argument(
        "--record",
        action="store_true",
        help="Append snapshot to logs/agent_workload_history.csv",
    )
    args = parser.parse_args()

    report = build_report(args.since)
    if args.record:
        append_history(report)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_human(report)


if __name__ == "__main__":
    main()
