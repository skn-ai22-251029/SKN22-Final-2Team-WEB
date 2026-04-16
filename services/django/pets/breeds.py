from collections import defaultdict
from functools import lru_cache

from django.db import connection


SPECIES_KEY_MAP = {
    "dog": "dog",
    "cat": "cat",
    "강아지": "dog",
    "고양이": "cat",
}

BUILTIN_BREEDS = {
    "dog": {
        "믹스": [
            "Mix",
            "Mixed",
            "믹스견",
            "Mongrel",
        ]
    },
    "cat": {
        "믹스": [
            "Mix",
            "Mixed",
            "믹스묘",
        ]
    },
}


def _normalize_species(species):
    return SPECIES_KEY_MAP.get((species or "").strip(), "")


def _normalize_breed_key(value):
    return " ".join(str(value or "").strip().split())


def _collapse_breed_key(value):
    return _normalize_breed_key(value).replace(" ", "")


def _register_alias(alias_map, canonical_name, alias):
    normalized = _normalize_breed_key(alias)
    if not normalized:
        return
    alias_map[normalized.casefold()] = canonical_name
    alias_map[_collapse_breed_key(normalized).casefold()] = canonical_name


def _apply_builtin_breeds(options, aliases):
    for species, breeds in BUILTIN_BREEDS.items():
        for canonical_name, extra_aliases in breeds.items():
            normalized_canonical = _normalize_breed_key(canonical_name)
            if normalized_canonical not in options[species]:
                options[species].append(normalized_canonical)

            _register_alias(aliases[species], normalized_canonical, normalized_canonical)
            for alias in extra_aliases:
                _register_alias(aliases[species], normalized_canonical, alias)


@lru_cache(maxsize=1)
def _breed_meta_snapshot():
    options = defaultdict(list)
    aliases = defaultdict(dict)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT species, breed_name, breed_name_en
            FROM breed_meta
            WHERE species IN ('dog', 'cat')
              AND breed_name IS NOT NULL
              AND breed_name <> ''
            ORDER BY species, breed_name
            """
        )
        rows = cursor.fetchall()

    for species, breed_name, breed_name_en in rows:
        normalized_species = _normalize_species(species)
        canonical_name = _normalize_breed_key(breed_name)
        english_name = _normalize_breed_key(breed_name_en)
        if not normalized_species or not canonical_name:
            continue

        if canonical_name not in options[normalized_species]:
            options[normalized_species].append(canonical_name)

        _register_alias(aliases[normalized_species], canonical_name, canonical_name)
        if english_name:
            _register_alias(aliases[normalized_species], canonical_name, english_name)

    _apply_builtin_breeds(options, aliases)

    return {key: list(values) for key, values in options.items()}, {key: dict(values) for key, values in aliases.items()}


def get_breed_options(species):
    options, _ = _breed_meta_snapshot()
    return options.get(_normalize_species(species), [])


def get_breed_search_options(species):
    normalized_species = _normalize_species(species)
    species_options, species_aliases = _breed_meta_snapshot()
    canonical_names = species_options.get(normalized_species, [])
    alias_lookup = species_aliases.get(normalized_species, {})

    reverse_aliases = defaultdict(list)
    for alias_key, canonical_name in alias_lookup.items():
        if alias_key not in reverse_aliases[canonical_name]:
            reverse_aliases[canonical_name].append(alias_key)

    items = []
    for canonical_name in canonical_names:
        search_terms = []
        for term in [canonical_name, *reverse_aliases.get(canonical_name, [])]:
            if term and term not in search_terms:
                search_terms.append(term)
        items.append(
            {
                "label": canonical_name,
                "search_terms": search_terms,
            }
        )
    return items


def resolve_breed(species, breed):
    normalized_breed = _normalize_breed_key(breed)
    if not normalized_breed:
        return None

    _, aliases = _breed_meta_snapshot()
    species_aliases = aliases.get(_normalize_species(species), {})
    return (
        species_aliases.get(normalized_breed.casefold())
        or species_aliases.get(_collapse_breed_key(normalized_breed).casefold())
    )


def is_valid_breed(species, breed):
    return resolve_breed(species, breed) is not None
