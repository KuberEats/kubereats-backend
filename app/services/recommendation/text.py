import re


def tokenize(value: str | None):
    if not value:
        return set()

    normalized = value.lower()
    return {
        token
        for token in re.split(r"[\s,，、/|;；:：()（）-]+", normalized)
        if token
    }


def contains_term(value: str | None, term: str):
    return term.lower() in (value or "").lower()


def delivery_minutes(value: str | None):
    if not value:
        return None

    numbers = [int(number) for number in re.findall(r"\d+", value)]

    if not numbers:
        return None

    return sum(numbers) / len(numbers)
