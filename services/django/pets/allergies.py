ALLOWED_ALLERGY_INGREDIENTS = [
    "감자",
    "가다랑어",
    "고구마",
    "닭고기",
    "밀",
    "병아리콩",
    "새우",
    "소고기",
    "쌀",
    "양고기",
    "연어",
    "오리",
    "옥수수",
    "완두콩",
    "우유",
    "참치",
    "칠면조",
]

ALLERGY_ALIAS_MAP = {
    "beef": "소고기",
    "chicken": "닭고기",
    "chickpea": "병아리콩",
    "corn": "옥수수",
    "duck": "오리",
    "lamb": "양고기",
    "milk": "우유",
    "pea": "완두콩",
    "peas": "완두콩",
    "potato": "감자",
    "rice": "쌀",
    "salmon": "연어",
    "shrimp": "새우",
    "skipjack": "가다랑어",
    "sweet potato": "고구마",
    "sweetpotato": "고구마",
    "tuna": "참치",
    "turkey": "칠면조",
    "wheat": "밀",
}


def allergy_options():
    return sorted(ALLOWED_ALLERGY_INGREDIENTS)


_CANONICAL_MAP = {value.replace(" ", ""): value for value in allergy_options()}
_ALIAS_MAP = {key.replace(" ", "").lower(): value for key, value in ALLERGY_ALIAS_MAP.items()}


def normalize_allergy_ingredient(value):
    if value is None:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    compact = raw.replace(" ", "")
    if compact in _CANONICAL_MAP:
        return _CANONICAL_MAP[compact]
    return _ALIAS_MAP.get(compact.lower())


def parse_allergy_ingredients(raw_values):
    if raw_values is None:
        return None, []

    values = list(raw_values)
    if len(values) == 1 and isinstance(values[0], str) and "," in values[0]:
        values = values[0].split(",")

    cleaned = []
    invalid = []
    seen = set()
    for value in values:
        raw = str(value).strip()
        if not raw:
            continue
        normalized = normalize_allergy_ingredient(raw)
        if not normalized:
            if raw not in invalid:
                invalid.append(raw)
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return cleaned, invalid
