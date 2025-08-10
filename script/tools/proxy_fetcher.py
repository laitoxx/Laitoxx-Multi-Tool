import requests
from ..shared_utils import Color

def get_proxy_list():
    """
    Fetches a list of free proxies from proxyscrape.com and displays them.
    """
    proxy_api_url = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all"

    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Fetching proxy list from proxyscrape.com...")

    try:
        response = requests.get(proxy_api_url, timeout=15)
        response.raise_for_status()

        proxy_list = response.text.strip().split("\r\n")

        if proxy_list and proxy_list[0]:
            print(f"\n{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Successfully fetched {len(proxy_list)} proxies:")

            # Ask user if they want to see the list
            show_list = input(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Do you want to display the full list? (y/n) [default: n]: {Color.RESET}")
            if show_list is None:
                return
            show_list = show_list.strip().lower()

            if show_list == 'y':
                for i, proxy in enumerate(proxy_list):
                    print(f"  {Color.DARK_GRAY}[{i+1:03d}]{Color.WHITE} {proxy}")

            # Save to file option
            save_to_file = input(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Do you want to save the list to a file? (y/n) [default: y]: {Color.RESET}")
            if save_to_file is None:
                return
            save_to_file = save_to_file.strip().lower()

            if save_to_file != 'n':
                filename = "proxies.txt"
                with open(filename, 'w') as f:
                    f.write("\n".join(proxy_list))
                print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Proxy list saved to {filename}")
        else:
             print(f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Failed to fetch proxy list. The API returned an empty list.")

    except requests.exceptions.Timeout:
        print(f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} The request timed out. The API might be down or your connection is slow.")
    except requests.exceptions.RequestException as e:
        print(f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} An error occurred while fetching proxies: {e}")
