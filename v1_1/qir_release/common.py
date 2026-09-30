from __future__ import annotations
import hashlib, json, re, unicodedata
from pathlib import Path
from typing import Any

ROUTES = ("short_circuit", "medium", "complex", "llm_needed")
SEED = 20260929

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text)).casefold()
    text = text.replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text).strip()

def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

# Fixed lexical generalization, declared before closeout evaluation. No labels or
# test results are consulted. This is a leakage heuristic, not entity extraction.
SCHOOLS = (
    "massachusetts institute of technology", "california institute of technology",
    "university of california los angeles", "university of california berkeley",
    "university of southern california", "university of illinois urbana champaign",
    "university of wisconsin madison", "university of north carolina chapel hill",
    "university of pennsylvania", "university of washington", "university of wisconsin",
    "university of maryland", "university of michigan", "university of florida",
    "university of virginia", "university of chicago", "university of texas at austin",
    "georgia institute of technology", "carnegie mellon", "boston university",
    "arizona state", "michigan state", "ohio state", "penn state", "georgia tech",
    "rice university", "virginia tech", "uc san diego", "uc berkeley", "uc irvine",
    "ut austin", "northeastern", "northwestern", "vanderbilt", "princeton", "stanford",
    "columbia", "harvard", "cornell", "dartmouth", "purdue", "caltech", "ucla", "usc",
    "nyu", "mit", "brown", "duke", "yale", "rice", "upenn", "uconn", "uiuc",
)
PROGRAMS = ("computer science", "mechanical engineering", "aerospace engineering",
            "electrical engineering", "political science", "data science", "civil engineering",
            "neuroscience", "psychology", "philosophy", "engineering", "biology", "chemistry",
            "architecture", "nursing", "business", "economics", "history", "education", "design")
PLACES = ("california", "massachusetts", "pennsylvania", "north carolina", "south carolina",
          "new york", "new jersey", "new england", "east coast", "west coast", "florida",
          "illinois", "michigan", "maryland", "texas", "washington", "chicago", "boston",
          "detroit", "midwest", "northeast", "southeast")

def _replace_terms(text: str, terms: tuple[str, ...], token: str) -> str:
    pattern = r"(?<!\w)(?:" + "|".join(re.escape(x) for x in sorted(terms, key=len, reverse=True)) + r")(?!\w)"
    return re.sub(pattern, token, text)

def family_text(text: str) -> str:
    text = normalize(text)
    text = _replace_terms(text, SCHOOLS, "entityschool")
    text = _replace_terms(text, PROGRAMS, "entityprogram")
    text = _replace_terms(text, PLACES, "entityplace")
    text = re.sub(r"\$?\d+(?:[,.]\d+)*(?:k|%| dollars)?", "entitynumber", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def family_id(text: str) -> str:
    return hashlib.sha256(family_text(text).encode()).hexdigest()[:20]
