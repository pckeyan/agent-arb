from pathlib import Path

from agent_arb.ingest import outline, read_document, split_sections


def test_markdown_splits_by_heading(example_doc: Path) -> None:
    sections = split_sections(read_document(example_doc))
    headings = [s.heading for s in sections]
    assert headings[0] == "Orders Service: design document"
    assert "Payment handling" in headings
    assert all(s.start_line <= s.end_line for s in sections)
    assert all(s.ref == f"S{i + 1}" for i, s in enumerate(sections))


def test_outline_is_compact(example_doc: Path) -> None:
    sections = split_sections(read_document(example_doc))
    text = outline(sections, first_chars=60)
    assert "[S1]" in text
    assert len(text) < sum(len(s.text) for s in sections)


def test_unsupported_type(tmp_path: Path) -> None:
    p = tmp_path / "x.rtf"
    p.write_text("hi")
    try:
        read_document(p)
    except ValueError as e:
        assert "unsupported" in str(e)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")
