import os
import requests
import telebot
from telebot import types
from dotenv import load_dotenv


telegram_token_bot = os.environ['TELEGRAM_BOT_TOKEN']
bot = telebot.TeleBot(telegram_token_bot) 
load_dotenv()


class GameData:

  
    def __init__(self):
        self.decks = {}

    
    def add_game(self, user_id, deck_id):
        self.decks[user_id] = {
            'deck_id': deck_id,
            'player_hand': [],
            'dealer_hand': [],
            'game_started': False
        }


    def get_game_data(self, user_id):
        return self.decks.get(user_id, None)

game_data = GameData()


def send_message(message, text, reply_markup=None):
    bot.send_message(message.chat.id, text, reply_markup=reply_markup)


def send_card_image(message, image_url):
    bot.send_photo(message.chat.id, image_url)


def create_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('/hit'), types.KeyboardButton('/stand'))
    return keyboard


def card_value_to_int(card_value):
    if card_value.lower() in ['king', 'queen', 'jack']:
        return 10
    elif card_value.lower() == 'ace':
        return 11
    else:
        return int(card_value)


def deal_initial_cards(deck_id):
    player_hand = [draw_card(deck_id), draw_card(deck_id)]
    dealer_hand = [draw_card(deck_id), draw_card(deck_id)]
    return player_hand, dealer_hand


def draw_card(deck_id):
    response = requests.get(f'https://deckofcardsapi.com/api/deck/{deck_id}/draw/?count=1')
    card_info = response.json()['cards'][0]
    image_url = card_info['image']
    return card_info, image_url


def hit(user_id, message):
    global game_data
    game_info = game_data.get_game_data(user_id)
    if game_info is not None:
        card_info, image_url = draw_card(game_info['deck_id'])
        game_info['player_hand'].append(card_info)
        player_score = calculate_score(game_info['player_hand'])
        bot.reply_to(message, f"Вы взяли карту {card_info['value']}. Ваш счет: {player_score}.")
        send_card_image(message, image_url)
        if player_score > 21:
            bot.reply_to(message, "Вы проиграли!")
            end_game(message, False, user_id)
        else:
            send_message(message, "Ваш ход:", create_keyboard())
    else:
        send_message(message, "Начните новую игру с помощью /newgame.")

        
def stand(user_id, message):
    global game_data
    game_info = game_data.get_game_data(user_id)
    if game_info is not None:
        dealer_images = []
        for card in game_info['dealer_hand']:
            dealer_images.append(card['image'])
            send_card_image(message, card['image'])
        while calculate_score(game_info['dealer_hand']) < 17:
            card_info, image_url = draw_card(game_info['deck_id'])
            game_info['dealer_hand'].append(card_info)
            dealer_images.append(image_url)
            send_card_image(message, image_url)
        dealer_score = calculate_score(game_info['dealer_hand'])
        player_score = calculate_score(game_info['player_hand'])
        if dealer_score > 21 or player_score > dealer_score:
            send_message(message, "Вы выиграли!")
        elif dealer_score > player_score:
            send_message(message, "Вы проиграли!")
        else:
            send_message(message, "Ничья!")
        end_game(message, True, user_id)
    else:
        send_message(message, "Начните новую игру с помощью /newgame.")


def calculate_score(hand):
    values = [card_value_to_int(card['value']) for card in hand]
    score = sum(values)
    ace_count = sum(1 for card in hand if card['value'] == 'ACE')
    while score > 21 and ace_count > 0:
        score -= 11
        ace_count -= 1
    return score


def end_game(message, show_balance=True, user_id=None):
    global game_data
    if user_id is not None:
        game_data.decks.pop(user_id, None)
    game_data.game_started = False
    if show_balance:
        send_message(message, "Игра завершена. Используйте /newgame для начала новой игры.")
    else:
        send_message(message, "Игра завершена. Используйте /newgame, чтобы начать новую игру.")


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Добро пожаловать в игру блэкджек! Используйте /newgame для начала новой игры.")


@bot.message_handler(commands=['newgame'])
def start_new_game(message):
    global game_data
    user_id = message.from_user.id
    if user_id not in game_data.decks:
        deck_id = requests.get('https://deckofcardsapi.com/api/deck/new/shuffle/?deck_count=1').json()['deck_id']
        game_data.add_game(user_id, deck_id)
        send_message(message, "Новая игра началась! Используйте /hit, чтобы взять карту")
    else:
        send_message(message, "У вас уже идет игра. Используйте /hit или /stand.")


@bot.message_handler(commands=['hit', 'stand'])
def handle_commands(message):
    global game_data
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_data = bot.get_chat_member(chat_id, user_id)
    if user_data.status not in ["member", "administrator", "creator"]:
        send_message(message, "Вы не можете использовать эти команды.")
        return
    command = message.text.lower()
    if command == '/hit':
        hit(user_id, message)
    elif command == '/stand':
        stand(user_id, message)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.message:
        pass  


bot.polling()
