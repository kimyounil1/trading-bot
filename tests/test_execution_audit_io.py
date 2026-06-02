from pathlib import Path

import pandas as pd

from src.execution_audit_io import (
    EXECUTION_AUDIT_COLUMNS,
    normalize_execution_audit_file,
    read_execution_audit_csv,
)


def test_read_execution_audit_csv_maps_legacy_and_extended_rows(tmp_path: Path) -> None:
    path = tmp_path / "execution_audit.csv"
    path.write_text(
        "timestamp,event_type,ticker,action,status,reason,profile_name,regime,signal,ai_score,llm_verdict\n"
        "2026-06-01T10:00:00,SKIP_BUY,AAA,BUY,SKIPPED,old skip,PRO,NEU,BUY,0.5,ACCEPT: ok\n"
        "2026-06-01T11:00:00,SKIP_BUY,BBB,BUY,SKIPPED,rank ai gate blocked,PRO,NEU,BUY,0.6,REJECT: no,0.61,0.72\n",
        encoding="utf-8",
    )

    df = read_execution_audit_csv(path)

    assert list(df.columns) == list(EXECUTION_AUDIT_COLUMNS)
    assert df.loc[0, "llm_verdict"] == "ACCEPT: ok"
    assert df.loc[0, "rank_ai_score"] is None
    assert df.loc[1, "rank_ai_score"] == "0.61"
    assert df.loc[1, "rank_ai_percentile"] == "0.72"


def test_normalize_execution_audit_file_rewrites_header(tmp_path: Path) -> None:
    path = tmp_path / "execution_audit.csv"
    path.write_text(
        "timestamp,event_type,ticker,action,status,reason\n"
        "2026-06-01T10:00:00,SKIP_BUY,AAA,BUY,SKIPPED,reason\n",
        encoding="utf-8",
    )

    normalize_execution_audit_file(path)
    header = path.read_text(encoding="utf-8").splitlines()[0]

    assert header == ",".join(EXECUTION_AUDIT_COLUMNS)


def test_log_execution_audit_handles_empty_existing_file(tmp_path, monkeypatch) -> None:
    from src import logger

    audit_path = tmp_path / "execution_audit.csv"
    audit_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(logger, "EXECUTION_AUDIT_LOG_PATH", str(audit_path))

    logger.log_execution_audit(
        event_type="SKIP_BUY",
        ticker="AAA",
        action="BUY",
        status="SKIPPED",
        reason="test",
    )

    assert audit_path.stat().st_size > 0
    first_line = audit_path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("timestamp,")


def test_normalize_execution_audit_file_readable_by_pandas(tmp_path: Path) -> None:
    path = tmp_path / "execution_audit.csv"
    path.write_text(
        "timestamp,event_type,ticker,action,status,reason\n"
        "2026-06-01T10:00:00,SKIP_BUY,AAA,BUY,SKIPPED,reason\n",
        encoding="utf-8",
    )

    normalize_execution_audit_file(path)
    df = pd.read_csv(path)

    assert list(df.columns) == list(EXECUTION_AUDIT_COLUMNS)
    assert df.loc[0, "ticker"] == "AAA"
    assert pd.isna(df.loc[0, "rank_ai_score"])


def test_normalize_mixed_legacy_header_and_trailing_rank_rows(tmp_path: Path) -> None:
    path = tmp_path / "execution_audit.csv"
    path.write_text(
        "timestamp,event_type,ticker,action,status,reason,profile_name,regime,signal,ai_score,llm_verdict\n"
        "2026-06-01T10:00:00,SKIP_BUY,AAA,BUY,SKIPPED,legacy only,PRO,NEU,BUY,0.5,ACCEPT: ok\n"
        "2026-06-01T11:00:00,SKIP_BUY,BBB,BUY,SKIPPED,rank blocked,PRO,NEU,BUY,0.6,REJECT: no,0.61,0.72\n",
        encoding="utf-8",
    )

    normalize_execution_audit_file(path)
    df = pd.read_csv(path)

    assert list(df.columns) == list(EXECUTION_AUDIT_COLUMNS)
    assert df.loc[0, "llm_verdict"] == "ACCEPT: ok"
    assert pd.isna(df.loc[0, "rank_ai_score"])
    assert df.loc[1, "rank_ai_score"] == 0.61
    assert df.loc[1, "rank_ai_percentile"] == 0.72

    reread = read_execution_audit_csv(path)
    assert reread.loc[1, "rank_ai_percentile"] == "0.72"
