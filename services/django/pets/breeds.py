from collections import defaultdict
from functools import lru_cache

from django.db import connection


SPECIES_KEY_MAP = {
    "dog": "dog",
    "cat": "cat",
    "강아지": "dog",
    "고양이": "cat",
}


def _normalize_species(species):
    return SPECIES_KEY_MAP.get((species or "").strip(), "")


def _normalize_breed_key(value):
    return " ".join(str(value or "").strip().split())


def _collapse_breed_key(value):
    return _normalize_breed_key(value).replace(" ", "")


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

        aliases[normalized_species][canonical_name.casefold()] = canonical_name
        aliases[normalized_species][_collapse_breed_key(canonical_name).casefold()] = canonical_name
        if english_name:
            aliases[normalized_species][english_name.casefold()] = canonical_name
            aliases[normalized_species][_collapse_breed_key(english_name).casefold()] = canonical_name

    return {key: list(values) for key, values in options.items()}, {key: dict(values) for key, values in aliases.items()}


def get_breed_options(species):
    options, _ = _breed_meta_snapshot()
    return options.get(_normalize_species(species), [])


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
