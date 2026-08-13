"""Pure, database-free hardware model identity matching shared by public search and AI.

The contract is deliberately narrow: complete ASCII token sequences are exact, and
compact spacing/vendor aliases are enabled only for recognizable GPU model names.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any, Callable

GPU_VENDOR_PREFIXES = {"NVIDIA", "AMD", "INTEL"}
GPU_FAMILY_TOKENS = {"RTX", "GEFORCE", "QUADRO", "TESLA", "INSTINCT", "RADEON", "ARC"}
NEGATIVE_TEXT = re.compile(r"(?:不接受|不要|排除|不能|必须不是|不可|不支持|不得|不引用|非本型号|相近型号)", re.I)


def normalized_tokens(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[A-Z0-9]+", str(text or "").upper()))


def _gpu_alias(tokens: tuple[str, ...]) -> tuple[str, ...] | None:
    if len(tokens) < 2 or tokens[0] not in GPU_VENDOR_PREFIXES:
        return None
    alias = tokens[1:]
    if alias[-1:] == ("GENERATION",) and "RTX" in alias and "ADA" in alias:
        alias = alias[:-1]
    if not alias or not any(any(char.isdigit() for char in token) for token in alias):
        return None
    gpu_shape = (len(alias) == 1 or alias[0] in GPU_FAMILY_TOKENS) if tokens[0] == "NVIDIA" else alias[0] in GPU_FAMILY_TOKENS
    return alias if gpu_shape else None


def _query_sequences(query: str) -> tuple[tuple[str, ...], ...]:
    tokens = normalized_tokens(query)
    sequences: list[tuple[str, ...]] = []
    for start in range(len(tokens)):
        for end in range(start + 1, len(tokens) + 1):
            sequences.append(tokens[start:end])
    return tuple(sequences)


def model_name_match_rank(query: str, model_name: str) -> int:
    """Return 300 exact, 200 narrow GPU alias/compact exact, otherwise zero."""
    model_tokens = normalized_tokens(model_name)
    if not model_tokens:
        return 0
    sequences = _query_sequences(query)
    if model_tokens in sequences:
        return 300
    # Server full-model equivalence is intentionally narrow: separators may differ,
    # but every alphanumeric character of the complete model must remain present.
    # NF5280-M7 / NF5280 M7 == NF5280M7; the prefix NF5280 is never enough.
    query_tokens = normalized_tokens(query)
    compact_model = "".join(model_tokens)
    if len(compact_model) >= 5 and any(char.isdigit() for char in compact_model):
        # Accept separator-only spelling differences inside an otherwise complete
        # model token, including model embedded in prose. Contiguous token windows
        # keep NF5280-M7 / NF5280 M7 / NF5280M7 equivalent without accepting NF5280.
        for start in range(len(query_tokens)):
            joined = ""
            for end in range(start, len(query_tokens)):
                joined += query_tokens[end]
                if joined == compact_model:
                    return 250
                if len(joined) >= len(compact_model):
                    break
    alias = _gpu_alias(model_tokens)
    if alias and alias in sequences:
        return 200
    # Compact equivalence is GPU-only. It must never broaden server prefixes/short words.
    compact_query_tokens = normalized_tokens(query)
    if alias and "".join(alias) in compact_query_tokens:
        return 200
    return 0


def positive_model_text_match(text: str, model_name: str) -> bool:
    """Match model identity in one positive evidence line; negative prose is ignored."""
    return not NEGATIVE_TEXT.search(str(text or "")) and model_name_match_rank(text, model_name) > 0


def rank_model_rows(query: str, rows: Iterable[Any], name_getter: Callable[[Any], str], id_getter: Callable[[Any], int]) -> list[Any]:
    ranked = [(model_name_match_rank(query, name_getter(row)), id_getter(row), row) for row in rows]
    exact = [item for item in ranked if item[0] > 0]
    return [row for _rank, _id, row in sorted(exact, key=lambda item: (-item[0], item[1]))]
