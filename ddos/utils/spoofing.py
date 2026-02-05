import random
import string

from fake_useragent import UserAgent
from faker import Faker

fake = Faker()
ua = UserAgent()


def generate_spoofed_headers():
    headers = {
        "User-Agent": ua.random,
        "Accept-Language": random.choice(["en-US", "ru-RU", "fr-FR", "de-DE"]),
        "Referer": fake.url(),
        "Accept": random.choice([
            "text/html,application/xhtml+xml",
            "application/json",
            "*/*"
        ])
    }
    return headers


def generate_cookies():
    """Генерация случайных cookies"""
    return {
        "session_id": "".join(random.choices(string.ascii_letters + string.digits, k=32)),
        "user_id": fake.uuid4()
    }


def spoof_fingerprint():
    """Подделка фингерпринта"""
    return {
        "timezone": random.choice(["UTC", "GMT+3", "GMT-5"]),
        "screen_resolution": random.choice(["1920x1080", "1366x768", "1280x720"]),
        "language": random.choice(["en-US", "ru-RU", "fr-FR"])
    }
