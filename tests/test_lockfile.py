import pytest
from pathlib import Path

from flock.lockfile import (
    read_lockfile,
    write_lockfile,
    assert_lockfile_not_modified,
    _enforce_read_only_at_install_time,
)


def test_enforce_read_only_at_install_time(tmp_path):
    lockfile_path = tmp_path / "flock.lock"
    with pytest.raises(RuntimeError, match="read-only during"):
        _enforce_read_only_at_install_time(lockfile_path)


def test_write_and_read_lockfile_roundtrip(tmp_path):
    lockfile_path = tmp_path / "flock.lock"
    data = {
        "meta": {
            "generated_by": "flock resolve",
            "verify_level": "checksum",
            "timestamp": "2026-04-24T11:00:00Z",
        },
        "package": [
            {
                "name": "curl",
                "version": "7.88.1-10+deb12u5",
                "architecture": "amd64",
                "sha256": "abc123",
                "url": "https://example.com/curl.deb",
            }
        ],
    }
    write_lockfile(lockfile_path, data)
    loaded = read_lockfile(lockfile_path)
    assert loaded["meta"]["generated_by"] == "flock resolve"
    assert loaded["meta"]["verify_level"] == "checksum"
    assert len(loaded["package"]) == 1
    assert loaded["package"][0]["name"] == "curl"
    assert loaded["package"][0]["sha256"] == "abc123"


def test_read_lockfile_missing_raises(tmp_path):
    lockfile_path = tmp_path / "flock.lock"
    with pytest.raises(FileNotFoundError, match="flock resolve"):
        read_lockfile(lockfile_path)


def test_assert_lockfile_not_modified_passes_on_equal():
    data = {"meta": {"verify_level": "checksum"}, "package": []}
    assert_lockfile_not_modified(data, data)  # should not raise


def test_assert_lockfile_not_modified_raises_on_diff():
    original = {"meta": {"verify_level": "checksum"}, "package": []}
    modified = {"meta": {"verify_level": "full"}, "package": []}
    with pytest.raises(ValueError, match="modified"):
        assert_lockfile_not_modified(original, modified)
