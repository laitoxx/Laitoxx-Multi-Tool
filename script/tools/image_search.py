"""
image_search.py — Бэкенд для обратного поиска изображений в LAITOXX.

Загружает изображение на reverseimg.net (с fallback на imgbb),
строит поисковые URL для всех доступных движков и выводит их через print().
"""
from __future__ import annotations

import os
import base64
import urllib.parse

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ───────────────────────────────────────────────────────────────
# Поисковые движки
# ───────────────────────────────────────────────────────────────

ALL_ENGINES: dict[str, str] = {
    "Yandex":      "https://yandex.com/images/search?rpt=imageview&url={url}",
    "Google Lens": "https://lens.google.com/uploadbyurl?url={url}",
    "Bing":        "https://www.bing.com/images/search?view=detailv2&iss=sbi&FORM=SBIHMP&sbisrc=UrlPaste&q=imgurl:{url}",
    "TinEye":      "https://tineye.com/search?url={url}",
    "SauceNao":    "https://saucenao.com/search.php?url={url}",
    "IQDB":        "https://iqdb.org/?url={url}",
    "Ascii2D":     "https://ascii2d.net/search/url/{url}",
    "TraceMoe":    "https://trace.moe/?url={url}",
    "Baidu":       "https://graph.baidu.com/details?isfrom=pc&image={url}",
    "Sogou":       "https://pic.sogou.com/ris?query={url}",
}


# ───────────────────────────────────────────────────────────────
# Загрузка изображения
# ───────────────────────────────────────────────────────────────

def _encode_image_b64(file_path: str) -> str:
    """Читает файл и возвращает base64-строку."""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _upload_reverseimg(b64: str) -> str:
    """Загружает изображение на reverseimg.net. Возвращает URL."""
    import requests
    url = "https://reverseimg.net/api/upload"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) "
            "Gecko/20100101 Firefox/149.0"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://reverseimg.net/",
        "Content-Type": "application/json",
        "Origin": "https://reverseimg.net",
        "DNT": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    payload = {"imageBase64": b64}
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "url" not in data:
        raise ValueError(f"reverseimg.net: нет поля 'url' в ответе: {data}")
    return data["url"]


def _upload_imgbb(b64: str) -> str:
    """Fallback: загружает на imgbb (без API-ключа — публичный эндпоинт)."""
    import requests
    resp = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": "public", "image": b64},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["data"]["url"]


def upload_image(file_path: str) -> str:
    """
    Загружает изображение на хостинг и возвращает публичный URL.
    Сначала пробует reverseimg.net, при ошибке — imgbb.
    """
    if not HAS_REQUESTS:
        raise ImportError("Библиотека 'requests' не установлена.")
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    b64 = _encode_image_b64(file_path)

    print("[*] Загрузка изображения на reverseimg.net...")
    try:
        image_url = _upload_reverseimg(b64)
        print(f"[+] Изображение загружено: {image_url}")
        return image_url
    except Exception as e:
        print(f"[-] reverseimg.net недоступен ({e}), пробуем imgbb...")

    try:
        image_url = _upload_imgbb(b64)
        print(f"[+] Изображение загружено (imgbb): {image_url}")
        return image_url
    except Exception as e2:
        raise RuntimeError(
            f"Не удалось загрузить изображение ни на один хостинг. "
            f"Последняя ошибка: {e2}"
        ) from e2


# ───────────────────────────────────────────────────────────────
# Построение поисковых URL
# ───────────────────────────────────────────────────────────────

def build_search_urls(image_url: str, engines: list[str] | None = None) -> dict[str, str]:
    """
    Строит поисковые URL для указанных движков.
    Если engines=None — возвращает все движки.
    """
    encoded = urllib.parse.quote(image_url, safe="")
    result: dict[str, str] = {}
    selected = engines if engines is not None else list(ALL_ENGINES.keys())
    for engine in selected:
        template = ALL_ENGINES.get(engine)
        if template:
            result[engine] = template.format(url=encoded)
    return result


# ───────────────────────────────────────────────────────────────
# Основная функция-инструмент
# ───────────────────────────────────────────────────────────────

def image_search_tool(data: dict) -> None:
    """
    Точка входа для tool_registry.

    data:
      file_path     (str)        — путь к локальному файлу изображения
      search_engines (list[str]) — список движков; если пуст/отсутствует — все
    """
    file_path: str = data.get("file_path", "").strip().strip('"').strip("'")
    engines: list[str] | None = data.get("search_engines") or None

    if not file_path:
        print("[-] Путь к файлу не указан.")
        return

    try:
        image_url = upload_image(file_path)
    except Exception as e:
        print(f"[-] Ошибка загрузки: {e}")
        return

    urls = build_search_urls(image_url, engines)

    print()
    print("=" * 60)
    print("  РЕЗУЛЬТАТЫ ОБРАТНОГО ПОИСКА ИЗОБРАЖЕНИЙ")
    print("=" * 60)
    print(f"  URL изображения: {image_url}")
    print("=" * 60)

    for engine, link in urls.items():
        print(f"\n[{engine}]:\n{link}")

    print("\n[✓] Готово.")
