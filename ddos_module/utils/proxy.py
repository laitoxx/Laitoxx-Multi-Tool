import requests
from torpy.http.requests import tor_requests_session
from ..config import Config, logger
import random
from aiohttp_socks import ProxyConnector

def get_proxies():
    try:
        response = requests.get("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=elite")
        proxies = response.text.splitlines()
        return [{"socks5": f"socks5://{proxy}"} for proxy in proxies if proxy]
    except Exception as e:
        logger.error(f"Ошибка при получении прокси: {e}")
        return []

def get_tor_session():
    """Создание сессии с Tor"""
    if Config["tor_library"] == "torpy":
        return tor_requests_session()
    else:
        return requests.Session()

async def get_async_tor_connector():
    """Создание асинхронного коннектора для Tor"""
    if Config["tor_library"] == "torpy":
        # aiohttp-socks can be used with Tor's SOCKS port
        return ProxyConnector.from_url('socks5://127.0.0.1:9050')
    return None

def get_random_proxy():
    """Выбор случайного прокси"""
    proxies = Config["proxies"] or get_proxies()
    return random.choice(proxies) if proxies else None
