"""
Reads a .docx file and splits it into sections.

A new section starts at any paragraph that BEGINS with an Arabic numeral
(1, 2, 3, ... 10, 11, ...), optionally followed by "." or ")" and a space,
e.g.:
    1. የመጀመሪያው ክፍል ርዕስ
    2) ሁለተኛው ክፍል ርዕስ

Everything after that heading paragraph, up to the next numbered
paragraph, is treated as the body of that section.

Sections are sorted NUMERICALLY (1, 2, ... 10, 11 ...) by their number,
not by the order they appear in the file and not as text (so "10" is
never treated as coming before "2").

Output: sections.json -- a list of objects, in final send order:
    {"number": 1, "title": "...", "content": "full section text"}

Usage:
    python extract_sections.py "path/to/YourBigFile.docx"
"""

import sys
import json
import re
from docx import Document

# Arabic numeral at the very start of a paragraph, e.g. "1.", "12)", "3 "
NUMBER_RE = re.compile(r'^(\d+)[.\)]?\s*(.*)$')


def is_section_heading(text: str):
    """Return (number, rest_of_title) if the paragraph starts a new section, else None."""
    text = text.strip()
    if not text:
        return None
    m = NUMBER_RE.match(text)
    if m:
        return int(m.group(1)), m.group(2).strip()
    return None


def extract_sections(docx_path: str):
    doc = Document(docx_path)
    sections = []
    current = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        heading = is_section_heading(text)
        if heading:
            if current is not None:
                sections.append(current)
            number, title = heading
            current = {
                "number": number,
                "title": title,
                "content_lines": [text],  # keep the heading line as the first line
            }
        else:
            if current is None:
                print(f"[warning] Text found before first section marker, skipping: {text[:60]}...")
                continue
            current["content_lines"].append(text)

    if current is not None:
        sections.append(current)

    for s in sections:
        s["content"] = "\n\n".join(s["content_lines"])
        del s["content_lines"]

    duplicates = _find_duplicates(sections)
    sections.sort(key=lambda s: s["number"])

    return sections, duplicates


def _find_duplicates(sections):
    seen = {}
    dups = []
    for s in sections:
        if s["number"] in seen:
            dups.append(s["number"])
        seen[s["number"]] = True
    return sorted(set(dups))


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_sections.py <path-to-docx> [output.json]")
        sys.exit(1)

    docx_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "sections.json"

    sections, duplicates = extract_sections(docx_path)

    if not sections:
        print("No sections found. Make sure each section starts with a number "
              "(1, 2, 3 ...) at the very beginning of its own paragraph.")
        sys.exit(1)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sections, f, ensure_ascii=False, indent=2)

    print(f"Found {len(sections)} sections. Saved to {out_path} (sorted 1 -> {sections[-1]['number']})")
    for s in sections:
        preview = s["content"][:40].replace("\n", " ")
        print(f"  {s['number']:>3}  {preview}...")

    if duplicates:
        print(f"\n[warning] These section numbers appear more than once in the file: {duplicates}")
        print("Only the LAST occurrence of each duplicated number was kept before sorting -- "
              "check your Word file if that's not what you intended.")

    numbers = [s["number"] for s in sections]
    expected = set(range(numbers[0], numbers[-1] + 1))
    missing = sorted(expected - set(numbers))
    if missing:
        print(f"\n[warning] These section numbers seem to be missing: {missing}")
        print("Double check those sections in the Word file are numbered correctly.")


if __name__ == "__main__":
    main()
