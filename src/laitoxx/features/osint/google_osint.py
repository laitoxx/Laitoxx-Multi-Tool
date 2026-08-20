import webbrowser
from urllib.parse import quote_plus

from laitoxx.features.utilities.shared_utils import Color

from .google_osint_cli import google_osint as google_osint


def manual_dork_builder():
    """Manual dork query builder for advanced users."""
    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Manual Dork Builder")
    print(f"{Color.DARK_GRAY}Enter your complete dork query manually.")

    query = input(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Enter your dork query: {Color.RESET}"
    ).strip()

    if not query:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No query provided!")
        return

    # Ask user which search engines to use
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

    for engine in selected_engines:
        if engine == "google":
            url = f"https://www.google.com/search?q={quote_plus(query)}"
        elif engine == "bing":
            url = f"https://www.bing.com/search?q={quote_plus(query)}"
        elif engine == "duckduckgo":
            url = f"https://duckduckgo.com/?q={quote_plus(query)}"
        elif engine == "yandex":
            url = f"https://yandex.ru/search/?text={quote_plus(query)}"

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


def show_dork_examples():
    """Display examples of common Google dorks."""
    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Google Dork Examples")
    print(f"{Color.DARK_GRAY}📚 Advanced Dork Examples with Explanations:")

    examples = [
        ("site:example.com inurl:admin", "Find admin pages on a specific site"),
        (
            "filetype:pdf site:gov confidential",
            "Find confidential PDFs on government sites",
        ),
        ("inurl:login.asp intitle:admin", "Find ASP login pages with admin in title"),
        (
            "site:example.com ext:sql intext:password",
            "Find SQL files with passwords on a site",
        ),
        ('"tesla" AROUND(5) "battery"', "Find Tesla and battery within 5 words"),
        ('"AI" NEAR/3 "ethics"', "Find AI and ethics within 3 words (Bing/SQL)"),
        ('"quantum" BEFORE "mechanics"', "Find quantum before mechanics"),
        ('intitle:"index of" "parent directory"', "Find open directories"),
        ('inurl:"/phpinfo.php"', "Find PHP info disclosure pages"),
        (
            "ext:(sql|db|bak|conf) intext:password",
            "Find exposed database files with passwords",
        ),
        (
            'site:github.com "password" filetype:env',
            "Find exposed .env files on GitHub",
        ),
        (
            'inanchor:"click here" site:example.com',
            "Find pages linking with 'click here'",
        ),
        ("allinurl: admin login site:example.com", "All words in URL on specific site"),
        ('allintitle:"login admin" site:example.com', "All words in title"),
        (
            '"data science" after:2022 before:2024',
            "Data science content from 2022-2024",
        ),
        ("site:news.com daterange:20230101-20231231", "News from 2023"),
        ("numrange:1-100 filetype:xls", "Excel files with numbers 1-100"),
        ('source:bbc "Ukraine"', "BBC news about Ukraine"),
        ("define:entropy", "Definition of entropy"),
        ("phonebook:John Doe New York", "Phonebook search"),
        ("weather:New York", "Weather in New York"),
        ("stocks:AAPL", "Apple stock information"),
        ('movie:"The Matrix"', "Information about The Matrix"),
        ('book:"Python programming"', "Python programming books"),
        ('"best _ in the world"', "Fill in the blank with one word"),
        ('"the best * ever"', "Fill in the blank with any words"),
        (
            '("login" OR "admin") NEAR/5 "password" site:example.com',
            "Login/admin near password",
        ),
        (
            "(site:example.com OR site:example.org) filetype:pdf confidential",
            "Confidential PDFs on multiple sites",
        ),
        (
            'ext:sql -site:github.com intext:"DROP TABLE"',
            "SQL files with DROP TABLE (excluding GitHub)",
        ),
        ("cache:bbc.com", "Google's cached version of BBC"),
        ("related:openai.com", "Sites related to OpenAI"),
        ("info:example.com", "Information about a site"),
        ("link:example.com", "Pages linking to example.com"),
    ]

    for i, (example, description) in enumerate(examples, 1):
        print(f"{Color.LIGHT_BLUE}{i:2d}.{Color.RESET} {Color.LIGHT_GREEN}{example}{Color.RESET}")
        print(f"{Color.GRAY}   └─ {description}{Color.RESET}")

    print(f"\n{Color.DARK_GRAY}💡 Pro Tips:")
    print(f"{Color.GRAY}• Combine operators for powerful searches")
    print(f"{Color.GRAY}• Use quotes for exact phrases")
    print(f"{Color.GRAY}• AROUND(n) works best in Google, NEAR/n in Bing")
    print(f"{Color.GRAY}• Some operators may not work in all search engines")

    input(f"\n{Color.GRAY}Press Enter to continue...{Color.RESET}")
