"""
 @@@  @@@  @@@@@@  @@@@@@@ @@@@@@@  @@@@@@@  @@@ @@@@@@@@ @@@ @@@
 @@!  @@@ @@!  @@@   @@!   @@!  @@@ @@!  @@@ @@! @@!      @@! !@@
 @!@!@!@! @!@  !@!   @!!   @!@  !@! @!@!!@!  !!@ @!!!:!    !@!@! 
 !!:  !!! !!:  !!!   !!:   !!:  !!! !!: :!!  !!: !!:        !!:  
  :   : :  : :. :     :    :: :  :   :   : : :    :         .:   
                                                                 
    HOTDRIFY cooked with the refactor for the LAITOXX squad.
                    github.com/hotdrify
                      t.me/hotdrify

                    github.com/laitoxx
                      t.me/laitoxx
"""

import concurrent.futures
from urllib.parse import urljoin

import requests

from ..shared_utils import Color


def check_path(url, path, session):
    full_url = urljoin(url, path)
    try:
        response = session.get(full_url, timeout=5, allow_redirects=True)
        if response.status_code == 200 and ('login' in response.text.lower() or 'admin' in response.text.lower() or 'dashboard' in response.text.lower()):
            return full_url
    except requests.RequestException:
        pass
    return None


def find_admin_panel():
    url = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} Enter the URL to scan: {Color.RESET}").strip()

    if not url:
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No URL entered.")
        return

    if not (url.startswith("http://") or url.startswith("https://")):
        url = "http://" + url
        print(
            f"{Color.DARK_GRAY}[{Color.LIGHT_BLUE}i{Color.DARK_GRAY}]{Color.LIGHT_BLUE} No scheme provided, defaulting to http. URL is now: {url}")

    admin_paths = [
        "admin/", "admin.php", "administrator/", "admin/login.php", "login.php", "admin_panel/", "admin-area/",
        "admin_login.php", "admin/index.php", "admincp/", "user.php", "controlpanel/", "dashboard/", "panel/",
        "manage/", "admin/account.php", "admin/home.php", "cpanel/", "backend/", "admin1/", "admin2/", "moderator/",
        "webadmin/", "siteadmin/", "login/", "auth/", "signin/", "wp-login.php", "wp-admin/"
    ]

    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Scanning {url} for admin panels using {len(admin_paths)} paths...")

    found_panels = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        with requests.Session() as session:
            future_to_path = {executor.submit(
                check_path, url, path, session): path for path in admin_paths}

            for i, future in enumerate(concurrent.futures.as_completed(future_to_path)):
                result = future.result()
                if result:
                    print(
                        f"\n{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Admin panel found: {Color.WHITE}{result}")
                    found_panels.append(result)

                print(
                    f"\r{Color.DARK_GRAY}Progress: {i+1}/{len(admin_paths)} paths checked...", end="")

    print("\n")
    if not found_panels:
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No admin panels found from the common list.")
    else:
        print(
            f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Scan complete. Found {len(found_panels)} potential panel(s).")
