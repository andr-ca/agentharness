"""Tests for block_installer.py: byte-preserving marker block insert/
replace/remove used by harness-link.sh's existing-surface integration.
"""
import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "setup" / "block_installer.py"
spec = importlib.util.spec_from_file_location("block_installer", MODULE_PATH)
bi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bi)


def test_detect_newline_style_lf():
    assert bi.detect_newline_style("a\nb\nc\n") == "\n"


def test_detect_newline_style_crlf():
    assert bi.detect_newline_style("a\r\nb\r\nc\r\n") == "\r\n"


def test_detect_newline_style_defaults_to_lf_when_no_newlines():
    assert bi.detect_newline_style("no newlines here") == "\n"


def test_has_trailing_newline_true():
    assert bi.has_trailing_newline("a\nb\n") is True


def test_has_trailing_newline_false():
    assert bi.has_trailing_newline("a\nb") is False


def test_has_trailing_newline_empty_string():
    assert bi.has_trailing_newline("") is False


def test_sha256_bytes_is_stable_and_correct():
    import hashlib
    data = b"hello world"
    assert bi.sha256_bytes(data) == hashlib.sha256(data).hexdigest()
