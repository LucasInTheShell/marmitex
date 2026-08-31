VALID_SIZES = frozenset({"P", "M", "G"})
MAX_ITEMS_PER_ORDER = 10
MAX_QUANTITY_PER_ITEM = 10
MAX_TOTAL_QUANTITY = 20


def normalized_cpf(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def normalized_phone(value: str) -> str:
    return "".join(character for character in value if character.isdigit())
