from ..shared_utils import Color


def transform_text():
    """
    Transforms input text using a predefined character replacement dictionary.
    """
    translit_dict = {
        "а": "@", "б": "Б", "в": "B", "г": "г", "д": "д", "е": "е", "ё": "ё", "ж": "ж", "з": "3",
        "и": "u", "й": "й", "к": "K", "л": "л", "м": "M", "н": "H", "о": "0", "п": "п", "р": "P",
        "с": "c", "т": "T", "у": "y", "ф": "ф", "х": "X", "ц": "ц", "ч": "4", "ш": "ш", "щ": "щ",
        "ъ": "ъ", "ы": "ы", "ь": "ь", "э": "э", "ю": "ю", "я": "я", "А": "A", "Б": "6", "В": "V",
        "Г": "r", "Д": "D", "Е": "E", "Ё": "Ё", "Ж": "Ж", "З": "2", "И": "I", "Й": "Й", "К": "K",
        "Л": "Л", "М": "M", "Н": "H", "О": "O", "П": "П", "Р": "P",
    }

    input_text = input(f"{Color.DARK_RED}Enter text: {Color.RESET}")
    if input_text is None:
        return

    transformed_text = "".join(translit_dict.get(char, char)
                               for char in input_text)

    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Result: {transformed_text}{Color.RESET}")
