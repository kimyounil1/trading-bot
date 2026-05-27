from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


def resolve_dump_bin_script(
    dump_bin_script: str | Path | None = None,
    qlib_repo_dir: str | Path | None = None,
) -> Path:
    if dump_bin_script is not None:
        path = Path(dump_bin_script).expanduser().resolve()
    elif qlib_repo_dir is not None:
        path = Path(qlib_repo_dir).expanduser().resolve() / "scripts" / "dump_bin.py"
    else:
        raise ValueError("Provide dump_bin_script or qlib_repo_dir")

    if not path.exists():
        raise FileNotFoundError(f"Qlib dump_bin.py not found: {path}")

    return path


def build_dump_bin_command(
    *,
    dump_bin_script: str | Path,
    csv_dir: str | Path,
    qlib_dir: str | Path,
    python_bin: str = sys.executable,
    freq: str = "day",
    include_fields: str = "open,high,low,close,volume,factor",
    date_field_name: str = "datetime",
    symbol_field_name: str = "instrument",
) -> list[str]:
    return [
        python_bin,
        str(Path(dump_bin_script)),
        "dump_all",
        "--data_path",
        str(Path(csv_dir)),
        "--qlib_dir",
        str(Path(qlib_dir)),
        "--freq",
        freq,
        "--date_field_name",
        date_field_name,
        "--symbol_field_name",
        symbol_field_name,
        "--include_fields",
        include_fields,
    ]


def run_dump_bin_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert qlib-ready CSVs into a Qlib binary dataset with dump_bin.py."
    )
    parser.add_argument(
        "--csv-dir",
        default="logs/baselines/current_strategy/qlib_ready",
        help="Directory containing qlib-ready CSV files.",
    )
    parser.add_argument(
        "--qlib-dir",
        required=True,
        help="Target directory for the generated Qlib binary dataset.",
    )
    parser.add_argument(
        "--dump-bin-script",
        default=None,
        help="Full path to Qlib's scripts/dump_bin.py.",
    )
    parser.add_argument(
        "--qlib-repo-dir",
        default=None,
        help="Path to a local Qlib repository clone. Used to resolve scripts/dump_bin.py.",
    )
    parser.add_argument(
        "--python-bin",
        default=sys.executable,
        help="Python executable used to run dump_bin.py.",
    )
    parser.add_argument(
        "--freq",
        default="day",
        help="Frequency passed to dump_bin.py.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved command without executing it.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dump_bin_script = resolve_dump_bin_script(
        dump_bin_script=args.dump_bin_script,
        qlib_repo_dir=args.qlib_repo_dir,
    )

    csv_dir = Path(args.csv_dir).expanduser().resolve()
    if not csv_dir.exists():
        raise FileNotFoundError(f"qlib-ready CSV directory not found: {csv_dir}")

    qlib_dir = Path(args.qlib_dir).expanduser().resolve()
    qlib_dir.parent.mkdir(parents=True, exist_ok=True)

    command = build_dump_bin_command(
        dump_bin_script=dump_bin_script,
        csv_dir=csv_dir,
        qlib_dir=qlib_dir,
        python_bin=args.python_bin,
        freq=args.freq,
    )

    print("Resolved Qlib dump command:")
    print(shlex.join(command))

    if args.dry_run:
        return

    run_dump_bin_command(command)
    print(f"Generated Qlib dataset at {qlib_dir}")


if __name__ == "__main__":
    main()
