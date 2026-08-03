"""Look up FinnGen endpoints on Risteys: names, ontology codes, and statistics."""
import re
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup, Tag

from agentic_finngen.llm.base import Tool
from agentic_finngen.logger import get_logger

logger = get_logger(__name__)

RISTEYS_BASE_URL = "https://risteys.finngen.fi"
REQUEST_TIMEOUT = 30
MAX_SUGGESTIONS = 10

# Endpoint pages live under /endpoints/<CODE> and the path is case-sensitive.
# Codes are upper-case alphanumerics joined by underscores, e.g. 'N14_CHRONKIDNEYDIS'.
_ENDPOINT_CODE = re.compile(r"^[A-Z0-9_]{2,80}$")
_MIN_TOKEN_LEN = 3
_EM_DASH = "—"

# Populated on first use from /api/endpoints, which returns a flat list of codes.
_endpoint_index: Optional[List[str]] = None


def _get(path: str) -> Optional[requests.Response]:
    """GET a Risteys path, returning None if the request could not be completed."""
    url = f"{RISTEYS_BASE_URL}/{path.lstrip('/')}"
    try:
        return requests.get(url, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        logger.warning("Risteys request to %s failed: %s", url, exc)
        return None


def _endpoint_codes() -> List[str]:
    """All endpoint codes Risteys knows about, fetched once and cached."""
    global _endpoint_index
    if _endpoint_index is not None:
        return _endpoint_index

    _endpoint_index = []
    response = _get("api/endpoints")
    if response is not None and response.status_code == 200:
        try:
            payload = response.json()
        except ValueError:
            logger.warning("Risteys endpoint index was not valid JSON.")
        else:
            if isinstance(payload, list):
                _endpoint_index = [c for c in payload if isinstance(c, str)]
    logger.debug("Loaded %d Risteys endpoint codes.", len(_endpoint_index))
    return _endpoint_index


def _tokenize(text: str) -> List[str]:
    return [
        token
        for token in re.split(r"[^A-Za-z0-9]+", text.upper())
        if len(token) >= _MIN_TOKEN_LEN
    ]


def _match_score(tokens: List[str], code: str) -> int:
    """Score a code by the longest prefix of each query token it contains.

    Endpoint codes abbreviate words ('CHRONIC' -> 'CHRON', 'DISEASE' -> 'DIS'),
    so scoring on prefixes rather than whole words is what lets a plain-language
    query reach the right code.
    """
    score = 0
    for token in tokens:
        for end in range(len(token), _MIN_TOKEN_LEN - 1, -1):
            if token[:end] in code:
                score += end
                break
    return score


def _suggest(keyword: str) -> List[str]:
    """Candidate endpoint codes for a keyword that did not resolve directly."""
    tokens = _tokenize(keyword)
    if not tokens:
        return []
    ranked = [
        (-_match_score(tokens, code), len(code), code) for code in _endpoint_codes()
    ]
    # Ties break toward shorter codes, which are the primary endpoints rather
    # than their '_WIDE' / '_STRICT' variants.
    ranked = sorted(entry for entry in ranked if entry[0] < 0)
    return [code for _, _, code in ranked[:MAX_SUGGESTIONS]]


def _endpoint_name(soup: BeautifulSoup) -> Optional[str]:
    """Every page has two <h1>: the site nav (holds #Risteys-link) and the name."""
    for heading in soup.find_all("h1"):
        if heading.find(id="Risteys-link") is None:
            name = heading.get_text(" ", strip=True)
            if name:
                return name
    return None


def _parse_key_figures(table: Tag) -> Dict[str, Any]:
    """Parse a 'Key figures' table into {metric: {All/Female/Male: value}}."""
    header_cells = [th.get_text(" ", strip=True) for th in table.select("thead th")]
    columns = [text for text in header_cells[1:] if text]

    figures: Dict[str, Any] = {}
    group: Optional[str] = None
    for row in table.select("tbody tr"):
        label_cell = row.find("th")
        if label_cell is None:
            continue
        label = label_cell.get_text(" ", strip=True)
        if not label:
            continue

        values = [td.get_text(" ", strip=True) for td in row.find_all("td")]
        if not any(values):
            # A metric with no values of its own heads a group of indented rows
            # (FinnRegistry splits metrics into 'Whole population' / 'Only index
            # persons'). Hold onto it so those rows nest underneath.
            group = label
            figures.setdefault(label, {})
            continue

        if columns and len(columns) == len(values):
            row_values: Any = dict(zip(columns, values))
        else:
            row_values = values[0]

        indented = "indent" in (label_cell.get("class") or [])
        if indented and group is not None:
            figures[group][label] = row_values
        else:
            group = None
            figures[label] = row_values
    return figures


def _parse_summary_statistics(soup: BeautifulSoup) -> Dict[str, Any]:
    """Case counts, prevalence and median age, split by data source."""
    section = soup.find(id="summary-statistics")
    if section is None:
        return {}

    statistics: Dict[str, Any] = {}
    for block in section.find_all("article", class_="sumstats"):
        heading = block.find("h3")
        if heading is None:
            continue
        # Source headings are rendered as '-FinnGen-' / '-FinRegistry-'.
        source = heading.get_text(" ", strip=True).strip("-").strip()
        if not source:
            continue

        table = block.find("table", class_="horizontal-table")
        if table is None:
            note = block.find("p", class_="explanation_text")
            if note is not None:
                statistics.setdefault(source, {})["note"] = note.get_text(
                    " ", strip=True
                )
            continue

        figures = _parse_key_figures(table)
        if figures:
            statistics.setdefault(source, {}).update(figures)
    return statistics


def _parse_registry_filters(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """The ICD / ATC codes defining the endpoint, per source registry.

    These are what the Analyst and Coder agents need in order to translate an
    endpoint into a query against the FinnGen registry tables.
    """
    section = soup.find(id="endpoint-definition")
    if section is None:
        return []

    filters: List[Dict[str, str]] = []
    seen = set()
    for marker in section.find_all("p"):
        if "Registry filters" not in marker.get_text():
            continue
        group = marker.find_next("ul")
        if group is None:
            continue
        for item in group.find_all("li"):
            label = item.find("b")
            if label is None:
                continue
            registry_label = label.get_text(" ", strip=True)
            # Each item reads '<registry>: <vocabulary> — <codes>'.
            remainder = item.get_text(" ", strip=True)[len(registry_label):].strip()
            vocabulary, _, codes = remainder.partition(_EM_DASH)
            entry = {
                "registry": registry_label.rstrip(":").strip(),
                "vocabulary": vocabulary.strip(),
                "codes": codes.strip(),
            }
            key = tuple(entry.values())
            if key not in seen:
                seen.add(key)
                filters.append(entry)
    return filters


def _parse_endpoint_page(html: str, code: str, url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    return {
        "status": "success",
        "url": url,
        "code": code,
        "name": _endpoint_name(soup),
        "registry_filters": _parse_registry_filters(soup),
        "summary_statistics": _parse_summary_statistics(soup),
    }


def _not_found(keyword: str) -> Dict[str, Any]:
    suggestions = _suggest(keyword)
    message = (
        f"No Risteys endpoint resolved for '{keyword}'. Risteys is keyed by exact "
        "endpoint code, not by free text."
    )
    if suggestions:
        message += " Call this tool again with one of the suggested codes."
    return {
        "status": "not_found",
        "message": message,
        "suggestions": suggestions,
    }


def search_risteys(keyword: str) -> Dict[str, Any]:
    """
    Look up a FinnGen endpoint on Risteys.

    Args:
        keyword: A FinnGen endpoint code such as 'E4_DM2' or 'N14_CHRONKIDNEYDIS'.
            Free text is accepted but only yields a list of candidate codes.

    Returns:
        On success, the endpoint name, its ICD/ATC registry filters, and summary
        statistics. Otherwise a status of 'not_found' with candidate codes, or
        'error' if Risteys could not be reached.
    """
    keyword = (keyword or "").strip()
    if not keyword:
        return {"status": "error", "message": "No keyword given."}

    code = keyword.upper()
    if not _ENDPOINT_CODE.match(code):
        return _not_found(keyword)

    path = f"endpoints/{code}"
    response = _get(path)
    if response is None:
        return {
            "status": "error",
            "message": f"Could not reach Risteys to look up '{code}'.",
        }
    if response.status_code == 404:
        return _not_found(keyword)
    if response.status_code != 200:
        return {
            "status": "error",
            "message": (
                f"Risteys returned HTTP {response.status_code} for '{code}'."
            ),
        }

    return _parse_endpoint_page(
        response.text, code, f"{RISTEYS_BASE_URL}/{path}"
    )


search_risteys_tool = Tool(
    name="search_risteys",
    description=(
        "Look up a FinnGen endpoint on Risteys. Pass an exact endpoint code such "
        "as 'E4_DM2' (type 2 diabetes), 'N14_CHRONKIDNEYDIS' (chronic kidney "
        "disease) or 'RX_STATIN' (statin purchases); codes are upper-case words "
        "joined by underscores. Returns the endpoint name, the ICD and ATC codes "
        "that define it per source registry, and summary statistics (number of "
        "individuals, prevalence, median age at first event) broken down by sex. "
        "Risteys cannot be searched by free text: passing a plain-language "
        "description returns a list of candidate codes under 'suggestions', which "
        "you should then look up individually."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": (
                    "A FinnGen endpoint code, e.g. 'E4_DM2' or 'RX_STATIN'."
                ),
            }
        },
        "required": ["keyword"],
    },
    fn=search_risteys,
)


if __name__ == "__main__":
    logger.info(search_risteys("E4_DM2"))
