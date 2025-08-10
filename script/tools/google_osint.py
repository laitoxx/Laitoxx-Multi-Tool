import webbrowser
from urllib.parse import quote_plus
from ..shared_utils import Color

def google_osint():
    """
    Constructs a Google dorking query and opens it in the user's default web browser.
    """
    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Google OSINT Search")
    print(f"{Color.DARK_GRAY}This tool will construct a search query and open it in your browser.")
    print(f"{Color.GRAY}Example dorks: 'site:example.com', 'inurl:admin', 'filetype:pdf'")

    query = input(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Enter your search query/dork: {Color.RESET}"
    ).strip()

    if not query:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No input provided! Please try again.")
        return

    # Construct the Google search URL
    search_url = f"https://www.google.com/search?q={quote_plus(query)}"

    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Opening the following URL in your browser:")
    print(f"{Color.LIGHT_BLUE}{search_url}{Color.RESET}")

    try:
        # Open the URL in the default web browser
        webbrowser.open(search_url)
        print(f"\n{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Search opened successfully.")
    except Exception as e:
        print(f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Could not open web browser: {e}")
        print(f"{Color.GRAY}You can manually copy the link above.")
