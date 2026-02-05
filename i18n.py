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

import json
import os


class I18n:
    def __init__(self, language: str = 'ru') -> None:
        self.language: str = language
        self.translations: dict = self.load_translations()

    def load_translations(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))

        filepath = os.path.join(
            base_dir, '..', 'translations', f'{self.language}.json')

        try:
            with open(filepath, encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            if self.language != 'ru':
                self.language = 'ru'
                return self.load_translations()
            return {}

    def translate(self, key, **kwargs):
        return self.translations.get(key, key).format(**kwargs)


def get_current_language() -> str:
    try:
        with open("language.settings") as file:
            return file.read().strip()
    except FileNotFoundError:
        return 'ru'


i18n = I18n(get_current_language())

TRANSLATIONS = {
    "ru": {
        "app_title": "Laitoxx",
        "search": "Поиск",
        "add_step": "Добавить шаг",
        "remove_step": "Удалить шаг",
        "run_script": "Запустить скрипт",
        "save_script": "Сохранить скрипт",
        "load_script": "Загрузить скрипт",
        "step": "Шаг",
        "function": "Функция",
        "input_from": "Входные данные из",
        "previous_step": "Предыдущий шаг",
        "user_input": "Пользовательский ввод",
        "input_data": "Входные данные",
        "output_parsing": "Парсинг вывода",
        "regex_for_parsing": "REGEX для парсинга",
        "api_key": "API-ключ",
        "settings": "Настройки",
        "language": "Язык",
        "theme": "Тема",
        "save": "Сохранить",
        "script_saved": "Скрипт сохранен",
        "script_loaded": "Скрипт загружен",
        "error": "Ошибка",
        "select_script": "Выберите скрипт для загрузки",
        "enter_script_name": "Введите имя файла для сохранени��",
        "no_function_selected": "Функция не выбрана",
        "input_data_required": "Необходимо ввести входные данные",
        "step_error": "Ошибка на шаге {step_num}: {error}",
        "script_completed": "Скрипт выполнен",
        "script_failed": "Скрипт не выполнен",
        "no_steps": "Нет шагов для выполнения",
        "invalid_json": "Неверный формат JSON файла",
        "select_file": "Выберите файл",
        "file_not_found": "Файл не найден",
        "add_regex": "Добавить REGEX",
        "remove_regex": "Удалить REGEX",
        "change_background": "Изменить фон",
        "change_theme": "Изменить тему",
        "create_color_theme": "Создать цветовую тему",
        "plugin_builder": "Конструктор плагинов",
        "hide_ui": "Скрыть интерфейс",
        "exit": "Выход",
        "information_gathering": "Сбор информации",
        "web_security": "Веб-безопасность",
        "tools_utilities": "Инструменты и утилиты",
        "plugins": "Плагины",
        "Check Phone Number": "Проверить номер телефона",
        "Check IP": "Проверить IP",
        "Validate Email": "Проверить Email",
        "Data Search": "Поиск данных",
        "Info Website": "Информация о сайте",
        "Gmail Osint": "Gmail Osint",
        "Database search": "Поиск по базам данных",
        "Check MAC-address": "Проверить MAC-адрес",
        "Subdomain finder": "Поиск субдоменов",
        "Google Osint": "Google Osint",
        "Telegram (paketlib)": "Telegram (paketlib)",
        "Search Nick": "Поиск по нику",
        "Web-crawler": "Веб-краулер",
        "Port Scanner": "Сканер портов",
        "Check site": "Проверить сайт",
        "Check url": "Проверить URL",
        "Xss scan": "XSS сканнер",
        "Find admin panel": "Поиск админ-панели",
        "Sql scan": "SQL-сканнер",
        "DDoS Attack": "DDoS-атака",
        "Strange Text": "Странный текст",
        "Password Generator": "Генератор паролей",
        "Temp Mail": "Временная почта",
        "Get proxy": "Получить прокси",
        "Ip logger": "IP логгер",
        "Obfuscate python": "Обфускация Python",
        "Phish Bot(lamer)": "Фишинг-бот (lamer)",
        "data_search_title": "Поиск данных",
        "data_search_mode_label": "Тип поиска",
        "data_search_value_label": "Введите значение",
        "data_search_phone_option": "Телефон",
        "data_search_email_option": "Email",
        "data_search_telegram_option": "Telegram",
        "data_search_phone_placeholder": "Введите номер без +",
        "data_search_email_placeholder": "Введите email",
        "data_search_telegram_placeholder": "Введите username без @",
        "plugin_builder_title": "Конструктор плагинов",
        "plugin_name": "Имя плагина",
        "author_name": "Имя автора",
        "website": "Веб-сайт",
        "description": "Описание",
        "supported_os": "Поддерживаемые ОС",
        "continue": "Продолжить",
        "cancel": "Отмена",
        "add_delay": "Добавить задержку",
        "delete_last_step": "Удалить последний шаг",
        "save_plugin": "Сохранить плагин",
        "editing_plugin": "Редактирование: {name}",
        "set_delay_title": "Установить задержку",
        "delay_seconds": "Задержка (секунды)",
        "step_settings_title": "Настройки шага",
        "select_icon": "Выбрать иконку",
        "step_description": "Описание шага",
        "input_source": "Источник ввода",
        "input_source_user": "Пользовательск��й ввод",
        "input_source_none": "Ничего",
        "input_source_previous": "Из: {description}",
        "input_filter_regex": "Фильтр ввода (REGEX)",
        "action_type": "Тип действия",
        "action_type_command": "Командная строка",
        "action_type_function": "Внутренняя функция",
        "action_value": "Действие",
        "requires_api_key": "Требуется API-ключ",
        "plugin_name_label": "Имя плагина:",
        "author_name_label": "Имя автора:",
        "website_label": "Веб-сайт (необязательно):",
        "description_label": "Описание:",
        "step_description_default": "...",
        "delay_duration_seconds": "{duration}с",
        "step_default_name": "Шаг {order}",
        "new_step_default_description": "Новый шаг",
        "image_files_filter": "Файлы изображений (*.png *.jpg)",
        "theme_map": {
            "button_bg_color": "Фон кнопки",
            "button_hover_bg_color": "Фон кнопки при наведении",
            "button_pressed_bg_color": "Фон кнопки при нажатии",
            "button_border_color": "Цвет рамки кнопки",
            "button_text_color": "Цвет текста кнопки",
            "text_area_bg_color": "Фон текстовой области",
            "text_area_border_color": "Цвет рамки текстовой области",
            "text_area_text_color": "Цвет текста текстовой области",
            "sidebar_bg_color": "Фон боковой панели",
            "title_text_color": "Цвет заголовка",
            "scrollbar_handle_color": "Цвет ползунка прокрутки",
            "scrollbar_handle_hover_color": "Цвет ползунка прокрутки при наведении",
            "plugin_canvas_bg_color": "Фон холста плагина"
        },
        "search": "Поиск..."
    },
    "en": {
        "app_title": "Laitoxx",
        "search": "Search...",
        "add_step": "Add Step",
        "remove_step": "Remove Step",
        "run_script": "Run Script",
        "save_script": "Save Script",
        "load_script": "Load Script",
        "step": "Step",
        "function": "Function",
        "input_from": "Input from",
        "previous_step": "Previous Step",
        "user_input": "User Input",
        "input_data": "Input Data",
        "output_parsing": "Output Parsing",
        "regex_for_parsing": "REGEX for parsing",
        "api_key": "API Key",
        "settings": "Settings",
        "language": "Language",
        "theme": "Theme",
        "save": "Save",
        "script_saved": "Script saved",
        "script_loaded": "Script loaded",
        "error": "Error",
        "select_script": "Select a script to load",
        "enter_script_name": "Enter a filename to save",
        "no_function_selected": "No function selected",
        "input_data_required": "Input data is required",
        "step_error": "Error at step {step_num}: {error}",
        "script_completed": "Script completed",
        "script_failed": "Script failed",
        "no_steps": "No steps to run",
        "invalid_json": "Invalid JSON file format",
        "select_file": "Select file",
        "file_not_found": "File not found",
        "add_regex": "Add REGEX",
        "remove_regex": "Remove REGEX",
        "change_background": "Change Background",
        "change_theme": "Change Theme",
        "create_color_theme": "Create Color Theme",
        "plugin_builder": "Plugin Builder",
        "hide_ui": "Hide UI",
        "exit": "Exit",
        "information_gathering": "Information Gathering",
        "web_security": "Web Security",
        "tools_utilities": "Tools & Utilities",
        "plugins": "Plugins",
        "Check Phone Number": "Check Phone Number",
        "Check IP": "Check IP",
        "Validate Email": "Validate Email",
        "Data Search": "Data Search",
        "Info Website": "Info Website",
        "Gmail Osint": "Gmail Osint",
        "Database search": "Database search",
        "Check MAC-address": "Check MAC-address",
        "Subdomain finder": "Subdomain finder",
        "Google Osint": "Google Osint",
        "Telegram (paketlib)": "Telegram (paketlib)",
        "Search Nick": "Search Nick",
        "Web-crawler": "Web-crawler",
        "Port Scanner": "Port Scanner",
        "Check site": "Check site",
        "Check url": "Check url",
        "Xss scan": "Xss scan",
        "Find admin panel": "Find admin panel",
        "Sql scan": "Sql scan",
        "DDoS Attack": "DDoS Attack",
        "Strange Text": "Strange Text",
        "Password Generator": "Password Generator",
        "Temp Mail": "Temp Mail",
        "Get proxy": "Get proxy",
        "Ip logger": "Ip logger",
        "Obfuscate python": "Obfuscate python",
        "Phish Bot(lamer)": "Phish Bot(lamer)",
        "data_search_title": "Data Search",
        "data_search_mode_label": "Search type",
        "data_search_value_label": "Enter value",
        "data_search_phone_option": "Phone",
        "data_search_email_option": "Email",
        "data_search_telegram_option": "Telegram",
        "data_search_phone_placeholder": "Phone without +",
        "data_search_email_placeholder": "Enter email",
        "data_search_telegram_placeholder": "Username without @",
        "plugin_builder_title": "Plugin Builder",
        "plugin_name": "Plugin Name",
        "author_name": "Author Name",
        "website": "Website",
        "description": "Description",
        "supported_os": "Supported OS",
        "continue": "Continue",
        "cancel": "Cancel",
        "add_delay": "Add Delay",
        "delete_last_step": "Delete Last Step",
        "save_plugin": "Save Plugin",
        "editing_plugin": "Editing: {name}",
        "set_delay_title": "Set Delay",
        "delay_seconds": "Delay (seconds)",
        "step_settings_title": "Step Settings",
        "select_icon": "Select Icon",
        "step_description": "Step Description",
        "input_source": "Input Source",
        "input_source_user": "User Input",
        "input_source_none": "None",
        "input_source_previous": "From: {description}",
        "input_filter_regex": "Input Filter (REGEX)",
        "action_type": "Action Type",
        "action_type_command": "Command Line",
        "action_type_function": "Internal Function",
        "action_value": "Action",
        "requires_api_key": "Requires API Key",
        "plugin_name_label": "Plugin Name:",
        "author_name_label": "Author Name:",
        "website_label": "Website (optional):",
        "description_label": "Description:",
        "step_description_default": "...",
        "delay_duration_seconds": "{duration}s",
        "step_default_name": "Step {order}",
        "new_step_default_description": "New Step",
        "image_files_filter": "Image Files (*.png *.jpg)",
        "theme_map": {
            "button_bg_color": "Button Background",
            "button_hover_bg_color": "Button Hover",
            "button_pressed_bg_color": "Button Pressed",
            "button_border_color": "Button Border",
            "button_text_color": "Button Text",
            "text_area_bg_color": "Text Area Background",
            "text_area_border_color": "Text Area Border",
            "text_area_text_color": "Text Area Text",
            "sidebar_bg_color": "Sidebar Background",
            "title_text_color": "Title Text",
            "scrollbar_handle_color": "Scrollbar Handle",
            "scrollbar_handle_hover_color": "Scrollbar Handle Hover",
            "plugin_canvas_bg_color": "Plugin Canvas Background"
        }
    }
}

base_dir: str = os.path.dirname(os.path.abspath(__file__))
translations_dir: str  = os.path.join(base_dir, '..', 'translations')
os.makedirs(translations_dir, exist_ok=True)

for lang, trans_data in TRANSLATIONS.items():
    filepath: str = os.path.join(translations_dir, f'{lang}.json')
    with open(filepath, 'w', encoding='utf-8') as file:
        json.dump(trans_data, file, ensure_ascii=False, indent=4)
