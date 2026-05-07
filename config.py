import re

NUMBER_PATTERN = re.compile(
    r'(?<!\w)\$?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)'
)

SCALE_PHRASE_PATTERNS = [
    (re.compile(r'\bin\s+billions?\b', re.IGNORECASE), 10**9),
    (re.compile(r'\bin\s+millions?\b', re.IGNORECASE), 10**6),
    (re.compile(r'\bin\s+thousands?\b', re.IGNORECASE), 10**3),
    (re.compile(r'\bvalues?\s+(?:are\s+)?(?:expressed\s+)?in\s+billions?\b', re.IGNORECASE), 10**9),
    (re.compile(r'\bvalues?\s+(?:are\s+)?(?:expressed\s+)?in\s+millions?\b', re.IGNORECASE), 10**6),
    (re.compile(r'\bvalues?\s+(?:are\s+)?(?:expressed\s+)?in\s+thousands?\b', re.IGNORECASE), 10**3),
    (re.compile(r'\(?dollars?\s+in\s+billions?\)?', re.IGNORECASE), 10**9),
    (re.compile(r'\(?dollars?\s+in\s+millions?\)?', re.IGNORECASE), 10**6),
    (re.compile(r'\(?dollars?\s+in\s+thousands?\)?', re.IGNORECASE), 10**3),
]

LOCAL_SCALE_PATTERNS = [
    (re.compile(r'\bbillions?\b', re.IGNORECASE), 10**9),
    (re.compile(r'\bmillions?\b', re.IGNORECASE), 10**6),
    (re.compile(r'\bthousands?\b', re.IGNORECASE), 10**3),
]

SCALE_NAMES = {10**3: "thousands", 10**6: "millions", 10**9: "billions"}

NON_FINANCIAL_PATTERN = re.compile(
    r'\b(?:strength|workyears?|work\s+years?|personnel|headcount|fte|'
    r'positions?|employees?|workforce|staffing|manpower)\b',
    re.IGNORECASE
)