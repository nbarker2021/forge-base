from pathlib import Path

from cqekernel.master_ribbon.compiler import _content_hash


def test_text_hash_is_portable_across_lf_and_crlf(tmp_path: Path) -> None:
    text = tmp_path / "receipt.jsonl"
    text.write_bytes(b'{"result":"PASS"}\n{"value":1}\n')
    lf_hash = _content_hash(text)
    text.write_bytes(b'{"result":"PASS"}\r\n{"value":1}\r\n')
    assert _content_hash(text) == lf_hash

    binary = tmp_path / "receipt.bin"
    binary.write_bytes(b"a\nb")
    lf_binary_hash = _content_hash(binary)
    binary.write_bytes(b"a\r\nb")
    assert _content_hash(binary) != lf_binary_hash
