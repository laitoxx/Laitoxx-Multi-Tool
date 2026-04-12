"""
avatar_downloader.py — Download and cache user avatars.
"""
from __future__ import annotations

import os
import hashlib
import requests
from typing import Optional

# Директория для хранения кэшированных аватаров
_CACHE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "resources", "avatar_cache"
)

# User-Agent для выполнения HTTP-запросов
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class AvatarDownloader:
    """Download avatars from site profile URLs and cache them locally."""

    def __init__(self, cache_dir: Optional[str] = None, proxy: Optional[dict] = None):
        self.cache_dir = cache_dir or _CACHE_DIR
        self.proxy = proxy
        os.makedirs(self.cache_dir, exist_ok=True)

    def _cache_key(self, username: str, site_name: str) -> str:
        """Генерирует уникальный MD5 хеш для комбинации пользователя и сайта."""
        raw = f"{username}@{site_name}".lower()
        return hashlib.md5(raw.encode()).hexdigest()

    def _cache_path(self, username: str, site_name: str) -> str:
        """Возвращает путь к файлу в кэше."""
        key = self._cache_key(username, site_name)
        return os.path.join(self.cache_dir, f"{key}.jpg")

    def get_cached(self, username: str, site_name: str) -> Optional[str]:
        """Проверяет наличие аватара в локальном кэше."""
        path = self._cache_path(username, site_name)
        return path if os.path.exists(path) else None

    def download(self, url: str, username: str, site_name: str) -> Optional[str]:
        """Download avatar from *url*, cache to disk, return local path or None."""
        cached = self.get_cached(username, site_name)
        if cached:
            return cached

        try:
            resp = requests.get(
                url,
                headers={"User-Agent": _UA},
                timeout=10,
                proxies=self.proxy or {},
                stream=True,
            )
            if resp.status_code != 200:
                return None

            # Проверка типа контента (должно быть изображение)
            content_type = resp.headers.get("Content-Type", "")
            if "image" not in content_type and "octet" not in content_type:
                return None

            path = self._cache_path(username, site_name)
            with open(path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)

            # Проверка, что файл не пустой и имеет минимальный размер
            if os.path.getsize(path) < 100:
                os.remove(path)
                return None

            return path
        except Exception:
            return None

    def download_all(self, avatar_urls: dict[str, str], username: str) -> dict[str, str]:
        """
        Download multiple avatars.

        Parameters
        ----------
        avatar_urls : dict[str, str]
            {site_name: avatar_url}
        username : str

        Returns
        -------
        dict[str, str]
            {site_name: local_path} for successfully downloaded avatars.
        """
        result = {}
        for site_name, url in avatar_urls.items():
            path = self.download(url, username, site_name)
            if path:
                result[site_name] = path
        return result

    def clear_cache(self):
        """Remove all cached avatars from the cache directory."""
        if os.path.isdir(self.cache_dir):
            for f in os.listdir(self.cache_dir):
                fp = os.path.join(self.cache_dir, f)
                if os.path.isfile(fp):
                    os.remove(fp)