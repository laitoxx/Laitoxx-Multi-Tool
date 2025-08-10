import os
import sys
import requests
import html
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from ..shared_utils import Color

def xss_scan():
    """
    Scans a website for potential XSS vulnerabilities by finding forms and injectable URLs.
    """
    payloads_dir = 'payloads'
    payload_file = 'xsspayloads.txt'
    xss_payloads_path = os.path.join(payloads_dir, payload_file)

    if not os.path.isfile(xss_payloads_path):
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Payload file not found at '{xss_payloads_path}'")
        return

    try:
        with open(xss_payloads_path, 'r', encoding='utf-8', errors='ignore') as file:
            payloads = [line.strip() for line in file if line.strip()]
    except Exception as e:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Error reading payloads file: {e}")
        return

    if not payloads:
        print(f"{Color.DARK_GRAY}[{Color.YELLOW}!{Color.DARK_GRAY}]{Color.YELLOW} No payloads found in the file.")
        return

    print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.WHITE} Loaded {len(payloads)} payloads.")

    base_url = input(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Enter URL to scan (e.g., http://test.com): {Color.RESET}")

    parsed_url = urlparse(base_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Invalid URL format. Please include a scheme (http/https) and a domain.")
        return

    print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Starting scan on {base_url}...")
    
    try:
        response = requests.get(base_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException as e:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Failed to connect to the URL: {e}")
        return

    vulnerabilities_found = 0

    # --- Test Forms ---
    forms = soup.find_all('form')
    print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Found {len(forms)} forms to test.")
    for form in forms:
        action = form.get('action', '')
        form_url = urljoin(base_url, action)
        method = form.get('method', 'get').lower()
        
        inputs = form.find_all(['input', 'textarea', 'select'])
        
        for payload in payloads:
            form_data = {}
            for i in inputs:
                name = i.get('name')
                if name:
                    # Populate all fields, but put payload in one
                    form_data[name] = "test" 
            
            # Test each input field with a payload
            for i in inputs:
                name = i.get('name')
                if not name:
                    continue
                
                temp_data = form_data.copy()
                temp_data[name] = payload

                try:
                    if method == 'post':
                        res = requests.post(form_url, data=temp_data, timeout=5)
                    else:
                        res = requests.get(form_url, params=temp_data, timeout=5)

                    if payload in res.text:
                        vulnerabilities_found += 1
                        print(f"\n{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Potential XSS in form!")
                        print(f"  URL: {Color.WHITE}{form_url}")
                        print(f"  Method: {Color.WHITE}{method.upper()}")
                        print(f"  Vulnerable Parameter: {Color.WHITE}{name}")
                        print(f"  Payload: {Color.WHITE}{payload}")
                        # Don't test this form with other payloads if one is found
                        break 
                except requests.RequestException:
                    continue
            if payload in res.text:
                break


    # --- Test URLs with query parameters ---
    links = soup.find_all('a', href=True)
    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Found {len(links)} links to test for injectable parameters.")
    urls_to_test = set()
    for link in links:
        href = link['href']
        if '?' in href and '=' in href:
            full_url = urljoin(base_url, href)
            urls_to_test.add(full_url)

    for url in urls_to_test:
        parsed = urlparse(url)
        query_params = parsed.query.split('&')
        
        for payload in payloads:
            # Test each parameter
            for i, param in enumerate(query_params):
                if '=' not in param: continue
                
                key = param.split('=')[0]
                
                # Create a new query string with the payload
                test_params = query_params[:]
                test_params[i] = f"{key}={payload}"
                new_query = '&'.join(test_params)
                
                test_url = parsed._replace(query=new_query).geturl()

                try:
                    res = requests.get(test_url, timeout=5)
                    if payload in res.text:
                        vulnerabilities_found += 1
                        print(f"\n{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Potential XSS in URL!")
                        print(f"  URL: {Color.WHITE}{test_url}")
                        print(f"  Vulnerable Parameter: {Color.WHITE}{key}")
                        print(f"  Payload: {Color.WHITE}{payload}")
                        break # Move to next URL
                except requests.RequestException:
                    continue
            if payload in res.text:
                break

    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Scan completed. Found {vulnerabilities_found} potential vulnerabilities.")