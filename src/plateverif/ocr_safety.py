"""Conservative whole-reading OCR parsing, never I/O substitution."""
import re
PATTERN=re.compile(r"([0-9]{1,3})(?:\s*(?:bis|ter|quater|[ABCD]))?",re.I)
def numeric_reading(raw):
 m=PATTERN.fullmatch(str(raw or "").strip())
 return (m.group(1).lstrip("0") or "") if m else ""
