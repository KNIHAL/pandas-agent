"""Tests for tool_gateway.audit — JSONL audit logging."""

import json
import threading

from tool_gateway.audit import AuditLogger


def test_record_writes_one_json_line(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    logger.record(
        tool_name="echo",
        permission="read_data",
        success=True,
        duration_ms=12.345,
    )

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["tool_name"] == "echo"
    assert entry["permission"] == "read_data"
    assert entry["success"] is True
    assert entry["duration_ms"] == 12.35 or entry["duration_ms"] == 12.34  # rounding
    assert entry["error_type"] is None
    assert entry["error_message"] is None
    assert "ts" in entry


def test_record_includes_error_fields_on_failure(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    logger.record(
        tool_name="echo",
        permission="read_data",
        success=False,
        duration_ms=1.0,
        error_type="TIMEOUT",
        error_message="too slow",
    )

    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert entry["success"] is False
    assert entry["error_type"] == "TIMEOUT"
    assert entry["error_message"] == "too slow"


def test_record_includes_extra_when_provided(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    logger.record(
        tool_name="echo",
        permission="read_data",
        success=True,
        duration_ms=1.0,
        extra={"truncated": True},
    )

    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert entry["extra"] == {"truncated": True}


def test_record_omits_extra_key_when_not_provided(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    logger.record(tool_name="echo", permission="read_data", success=True, duration_ms=1.0)

    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert "extra" not in entry


def test_multiple_records_append_as_separate_lines(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    for i in range(5):
        logger.record(tool_name=f"tool_{i}", permission="read_data", success=True, duration_ms=1.0)

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 5
    for i, line in enumerate(lines):
        assert json.loads(line)["tool_name"] == f"tool_{i}"


def test_creates_parent_directory_if_missing(tmp_path):
    log_path = tmp_path / "nested" / "dir" / "audit.jsonl"
    logger = AuditLogger(log_path)

    logger.record(tool_name="echo", permission="read_data", success=True, duration_ms=1.0)

    assert log_path.exists()


def test_concurrent_writes_do_not_corrupt_or_lose_lines(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    def write_many(start: int) -> None:
        for i in range(start, start + 20):
            logger.record(tool_name=f"tool_{i}", permission="read_data", success=True, duration_ms=1.0)

    threads = [threading.Thread(target=write_many, args=(i * 20,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 100
    # every line must be valid, complete JSON — proves no interleaved writes
    for line in lines:
        json.loads(line)
