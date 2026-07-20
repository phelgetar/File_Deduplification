#!/usr/bin/env python3
"""
Test script for the local LLM (Ollama) classification fallback.

Verifies that:
1. The client detects server availability without crashing
2. Text files with recognizable content get a sensible category
3. Binary content is not sent as a snippet
4. Results are cached by file hash (duplicates cost one call)

Requires a running Ollama server; tests are skipped gracefully if absent.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm_client import LLMClassifier, _read_snippet
from models.file_info import FileInfo


def test_snippet_extraction():
    with tempfile.TemporaryDirectory() as tmp:
        text_file = Path(tmp) / "notes"
        text_file.write_text("Meeting notes from the quarterly review.")
        assert _read_snippet(text_file) is not None, "text file should yield a snippet"

        binary_file = Path(tmp) / "blob"
        binary_file.write_bytes(b"\x00\x01\x02\xff" * 64)
        assert _read_snippet(binary_file) is None, "binary file should yield no snippet"

        empty_file = Path(tmp) / "empty"
        empty_file.write_bytes(b"")
        assert _read_snippet(empty_file) is None, "empty file should yield no snippet"
    print("✅ Snippet extraction behaves correctly")


def test_classification():
    client = LLMClassifier()
    if not client.is_available():
        print("⚠️  Ollama server not running — skipping live classification tests")
        return

    print(f"🦙 Using {client.model} @ {client.host}")

    with tempfile.TemporaryDirectory() as tmp:
        # An invoice-like file with no useful extension
        invoice = Path(tmp) / "scan_0042"
        invoice.write_text(
            "INVOICE #2024-118\n"
            "Bill To: Tim Canady\n"
            "Amount Due: $1,250.00\n"
            "Payment due within 30 days of receipt.\n"
        )
        fi = FileInfo(path=invoice, size=invoice.stat().st_size, hash="testhash1")
        result = client.classify(fi)
        assert result is not None, "classification should succeed"
        category, confidence = result
        print(f"   invoice-like file  -> {category} ({confidence:.2f})")
        assert category == "financial", f"expected 'financial', got '{category}'"

        # A python script with a misleading name and no extension
        script = Path(tmp) / "backup_util"
        script.write_text(
            "#!/usr/bin/env python3\n"
            "import argparse\n\n"
            "def main():\n"
            "    parser = argparse.ArgumentParser()\n"
            "    parser.add_argument('--target')\n"
        )
        fi2 = FileInfo(path=script, size=script.stat().st_size, hash="testhash2")
        result2 = client.classify(fi2)
        assert result2 is not None
        category2, confidence2 = result2
        print(f"   python script      -> {category2} ({confidence2:.2f})")
        assert category2 == "code", f"expected 'code', got '{category2}'"

        # Cache: same hash must not trigger a new call
        fi3 = FileInfo(path=invoice, size=fi.size, hash="testhash1")
        assert client.classify(fi3) == result, "cached result should be returned"
        assert len(client._cache) == 2, "cache should hold exactly 2 entries"
        print("   cache              -> hit on duplicate hash")

    print("✅ Live classification tests passed")


if __name__ == "__main__":
    test_snippet_extraction()
    test_classification()
    print("\n🎉 All LLM classifier tests passed")
