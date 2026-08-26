VALID_SIZES = frozenset({"P", "M", "G"})


def normalized_cpf(value: str) -> str:
    return "".join(character for character in value if character.isdigit())

