#!/usr/bin/env python3
"""
Simple CLI Documentation Search Tool for NOX Docs
Searches all markdown files in docs/ for a keyword or phrase.
"""
import re
import sys
from pathlib import Path


def find_markdown_files(root):
    return list(Path(root).rglob("*.md"))


def search_docs(keyword, root):
    md_files = find_markdown_files(root)
    results = []
    for md_file in md_files:
        with open(md_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if re.search(keyword, line, re.IGNORECASE):
                    results.append((md_file, i, line.strip()))
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: search_docs.py <keyword>")
        sys.exit(1)
    keyword = sys.argv[1]
    docs_root = str(Path(__file__).parent.parent / "docs")
    results = search_docs(keyword, docs_root)
    if results:
        print(f'Found {len(results)} matches for "{keyword}":')
        for f, i, l in results:
            print(f"- {f} [Line {i}]: {l}")
    else:
        print(f'No matches found for "{keyword}".')


if __name__ == "__main__":
    main()
