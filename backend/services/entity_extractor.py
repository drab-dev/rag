"""Entity extraction utilities using spaCy noun phrases.

This module provides a high-quality keyphrase extractor that
uses spaCy's noun_chunks to generate graph entities such as
"machine learning", "neural networks", "statistical models",
"natural language processing", "deep learning", and
"artificial intelligence".
"""

import re
import string
from functools import lru_cache
from typing import List, Optional, Set

import spacy
from spacy.language import Language


_MODEL_CANDIDATES = ("en_core_web_md", "en_core_web_sm")


@lru_cache(maxsize=1)
def _load_spacy_model() -> Language:
    """Load a spaCy English model, preferring the medium model if available.

    Tries ``en_core_web_md`` first, then falls back to ``en_core_web_sm``.
    Raises a clear error if no model can be loaded.
    """
    last_error: Optional[Exception] = None
    for model_name in _MODEL_CANDIDATES:
        try:
            return spacy.load(model_name)
        except Exception as exc:  # pragma: no cover - environment dependent
            last_error = exc
    raise RuntimeError(
        "Could not load any spaCy English model. "
        "Please install one of: en_core_web_md, en_core_web_sm. "
        "For example: `python -m spacy download en_core_web_sm`."
    ) from last_error


# Load the model once at import time for efficiency
_nlp = _load_spacy_model()


_ALPHA_RE = re.compile(r"[a-zA-Z]")


def _normalize_phrase(text: str) -> str:
    """Normalize a noun phrase for use as a graph entity.

    Normalization rules:
    - lowercasing
    - trimming whitespace
    - stripping leading/trailing punctuation
    - keep only phrases that contain at least one alphabetic character
    """
    phrase = text.lower().strip()
    phrase = phrase.strip(string.punctuation)

    if not phrase:
        return ""
    if not _ALPHA_RE.search(phrase):
        return ""
    return phrase


def extract_entities_spacy(text: str) -> List[str]:
    """Extract high‑quality noun‑phrase entities from text using spaCy.

    Extraction logic:
    - Use ``doc.noun_chunks`` from spaCy
    - Remove chunks that are only stopwords or punctuation
    - Only keep chunks that contain alphabetic characters
    - Normalize by:
      * lowercasing
      * trimming whitespace
      * removing leading/trailing punctuation
    - Deduplicate final list while preserving order

    Args:
        text: Input document text.

    Returns:
        List of normalized noun‑phrase entities.
    """
    if not text:
        return []

    doc = _nlp(text)

    seen: Set[str] = set()
    entities: List[str] = []

    for chunk in doc.noun_chunks:
        # Drop tokens that are just spaces or punctuation
        tokens = [t for t in chunk if not (t.is_space or t.is_punct)]
        if not tokens:
            continue

        # Skip chunks that are only stopwords
        if all(t.is_stop for t in tokens):
            continue

        # Use the surface form of the filtered tokens; lemmatization is optional
        # If you prefer lemmatized phrases, replace t.text with t.lemma_.
        surface = " ".join(t.text for t in tokens)
        normalized = _normalize_phrase(surface)

        if not normalized:
            continue

        if normalized not in seen:
            seen.add(normalized)
            entities.append(normalized)

    return entities
