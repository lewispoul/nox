#!/usr/bin/env python3
"""
Automated Markdown Link Checker for NOX Documentation
Scans all markdown files in docs/ and reports broken or unreachable links.
"""
import os
import re
from pathlib import Path

import requests


def find_markdown_files(root):
    return list(Path(root).rglob("*.md"))


def extract_links(md_text):
    # Matches [text](url) and <url>
    pattern = re.compile(r"\[.*?\]\((.*?)\)|<(http[^>]+)>")
    return [m.group(1) or m.group(2) for m in pattern.finditer(md_text)]


def check_link(url):
    if url.startswith("http"):  # External link
        try:
            resp = requests.head(url, allow_redirects=True, timeout=5)
            return resp.status_code < 400
        except Exception:
            return False
    else:  # Internal link
        # Remove anchors/fragments
        file_path = url.split("#")[0]
        return os.path.exists(file_path)


def main():
    docs_root = os.path.join(os.path.dirname(__file__), "docs")
    md_files = find_markdown_files(docs_root)
    broken = []
    for md_file in md_files:
        with open(md_file, "r", encoding="utf-8") as f:
            text = f.read()
        links = extract_links(text)
        for link in links:
            if not link:
                continue
            if not check_link(link):
                broken.append((md_file, link))
    if broken:
        print("Broken links found:")
        for f, l in broken:
            print(f"- {f}: {l}")
    else:
        print("No broken links found.")


if __name__ == "__main__":
    main()
