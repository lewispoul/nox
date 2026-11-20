"""Read a selected thesis_ai records.jsonl export; never open source PDF paths.

This bridge implements lexical retrieval, not thesis_ai's embedding pipeline.
No code, model, private corpus, or generated answer is copied from thesis_ai.
"""
import hashlib
import json
import re
from pathlib import Path


class Literature:
    def __init__(self, path: Path | None):
        self.records = []
        self.digest = None
        if path is None:
            return
        # Limit the pilot's memory use; larger corpora need a dedicated index.
        with path.open("rb") as stream:
            raw = stream.read(20_000_001)
        if len(raw) > 20_000_000:
            raise ValueError("Literature export exceeds 20 MB pilot limit")
        self.digest = hashlib.sha256(raw).hexdigest()
        for line_number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"Invalid literature record at line {line_number}")
            text, source = row.get("text"), row.get("source_name")
            if not isinstance(text, str) or not text.strip() or not isinstance(source, str) or not source.strip():
                raise ValueError(f"Missing text/source_name at line {line_number}")
            # Projection intentionally omits arbitrary metadata and local paths.
            page = row.get("page_number", row.get("page"))
            if page is not None and (type(page) is not int or page < 1):
                raise ValueError(f"Invalid page at line {line_number}")
            self.records.append({"citation_id": f"record-{line_number}", "source_name": source,
                                 "page_number": page, "text": text})

    @staticmethod
    def terms(text):
        return set(re.findall(r"\w+", text.casefold()))

    def search(self, query, limit):
        terms = self.terms(query)
        if not terms:
            raise ValueError("Query must contain a word")
        matches = []
        for record in self.records:
            score = len(terms & self.terms(record["text"])) / len(terms)
            if score:
                matches.append(dict(record, score=score, excerpt=record["text"][:1500]))
        matches.sort(key=lambda row: (-row["score"], row["citation_id"]))
        return {"method": "lexical_term_coverage", "index_sha256": self.digest,
                "answer_generated": False,
                "results": [{key: value for key, value in row.items() if key != "text"}
                            for row in matches[:limit]]}
