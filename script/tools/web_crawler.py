from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from ..shared_utils import Color


def get_all_links(session, url):
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            absolute_link = urljoin(url, href)
            parsed_link = urlparse(absolute_link)
            clean_link = parsed_link._replace(
                params='', query='', fragment='').geturl()
            links.add(clean_link)
        return links
    except requests.RequestException as e:
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Error fetching {url}: {e}")
        return set()


def web_crawler():
    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Simple Web Crawler")

    seed_url = input(
        f"{Color.DARK_GRAY}  - {Color.WHITE}Enter the seed URL to start crawling from: {Color.RESET}").strip()
    if not seed_url.startswith(('http://', 'https://')):
        seed_url = 'http://' + seed_url

    try:
        max_pages_str = input(
            f"{Color.DARK_GRAY}  - {Color.WHITE}Enter max number of pages to crawl [20]: {Color.RESET}").strip() or "20"
        max_pages = int(max_pages_str)
    except ValueError:
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Invalid number. Using default of 20.")
        max_pages = 20

    to_crawl = deque([seed_url])
    crawled = set()

    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Starting crawl from {seed_url}...")

    with requests.Session() as session:
        while to_crawl and len(crawled) < max_pages:
            url = to_crawl.popleft()
            if url in crawled:
                continue

            print(
                f"{Color.DARK_GRAY}[{len(crawled)+1:02d}]{Color.WHITE} Crawling: {Color.LIGHT_BLUE}{url}")
            crawled.add(url)

            new_links = get_all_links(session, url)

            for link in new_links:
                if urlparse(link).netloc == urlparse(seed_url).netloc and link not in crawled:
                    to_crawl.append(link)

    print(
        f"\n{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Crawl finished. Found {len(crawled)} pages.")

    save_to_file = input(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Do you want to save the list of crawled pages? (y/n) [y]: {Color.RESET}").strip().lower()
    if save_to_file != 'n':
        filename = f"crawled_{urlparse(seed_url).netloc}.txt"
        with open(filename, 'w') as f:
            for page in sorted(list(crawled)):
                f.write(page + '\n')
        print(
            f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Crawled pages saved to {filename}")
