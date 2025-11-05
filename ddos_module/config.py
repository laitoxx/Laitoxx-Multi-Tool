import logging
from pathlib import Path

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    filename=log_dir / "cyberblitz.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

Config = {
    "target_ip": "127.0.0.1",
    "target_url": "http://localhost",
    "port": 80,
    "threads": 100,
    "duration": 60,
    "proxies": [],
    "use_tor": False,
    "tor_library": "torpy",
    "use_proxy": False,
    "proxy_type": "socks5",
    "use_browser": "none",
    "spoofing": {
        "user_agent": True,
        "fingerprint": True,
        "cookies": True,
        "timezone": True,
        "screen_size": True,
        "language": True
    },
    "browser_behavior": {
        "clicks": False,
        "scroll": False,
        "delay": 1
    }
}

def update_Config(**kwargs):
    """Обновление конфигурации"""
    Config.update(kwargs)
    logger.info(f"Конфигурация обновлена: {kwargs}")