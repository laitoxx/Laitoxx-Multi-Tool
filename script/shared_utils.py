# shared_utils.py
from colorama import Fore, init
from pystyle import Anime, Colors, Colorate, Center
from telegraph import Telegraph

# Инициализация colorama
init(autoreset=True)

# --- Класс для цветов консоли ---


class Color:
    DARK_RED = Fore.RED
    DARK_GRAY = Fore.LIGHTBLACK_EX
    WHITE = Fore.WHITE
    RESET = Fore.RESET
    LIGHT_RED = Fore.LIGHTRED_EX
    RED = Fore.RED
    GRAY = Fore.LIGHTWHITE_EX
    LIGHT_GREEN = Fore.LIGHTGREEN_EX
    GREEN = Fore.GREEN
    DARK_GREEN = Fore.GREEN
    LIGHT_PURPLE = Fore.LIGHTMAGENTA_EX
    PURPLE = Fore.MAGENTA
    DARK_PURPLE = Fore.MAGENTA
    LIGHT_BLUE = Fore.LIGHTBLUE_EX
    BLUE = Fore.BLUE
    DARK_BLUE = Fore.BLUE
    YELLOW = Fore.YELLOW
    CYAN = Fore.CYAN


# --- Глобальные константы и переменные ---

MAX_TITLE_LENGTH = 30
current_color_scheme = 'red'

# Инициализация Telegraph
try:
    telegraph = Telegraph()
    telegraph.create_account(short_name='console_app')
except Exception as e:
    print(f"Could not initialize Telegraph: {e}")
    telegraph = None

# --- Тексты баннеров ---
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

             Laitoxx deanon tool! By: Asoru Telegram: @perehodasoru
                               Press to Enter
"""


def show_intro():
    Anime.Fade(Center.Center(intro), Colors.black_to_red,
               Colorate.Vertical, interval=0.045, enter=True)

# --- Функции для управления цветом ---


def change_color_scheme(scheme):
    global current_color_scheme, Color
    current_color_scheme = scheme
    if scheme == 'green':
        Color.LIGHT_RED, Color.RED, Color.DARK_RED = Color.LIGHT_GREEN, Color.GREEN, Color.DARK_GREEN
    elif scheme == 'blue':
        Color.LIGHT_RED, Color.RED, Color.DARK_RED = Color.LIGHT_BLUE, Color.BLUE, Color.DARK_BLUE
    elif scheme == 'purple':
        Color.LIGHT_RED, Color.RED, Color.DARK_RED = Color.LIGHT_PURPLE, Color.PURPLE, Color.DARK_PURPLE
    elif scheme == 'yellow':
        Color.LIGHT_RED, Color.RED, Color.DARK_RED = Color.YELLOW, Color.YELLOW, Fore.YELLOW
    elif scheme == 'cyan':
        Color.LIGHT_RED, Color.RED, Color.DARK_RED = Color.CYAN, Color.CYAN, Fore.CYAN
    elif scheme == 'grayscale':
        Color.LIGHT_RED, Color.RED, Color.DARK_RED = Color.WHITE, Color.GRAY, Color.DARK_GRAY
    else:  # red (default)
        Color.LIGHT_RED, Color.RED, Color.DARK_RED = Fore.LIGHTRED_EX, Fore.RED, Fore.RED


def gradient_text(text, color_scheme):
    color_schemes = {
        'red': [Color.LIGHT_RED, Color.RED, Color.DARK_RED, Color.DARK_GRAY, Color.GRAY],
        'green': [Color.LIGHT_GREEN, Color.GREEN, Color.DARK_GREEN, Color.DARK_GRAY, Color.GRAY],
        'blue': [Color.LIGHT_BLUE, Color.BLUE, Color.DARK_BLUE, Color.DARK_GRAY, Color.GRAY],
        'purple': [Color.LIGHT_PURPLE, Color.PURPLE, Color.DARK_PURPLE, Color.DARK_GRAY, Color.GRAY],
        'yellow': [Color.YELLOW, Color.YELLOW, Color.DARK_GRAY, Color.GRAY],
        'cyan': [Color.CYAN, Color.CYAN, Color.DARK_GRAY, Color.GRAY],
        'grayscale': [Color.WHITE, Color.GRAY, Color.DARK_GRAY]
    }
    selected_colors = color_schemes.get(color_scheme, color_schemes['red'])
    num_colors = len(selected_colors)
    gradient_steps = max(len(text) // num_colors, 1)
    gradient_result = ""
    for i, char in enumerate(text):
        color_index = min(i // gradient_steps, num_colors - 1)
        gradient_result += f"{selected_colors[color_index]}{char}"
    return f"{gradient_result}{Color.RESET}"
