"""
Document/email parsing layer.

Two modes:
  - "mock" (default, no API key needed): regex/heuristic extraction tuned for
    typical load tender / rate confirmation phrasing. Deterministic, fast,
    works fully offline -- good enough to power the MVP end-to-end.
  - "anthropic": if ANTHROPIC_API_KEY is set, delegates extraction to Claude
    using a strict JSON tool schema (structured output). Falls back to the
    mock parser on any error so the pipeline never blocks on an LLM outage.
"""
import json
import os
import re
from dataclasses import dataclass, asdict
from typing import Optional

EQUIPMENT_TYPES = ["Dry Van", "Reefer", "Flatbed", "Power Only", "Step Deck", "Box Truck"]

EQUIPMENT_ALIASES = {
    "dry van": "Dry Van",
    "van": "Dry Van",
    "reefer": "Reefer",
    "refrigerated": "Reefer",
    "flatbed": "Flatbed",
    "flat bed": "Flatbed",
    "step deck": "Step Deck",
    "stepdeck": "Step Deck",
    "power only": "Power Only",
    "box truck": "Box Truck",
}

CITY_STATE_RE = re.compile(
    r"([A-Z][a-zA-Z\.\s]+?,\s*[A-Z]{2})"
)


@dataclass
class ParsedTender:
    origin: Optional[str] = None
    destination: Optional[str] = None
    equipment_type: Optional[str] = None
    weight_lbs: Optional[float] = None
    pickup_date: Optional[str] = None
    commodity: Optional[str] = None
    confidence: float = 0.0
    parser_used: str = "mock"

    def to_dict(self):
        return asdict(self)


def _extract_equipment(text: str) -> Optional[str]:
    lower = text.lower()
    for alias, canonical in EQUIPMENT_ALIASES.items():
        if alias in lower:
            return canonical
    return None


def _extract_weight(text: str) -> Optional[float]:
    m = re.search(r"([\d,]{3,7})\s*(?:lbs?|pounds)", text, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def _extract_pickup_date(text: str) -> Optional[str]:
    patterns = [
        r"(?:pickup|pick[\s-]?up|ship)\s*(?:date)?\s*[:\-]?\s*(\d{1,2}/\d{1,2}/\d{2,4})",
        r"(?:pickup|pick[\s-]?up|ship)\s*(?:date)?\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})",
        r"(?:pickup|pick[\s-]?up|ship)\s*(?:date)?\s*[:\-]?\s*([A-Z][a-z]+ \d{1,2},? \d{4})",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def _extract_commodity(text: str) -> Optional[str]:
    m = re.search(r"commodity\s*[:\-]?\s*([A-Za-z0-9 \-]+)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip(".")
    return None


def _extract_origin_destination(text: str):
    origin = None
    destination = None

    o = re.search(r"(?:origin|pickup|from)\s*[:\-]?\s*([A-Z][a-zA-Z\.\s]+,\s*[A-Z]{2})", text, re.IGNORECASE)
    d = re.search(r"(?:destination|delivery|drop|to)\s*[:\-]?\s*([A-Z][a-zA-Z\.\s]+,\s*[A-Z]{2})", text, re.IGNORECASE)
    if o:
        origin = o.group(1).strip()
    if d:
        destination = d.group(1).strip()

    if not origin or not destination:
        # Fallback: "X, ST to Y, ST" or "X, ST -> Y, ST"
        m = re.search(
            r"([A-Z][a-zA-Z\.\s]+,\s*[A-Z]{2})\s*(?:to|->|–|-)\s*([A-Z][a-zA-Z\.\s]+,\s*[A-Z]{2})",
            text,
        )
        if m:
            origin = origin or m.group(1).strip()
            destination = destination or m.group(2).strip()

    if not origin or not destination:
        # Last resort: grab first two city/state matches in document order
        matches = CITY_STATE_RE.findall(text)
        matches = [m.strip() for m in matches]
        if not origin and len(matches) >= 1:
            origin = matches[0]
        if not destination and len(matches) >= 2:
            destination = matches[1]

    return origin, destination


def mock_parse(text: str) -> ParsedTender:
    origin, destination = _extract_origin_destination(text)
    equipment = _extract_equipment(text)
    weight = _extract_weight(text)
    pickup_date = _extract_pickup_date(text)
    commodity = _extract_commodity(text)

    fields_found = sum(1 for v in [origin, destination, equipment, weight, pickup_date] if v)
    confidence = round(0.5 + 0.1 * fields_found, 2)
    confidence = min(confidence, 0.98)

    return ParsedTender(
        origin=origin,
        destination=destination,
        equipment_type=equipment,
        weight_lbs=weight,
        pickup_date=pickup_date,
        commodity=commodity,
        confidence=confidence,
        parser_used="mock",
    )


ANTHROPIC_TOOL_SCHEMA = {
    "name": "extract_load_tender",
    "description": "Extract structured freight load tender fields from raw text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "origin": {"type": "string", "description": "Origin city, state e.g. 'Dallas, TX'"},
            "destination": {"type": "string", "description": "Destination city, state e.g. 'Atlanta, GA'"},
            "equipment_type": {
                "type": "string",
                "enum": EQUIPMENT_TYPES,
                "description": "Trailer/equipment type required",
            },
            "weight_lbs": {"type": "number", "description": "Shipment weight in pounds"},
            "pickup_date": {"type": "string", "description": "Requested pickup date as written"},
            "commodity": {"type": "string", "description": "Commodity/freight description"},
            "confidence": {"type": "number", "description": "0-1 confidence in the extraction"},
        },
        "required": ["origin", "destination", "equipment_type"],
    },
}


def anthropic_parse(text: str) -> Optional[ParsedTender]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5"),
            max_tokens=1024,
            tools=[ANTHROPIC_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": "extract_load_tender"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Extract structured load tender / rate confirmation data "
                        f"from this freight document:\n\n{text}"
                    ),
                }
            ],
        )
        for block in message.content:
            if block.type == "tool_use" and block.name == "extract_load_tender":
                data = block.input
                return ParsedTender(
                    origin=data.get("origin"),
                    destination=data.get("destination"),
                    equipment_type=data.get("equipment_type"),
                    weight_lbs=data.get("weight_lbs"),
                    pickup_date=data.get("pickup_date"),
                    commodity=data.get("commodity"),
                    confidence=float(data.get("confidence", 0.9)),
                    parser_used="anthropic",
                )
    except Exception:
        return None
    return None


def parse_tender_text(text: str) -> ParsedTender:
    """Best-available parse: try Claude structured extraction if configured,
    otherwise fall back to the deterministic mock parser."""
    result = anthropic_parse(text)
    if result is not None:
        return result
    return mock_parse(text)
