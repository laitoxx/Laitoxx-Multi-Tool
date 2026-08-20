import webbrowser
from importlib.util import find_spec
from urllib.parse import quote_plus

from laitoxx.features.utilities.shared_utils import Color

IS_GUI = find_spec("PyQt6") is not None

if IS_GUI:
    from .google_osint_dialog import GoogleOsintDialog

from .google_dorks import OPERATORS


def google_osint():
    """
    Constructs advanced Google dorking queries and opens them in the browser.
    """
    from .google_osint import manual_dork_builder, show_dork_examples

    if IS_GUI:
        import inspect

        for frame in inspect.stack():
            if "MainWindow" in str(frame.frame.f_code):
                main_window = frame.frame.f_locals.get("self")
                if main_window:
                    dialog = GoogleOsintDialog(main_window)
                    dialog.exec()
                    return

    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Google OSINT Dork Builder")
    print(f"{Color.DARK_GRAY}Build advanced Google dorks with multiple operators.")

    operators = OPERATORS

    print(f"\n{Color.DARK_GRAY}Available Dork Operators:")
    for key, op in operators.items():
        print(f"{Color.LIGHT_BLUE}{key:>2}.{Color.RESET} {op['name']:<12} - {op['desc']}")

    print(f"\n{Color.DARK_GRAY}Usage:")
    print(f"{Color.GRAY}- Select operators by number (comma-separated for multiple)")
    print(f"{Color.GRAY}- Enter '0' to build custom query manually")
    print(f"{Color.GRAY}- Enter 'help' to see examples")

    choice = input(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Select operators (e.g., 1,2,3): {Color.RESET}"
    ).strip()

    if choice.lower() == "help":
        show_dork_examples()
        return google_osint()  # Restart after showing help

    if choice == "0":
        return manual_dork_builder()

    selected_ops = []
    if choice:
        choices = [c.strip() for c in choice.split(",")]
        for c in choices:
            if c in operators:
                selected_ops.append(operators[c])
            else:
                print(f"{Color.DARK_GRAY}[{Color.YELLOW}⚠{Color.DARK_GRAY}]{Color.YELLOW} Invalid choice: {c}")

    if not selected_ops:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No valid operators selected!")
        return

    query_parts = []

    for op in selected_ops:
        op_name = op["name"]
        if op_name == "custom":
            custom_op = input(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Enter custom operator: {Color.RESET}"
            ).strip()
            if ":" in custom_op:
                op_name, value = custom_op.split(":", 1)
                query_parts.append(f"{op_name}:{value}")
            else:
                query_parts.append(custom_op)
        else:
            value = input(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Enter value for '{op_name}': {Color.RESET}"
            ).strip()
            if value:
                if op_name in ["numrange", "daterange"]:
                    query_parts.append(f"{value}")
                elif op_name in ["before", "after"]:
                    query_parts.append(f"{op_name}:{value}")
                else:
                    query_parts.append(f"{op_name}:{value}")

    base_query = input(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Enter base search terms (optional): {Color.RESET}"
    ).strip()
    if base_query:
        query_parts.insert(0, base_query)

    if not query_parts:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No query components provided!")
        return

    final_query = " ".join(query_parts)

    print(f"\n{Color.DARK_GRAY}Available Search Engines:")
    print(f"{Color.LIGHT_BLUE}1.{Color.RESET} Google (recommended for most dorks)")
    print(f"{Color.LIGHT_BLUE}2.{Color.RESET} Bing (good for NEAR/n and advanced operators)")
    print(f"{Color.LIGHT_BLUE}3.{Color.RESET} DuckDuckGo (privacy-focused)")
    print(f"{Color.LIGHT_BLUE}4.{Color.RESET} Yandex (good for Russian content)")
    print(f"{Color.LIGHT_BLUE}5.{Color.RESET} All engines")

    engine_choice = input(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Select search engines (comma-separated, default=1): {Color.RESET}"
    ).strip()

    if not engine_choice:
        engine_choice = "1"

    selected_engines = []
    choices = [c.strip() for c in engine_choice.split(",")]
    engines_map = {
        "1": "google",
        "2": "bing",
        "3": "duckduckgo",
        "4": "yandex",
        "5": "all",
    }

    for choice in choices:
        if choice in engines_map:
            if engines_map[choice] == "all":
                selected_engines = ["google", "bing", "duckduckgo", "yandex"]
                break
            else:
                selected_engines.append(engines_map[choice])

    if not selected_engines:
        selected_engines = ["google"]

    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Generated Dork:")
    print(f"{Color.LIGHT_BLUE}{final_query}{Color.RESET}")

    for engine in selected_engines:
        if engine == "google":
            url = f"https://www.google.com/search?q={quote_plus(final_query)}"
        elif engine == "bing":
            url = f"https://www.bing.com/search?q={quote_plus(final_query)}"
        elif engine == "duckduckgo":
            url = f"https://duckduckgo.com/?q={quote_plus(final_query)}"
        elif engine == "yandex":
            url = f"https://yandex.ru/search/?text={quote_plus(final_query)}"

        print(
            f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Opening {engine.upper()} search:"
        )
        print(f"{Color.LIGHT_BLUE}{url}{Color.RESET}")

        try:
            webbrowser.open(url)
            print(
                f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} {engine.upper()} search opened successfully."
            )
        except Exception as e:
            print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Could not open {engine}: {e}")
            print(f"{Color.GRAY}You can manually copy the link above.")
