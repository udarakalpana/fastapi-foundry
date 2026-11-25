"""Word helpers shared by the generators that derive names from PascalCase classes.

Models derive table names and controllers derive route paths from their class
names, so both need the same snake_case splitting and English plurals.
"""

import re

# Word boundaries in PascalCase: "OrderItem" -> "Order|Item", "HTTPClient" -> "HTTP|Client".
_WORD_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def snake_case(name: str) -> str:
    """Return PascalCase ``name`` in snake_case (``OrderItem`` -> ``order_item``)."""
    return _WORD_BOUNDARY.sub("_", name).lower()


def pluralize(word: str) -> str:
    """English plural for the common cases; good enough for a default name."""
    if len(word) > 1 and word.endswith("y") and word[-2] not in "aeiou":
        return word[:-1] + "ies"
    if word.endswith(("s", "x", "z", "ch", "sh")):
        return word + "es"
    return word + "s"


def singularize(word: str) -> str:
    """Undo :func:`pluralize` for the common cases, leaving other words alone."""
    if len(word) > 3 and word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("es") and word[:-2].endswith(("ss", "us", "x", "ch", "sh")):
        return word[:-2]
    if len(word) > 1 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word
