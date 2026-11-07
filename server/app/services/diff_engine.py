"""Diff Engine for Side-by-Side Content Comparison.

Computes mathematically exact word-level and line-level diffs using
Python's standard library SequenceMatcher, preserving whitespace and formatting.
"""

import re
import difflib
from typing import List, Dict, Any, Tuple
from app.schemas.audits import DiffChunk, DiffLine, DiffResponse


class DiffEngine:
    """Provides word-level and line-level structured diff calculations."""

    def split_tokens(self, text: str) -> List[str]:
        """Splits text into words, punctuation, and whitespace tokens."""
        # Splitting while capturing whitespace and word boundaries
        return re.findall(r'\S+|\s+', text)

    def compute_word_chunks(self, original_text: str, revised_text: str) -> List[DiffChunk]:
        """Computes granular inline token-level diff chunks (equal, delete, insert)."""
        orig_tokens = self.split_tokens(original_text)
        rev_tokens = self.split_tokens(revised_text)

        matcher = difflib.SequenceMatcher(None, orig_tokens, rev_tokens)
        chunks: List[DiffChunk] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                text = "".join(orig_tokens[i1:i2])
                chunks.append(DiffChunk(type="equal", text=text))
            elif tag == "delete":
                text = "".join(orig_tokens[i1:i2])
                chunks.append(DiffChunk(type="delete", text=text))
            elif tag == "insert":
                text = "".join(rev_tokens[j1:j2])
                chunks.append(DiffChunk(type="insert", text=text))
            elif tag == "replace":
                del_text = "".join(orig_tokens[i1:i2])
                ins_text = "".join(rev_tokens[j1:j2])
                chunks.append(DiffChunk(type="delete", text=del_text))
                chunks.append(DiffChunk(type="insert", text=ins_text))

        return chunks

    def compute_line_diff(self, original_text: str, revised_text: str) -> Tuple[List[DiffLine], Dict[str, int]]:
        """Computes synchronized side-by-side lines with modification classifications."""
        orig_lines = original_text.splitlines()
        rev_lines = revised_text.splitlines()

        matcher = difflib.SequenceMatcher(None, orig_lines, rev_lines)
        lines: List[DiffLine] = []
        stats = {"additions": 0, "deletions": 0, "modifications": 0, "unchanged": 0}

        orig_idx = 1
        rev_idx = 1

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    lines.append(
                        DiffLine(
                            line_number_orig=orig_idx,
                            line_number_rev=rev_idx,
                            type="equal",
                            original_text=orig_lines[i1 + k],
                            revised_text=rev_lines[j1 + k],
                        )
                    )
                    orig_idx += 1
                    rev_idx += 1
                    stats["unchanged"] += 1
            elif tag == "replace":
                max_len = max(i2 - i1, j2 - j1)
                for k in range(max_len):
                    orig_line = orig_lines[i1 + k] if (i1 + k) < i2 else None
                    rev_line = rev_lines[j1 + k] if (j1 + k) < j2 else None
                    line_o = orig_idx if orig_line is not None else None
                    line_r = rev_idx if rev_line is not None else None

                    lines.append(
                        DiffLine(
                            line_number_orig=line_o,
                            line_number_rev=line_r,
                            type="modified",
                            original_text=orig_line,
                            revised_text=rev_line,
                        )
                    )
                    if orig_line is not None:
                        orig_idx += 1
                    if rev_line is not None:
                        rev_idx += 1
                    stats["modifications"] += 1
            elif tag == "delete":
                for k in range(i2 - i1):
                    lines.append(
                        DiffLine(
                            line_number_orig=orig_idx,
                            line_number_rev=None,
                            type="delete",
                            original_text=orig_lines[i1 + k],
                            revised_text=None,
                        )
                    )
                    orig_idx += 1
                    stats["deletions"] += 1
            elif tag == "insert":
                for k in range(j2 - j1):
                    lines.append(
                        DiffLine(
                            line_number_orig=None,
                            line_number_rev=rev_idx,
                            type="insert",
                            original_text=None,
                            revised_text=rev_lines[j1 + k],
                        )
                    )
                    rev_idx += 1
                    stats["additions"] += 1

        return lines, stats

    def generate_diff(
        self,
        submission_id: str,
        from_rev_num: int,
        to_rev_num: int,
        original_text: str,
        revised_text: str,
    ) -> DiffResponse:
        """Generates unified DiffResponse with token chunks, side-by-side lines, and statistics."""
        chunks = self.compute_word_chunks(original_text, revised_text)
        lines, stats = self.compute_line_diff(original_text, revised_text)

        return DiffResponse(
            submission_id=submission_id,
            from_revision_number=from_rev_num,
            to_revision_number=to_rev_num,
            original_text=original_text,
            revised_text=revised_text,
            chunks=chunks,
            lines=lines,
            stats=stats,
        )


diff_engine = DiffEngine()
