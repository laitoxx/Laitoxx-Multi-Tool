import phonenumbers
from phonenumbers import geocoder, carrier, timezone
import requests
from .data_search import _phone_search_flow
from ..shared_utils import Color, USERSBOX_API_KEY

# Shared session (respects proxy settings if available)
try:
    from settings.proxy import make_session
    from settings.app_settings import settings as _app_settings
    _SESSION = make_session(_app_settings.proxy)
except Exception:
    _SESSION = requests.Session()

def search_by_number():
    phone = input(f"{Color.DARK_GRAY}[{Color.DARK_RED}!{Color.DARK_GRAY}]{Color.DARK_RED} Phone number: {Color.RESET}")
    if phone is None:
        return
    phone = phone.strip().replace(" ", "")
    if not phone:
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}!{Color.DARK_GRAY}]{Color.DARK_RED} Empty phone number.")
        return
    phone_for_validation = phone if phone.startswith("+") else f"+{phone}"

    def validate_phone(phone_value):
        try:
            parsed_number = phonenumbers.parse(phone_value, None)
            return phonenumbers.is_valid_number(parsed_number)
        except phonenumbers.phonenumberutil.NumberParseException:
            return False

    if not validate_phone(phone_for_validation):
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Invalid number. Try again (digits, with or without '+').")
        return

    # Basic phone number info
    try:
        parsed_number = phonenumbers.parse(phone_for_validation, None)
        country = geocoder.description_for_number(parsed_number, "en")
        region = carrier.name_for_number(parsed_number, "en")
        time_zones = timezone.time_zones_for_number(parsed_number)
        number_type = "Mobile" if phonenumbers.number_type(parsed_number) == 1 else "Fixed line or other"
        possible_number = phonenumbers.is_possible_number(parsed_number)
        valid_number = phonenumbers.is_valid_number(parsed_number)

        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Mobile number: {phone_for_validation}")
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Country: {country}")
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Carrier: {region}")
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Timezone: {', '.join(time_zones)}")
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Number Type: {number_type}")
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Possible Number: {possible_number}")
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Valid Number: {valid_number}")
        if valid_number:
            region_code = phonenumbers.region_code_for_number(parsed_number)
            print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Region Code: {region_code}")

    except Exception as e:
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} [!] - Error fetching basic phone data: {e} - [!]")

    # --- API Searches ---

    # UserBox Search
    if USERSBOX_API_KEY:
        try:
            headers = {'Authorization': f'Bearer {USERSBOX_API_KEY}'}
            params = {'q': phone}
            response = _SESSION.get("https://api.usersbox.ru/v1/explain", headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            items = data.get('data', {}).get('items', [])
            if items:
                print(f"{Color.DARK_GRAY}[{Color.DARK_RED}!{Color.DARK_GRAY}]{Color.LIGHT_GREEN} UserBox Results:")
                for item in items:
                    database = item.get('source', {}).get('database', 'N/A')
                    collection = item.get('source', {}).get('collection', 'N/A')
                    hits_count = item.get('hits', {}).get('count', 'N/A')
                    print(f"{Color.DARK_GRAY}  - {Color.WHITE}DB: {database}, Collection: {collection}, Found: {hits_count}")
            else:
                print(f"{Color.DARK_GRAY}[{Color.DARK_RED}!{Color.DARK_GRAY}]{Color.DARK_RED} No results from UserBox.")

        except requests.RequestException as e:
            print(f"{Color.DARK_GRAY}[{Color.DARK_RED}!{Color.DARK_GRAY}]{Color.DARK_RED} Error fetching data from UserBox: {e}")
        except ValueError:
            print(f"{Color.DARK_GRAY}[{Color.DARK_RED}!{Color.DARK_GRAY}]{Color.DARK_RED} Could not decode response from UserBox.")
    else:
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}!{Color.DARK_GRAY}]{Color.YELLOW} UserBox: API key not set, skipped.")

    # --- Social Media and Web Searches ---

    # VK Search
    try:
        response = _SESSION.get(f"https://find.vk.com/phone/{phone}", timeout=10)
        if response.status_code == 200 and "User not found" not in response.text:
             print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} VK: response received (verify manually — may require login to confirm).")
        else:
             print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} No user found in VK with this number.")
    except requests.RequestException as e:
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error checking VK: {e}")

    # Avito Search (manual check — search page always returns 200)
    avito_url = f'https://www.avito.ru/rossiya?q={phone}'
    print(f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Avito: manual check required → {avito_url}')

    # --- Data Search (phone) ---
    _phone_search_flow(phone, log=print)

    # --- Direct Links ---
    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Quick Links for further investigation:")
    print(f"  [1] Telegram: t.me/{phone}")
    print(f"  [2] WhatsApp: https://api.whatsapp.com/send/?phone={phone.replace('+', '')}&text&type=phone_number&app_absent=0")
    print(f"  [3] Viber: https://transitapp.com/redirect.html?url=viber://chat?number={phone.replace('+', '')}")
    print(f"  [4] PhoneRadar: https://www.phoneradar.ru/phone/{phone}")
    print(f"  [5] OK.ru Recovery: https://ok.ru/dk?st.cmd=anonymRecoveryStartPhoneLink")
    print(f"  [6] Twitter Recovery: https://twitter.com/account/begin_password_reset")
    print(f"  [7] Facebook Recovery: https://facebook.com/login/identify/?ctx=recover&ars=royal_blue_bar")
    print(f"  [8] Skype Call: skype:{phone}?call")

