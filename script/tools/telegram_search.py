import paketlib
from ..shared_utils import Color

def format_result(result):
    """
    Formats and prints the result from a paketlib search.
    """
    if not result or (isinstance(result, dict) and not result.get('success', True)):
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No results found or an error occurred.")
        return

    if isinstance(result, dict):
        key_colors = {
            "description": Color.LIGHT_GREEN, "name": Color.LIGHT_BLUE,
            "subscribers": Color.LIGHT_PURPLE, "image": Color.CYAN, "tg": Color.YELLOW,
        }
        for key, value in result.items():
            if value:
                label_color = key_colors.get(key, Color.WHITE)
                print(f"  {Color.DARK_GRAY}-{Color.WHITE} {key.capitalize():<15}: {label_color}{value}")

    elif isinstance(result, list):
        for idx, item in enumerate(result, 1):
            print(f"  {Color.DARK_GRAY}[{idx:02d}]{Color.WHITE} {item}")
    else:
        print(f"  {Color.LIGHT_GREEN}{result}")

def telegram_search(config=None):
    """
    Provides a menu to search Telegram using the paketlib library.
    Can be driven by a config dict or by console input.
    """
    search_map = {
        '1': ('Telegram Username', 'TelegramUsername'), '2': ('Telegram Channel', 'TelegramChannel'),
        '3': ('Telegram Chat', 'TelegramChat'), '4': ('Telegram Channel to Parse', 'TelegramCParser')
    }

    if config:
        method_name = config.get("method")
        query = config.get("query")
    else:
        print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Telegram Search Tool")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}1{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Search by Username")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}2{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Search by Channel")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}3{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Search by Chat")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}4{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Parse Channel")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}0{Color.DARK_GRAY}]{Color.LIGHT_RED} Back to Main Menu")
        choice = input(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Select an option: {Color.RESET}").strip()
        if choice == '0' or choice not in search_map:
            print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Invalid or cancelled option.")
            return
        prompt_text, method_name = search_map[choice]
        query = input(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Enter {prompt_text} (e.g., @query): {Color.RESET}").strip()

    if not query or not method_name:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Invalid input. Query and method are required.")
        return

    try:
        print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Searching...")
        search_method = getattr(paketlib.search.Telegram(), method_name)
        result = search_method(query)
        print(f"\n{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Search Result for '{query}':")
        format_result(result)
    except AttributeError:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Error: The search method '{method_name}' does not exist.")
    except Exception as e:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} An unexpected error occurred: {e}")