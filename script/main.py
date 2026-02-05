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

import os
import sys
import time
import traceback

from shared_utils import Color, banner_text, gradient_text, show_intro
from tools.admin_finder import find_admin_panel
from tools.data_search import data_search_tool
from tools.db_searcher import search_database
from tools.email_validator import check_email_address
from tools.gmail_osint import gmail_osint
from tools.google_osint import google_osint
from tools.ip_info import get_ip
from tools.ip_logger import logger_ip
from tools.mac_lookup import search_mac_address
from tools.obfuscator import obfuscate_tool
from tools.password_generator import password_generator_tool
from tools.phishing_bot import phishing
from tools.port_scanner import port_scanner_tool
from tools.proxy_fetcher import get_proxy_list
from tools.site_checker import check_site
from tools.sql_scanner import sql_injection_scanner_tool
from tools.subdomain_finder import find_subdomains
from tools.telegram_search import telegram_search
from tools.temp_mail import temp_mail
from tools.text_transformer import transform_text
from tools.url_checker import check_url
from tools.user_checker import check_username
from tools.user_search_by_phone import search_by_number
from tools.web_crawler import web_crawler
from tools.website_info import get_website_info
from tools.xss_scanner import xss_scan

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def _install_recursion_logger():
    def _hook(exc_type, exc_value, exc_tb):
        try:
            if issubclass(exc_type, RecursionError):
                tb_text = ''.join(traceback.format_exception(
                    exc_type, exc_value, exc_tb))
                import datetime
                logs_dir = os.path.join(os.path.dirname(
                    os.path.abspath(__file__)), '..', 'logs')
                os.makedirs(logs_dir, exist_ok=True)
                filename = os.path.join(
                    logs_dir, f"recursion_traceback_console_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(tb_text)
                sys.stderr.write(
                    f"RecursionError captured and written to {filename}\n")
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


_install_recursion_logger()


def display_main_menu():
    print(f"""{gradient_text(banner_text, Color.current_color_scheme)}                      
                            {Color.DARK_GRAY}Telegram: {Color.DARK_RED}@asoruperehod
        {Color.DARK_RED}╭──                        ──╮   {Color.DARK_RED}╭──                       ──╮
            {Color.DARK_GRAY}[{Color.DARK_RED}1{Color.DARK_GRAY}] {Color.DARK_RED}Check Phone Number           {Color.DARK_GRAY}[{Color.DARK_RED}2{Color.DARK_GRAY}] {Color.DARK_RED}Check IP
            {Color.DARK_GRAY}[{Color.DARK_RED}3{Color.DARK_GRAY}] {Color.DARK_RED}Validate Email               {Color.DARK_GRAY}[{Color.DARK_RED}4{Color.DARK_GRAY}] {Color.DARK_RED}About the Software
            {Color.DARK_GRAY}[{Color.DARK_RED}5{Color.DARK_GRAY}] {Color.DARK_RED}Support the Author           {Color.DARK_GRAY}[{Color.DARK_RED}6{Color.DARK_GRAY}] {Color.DARK_RED}Info Website
            {Color.DARK_GRAY}[{Color.DARK_RED}7{Color.DARK_GRAY}] {Color.DARK_RED}Data Search                  {Color.DARK_GRAY}[{Color.DARK_RED}8{Color.DARK_GRAY}] {Color.DARK_RED}Strange Text
            {Color.DARK_GRAY}[{Color.DARK_RED}9{Color.DARK_GRAY}] {Color.DARK_RED}Password Generator           {Color.DARK_GRAY}[{Color.DARK_RED}10{Color.DARK_GRAY}] {Color.DARK_RED}Port Scanner
            {Color.DARK_GRAY}[{Color.DARK_RED}11{Color.DARK_GRAY}] {Color.DARK_RED}Temp Mail                   {Color.DARK_GRAY}[{Color.DARK_RED}12{Color.DARK_GRAY}] {Color.DARK_RED}Gmail Osint
            {Color.DARK_GRAY}[{Color.DARK_RED}13{Color.DARK_GRAY}] {Color.DARK_RED}Database search             {Color.DARK_GRAY}[{Color.DARK_RED}14{Color.DARK_GRAY}] {Color.DARK_RED}Get proxy
            {Color.DARK_GRAY}[{Color.DARK_RED}15{Color.DARK_GRAY}] {Color.DARK_RED}Check site                  {Color.DARK_GRAY}[{Color.DARK_RED}16{Color.DARK_GRAY}] {Color.DARK_RED}DDoS Attack (Module)
            {Color.DARK_GRAY}[{Color.DARK_RED}18{Color.DARK_GRAY}] {Color.DARK_RED}Check url                   {Color.DARK_GRAY}[{Color.DARK_RED}19{Color.DARK_GRAY}] {Color.DARK_RED}Xss scan
            {Color.DARK_GRAY}[{Color.DARK_RED}20{Color.DARK_GRAY}] {Color.DARK_RED}Check MAC-address
            {Color.DARK_GRAY}[{Color.DARK_RED}66{Color.DARK_GRAY}] {Color.DARK_RED}Exit  
        {Color.DARK_RED}╰──                        ──╯   {Color.DARK_RED}╰──                       ──╯     
                                   {Color.DARK_GRAY}[{Color.DARK_RED}>{Color.DARK_GRAY}] {Color.DARK_RED}Next                 
    """)


def display_second_menu():
    banner2 = f"""{gradient_text(banner_text, Color.current_color_scheme)}                      
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
    print(banner2)


def main():
    show_intro()

    actions = {
        '1': search_by_number, '2': get_ip, '3': check_email_address,
        '6': get_website_info, '7': data_search_tool, '8': transform_text, '9': password_generator_tool,
        '10': port_scanner_tool, '11': temp_mail, '12': gmail_osint,
        '13': search_database, '14': get_proxy_list, '15': check_site,
        '18': check_url, '19': xss_scan, '20': search_mac_address,
        '21': find_admin_panel, '22': sql_injection_scanner_tool, '23': find_subdomains,
        '24': logger_ip, '25': google_osint, '26': telegram_search,
        '27': check_username, '28': obfuscate_tool, '29': web_crawler, '30': phishing
    }

    current_menu = 'main'

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        if current_menu == 'main':
            display_main_menu()
        else:
            display_second_menu()

        prompt_text = f"{Color.DARK_GRAY}╭───({Color.DARK_RED}admin@laitoxx{Color.DARK_GRAY})─[{Color.DARK_RED}~/Laitoxx/{current_menu}_menu{Color.DARK_GRAY}]\n╰──{Color.DARK_RED}$ "
        select = input(prompt_text).strip()

        if select == '>' and current_menu == 'main':
            current_menu = 'second'
            continue
        elif select == '<' and current_menu == 'second':
            current_menu = 'main'
            continue
        elif select == '66':
            break
        elif select == '4':
            print("""... About text ...""")
            input("\nPress Enter...")
        elif select == '5':
            print("""... Support text ...""")
            input("\nPress Enter...")
        elif select == '16':
            print(
                f"{Color.LIGHT_RED}DDoS functionality is in a separate module and is not run from here.{Color.RESET}")
            input("\nPress Enter...")
        elif select == 'COLOR':
            pass
        elif select in actions:
            try:
                actions[select]()
            except Exception as e:
                print(
                    f"{Color.RED}An error occurred while running the tool: {e}{Color.RESET}")
            input(
                f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Press Enter to continue.....{Color.RESET}")
        else:
            print(f"{Color.RED}Invalid selection. Please try again.{Color.RESET}")
            time.sleep(1)


if __name__ == "__main__":
    main()
