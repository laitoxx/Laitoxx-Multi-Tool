import phonenumbers
from phonenumbers import geocoder, carrier, timezone
import requests
from bs4 import BeautifulSoup
from ..shared_utils import Color, USERSBOX_API_KEY


def search_by_number():
    phone = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Phone number: ")
    if phone is None:
        return

    def validate_phone(phone):
        try:
            parsed_number = phonenumbers.parse(phone, None)
            return phonenumbers.is_valid_number(parsed_number)
        except phonenumbers.phonenumberutil.NumberParseException:
            return False

    if not validate_phone(phone):
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Invalid number. Try again, only without spaces and with '+'.")
        return

    # Basic phone number info
    try:
        parsed_number = phonenumbers.parse(phone, None)
        country = geocoder.description_for_number(parsed_number, "en")
        region = carrier.name_for_number(parsed_number, "en")
        time_zones = timezone.time_zones_for_number(parsed_number)
        number_type = "Mobile" if phonenumbers.number_type(
            parsed_number) == 1 else "Fixed line or other"
        possible_number = phonenumbers.is_possible_number(parsed_number)
        valid_number = phonenumbers.is_valid_number(parsed_number)

        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Mobile number: {phone}")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Country: {country}")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Carrier: {region}")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Timezone: {', '.join(time_zones)}")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Number Type: {number_type}")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Possible Number: {possible_number}")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Valid Number: {valid_number}")
        if valid_number:
            region_code = phonenumbers.region_code_for_number(parsed_number)
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Region Code: {region_code}")

    except Exception as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} [!] - Error fetching basic phone data: {e} - [!]")

    # --- API Searches ---

    # ProxyNova Search
    try:
        # Taking last 11 digits might not be safe for all number formats
        phone_suffix = phone.replace("+", "")[-11:]
        response = requests.get(
            f"https://api.proxynova.com/comb?query={phone_suffix}&start=0&limit=100", allow_redirects=False, timeout=10)
        response.raise_for_status()
        data = response.json()
        lines = data.get("lines", [])
        if lines:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} ProxyNova Results:")
            for line in lines:
                print(f"{Color.DARK_GRAY}  - {Color.WHITE}{line}")
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} No results from ProxyNova.")

    except requests.RequestException as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error fetching data from ProxyNova: {e}")
    except ValueError:  # Catches JSONDecodeError
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Could not decode response from ProxyNova.")

    # UserBox Search
    try:
        headers = {'Authorization': f'Bearer {USERSBOX_API_KEY}'}
        params = {'q': phone}
        response = requests.get(
            "https://api.usersbox.ru/v1/explain", headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        items = data.get('data', {}).get('items', [])
        if items:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} UserBox Results:")
            for item in items:
                database = item.get('source', {}).get('database', 'N/A')
                collection = item.get('source', {}).get('collection', 'N/A')
                hits_count = item.get('hits', {}).get('count', 'N/A')
                print(
                    f"{Color.DARK_GRAY}  - {Color.WHITE}DB: {database}, Collection: {collection}, Found: {hits_count}")
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} No results from UserBox.")

    except requests.RequestException as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error fetching data from UserBox: {e}")
    except ValueError:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Could not decode response from UserBox.")

    # --- Social Media and Web Searches ---

    # VK Search
    try:
        response = requests.get(
            f"https://find.vk.com/phone/{phone}", timeout=10)
        if response.status_code == 200 and "User not found" not in response.text:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} VK profile potentially found! Response length: {len(response.text)}")
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} No user found in VK with this number.")
    except requests.RequestException as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error checking VK: {e}")

    # Avito Search
    try:
        url = f'https://www.avito.ru/rossiya/telefony?q={phone}'
        response = requests.head(url, timeout=10)
        if response.status_code == 200:
            print(
                f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Avito account may exist (link returned 200 OK).')
        else:
            print(
                f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} No Avito account found (link returned {response.status_code}).')
    except requests.RequestException as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error checking Avito: {e}")

    # --- Direct Links ---
    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Quick Links for further investigation:")
    print(f"  [1] Telegram: t.me/{phone}")
    print(
        f"  [2] WhatsApp: https://api.whatsapp.com/send/?phone={phone.replace('+', '')}&text&type=phone_number&app_absent=0")
    print(
        f"  [3] Viber: https://transitapp.com/redirect.html?url=viber://chat?number={phone.replace('+', '')}")
    print(f"  [4] PhoneRadar: https://www.phoneradar.ru/phone/{phone}")
    print(
        "  [5] OK.ru Recovery: https://ok.ru/dk?st.cmd=anonymRecoveryStartPhoneLink")
    print("  [6] Twitter Recovery: https://twitter.com/account/begin_password_reset")
    print("  [7] Facebook Recovery: https://facebook.com/login/identify/?ctx=recover&ars=royal_blue_bar")
    print(f"  [8] Skype Call: skype:{phone}?call")

    # Google Search
    try:
        query = f"https://www.google.com/search?q=\"{phone}\""
        response = requests.get(query, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        search_results = soup.find_all('a')
        links = []
        for result in search_results:
            href = result.get('href')
            if href and href.startswith('/url?q='):
                link = href.replace('/url?q=', '').split('&')[0]
                if not any(x in link for x in ["google.com", "schema.org"]):
                    links.append(link)

        if links:
            print(
                f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Google Search Results:")
            for link in links[:5]:  # Show top 5 results
                print(f"  - {Color.WHITE}{link}")
        else:
            print(
                f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} No direct links found in Google search.")

    except requests.RequestException as e:
        print(
            f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error performing Google search: {e}")
