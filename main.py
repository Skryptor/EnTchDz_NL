#from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker
from create_bd import  User, Word, UserProgress
from data_file import engine
import telebot
import random
import configparser
from telebot import types
#import requests
config = configparser.ConfigParser()
config.read('settings.ini')
token = config["TOKEN"]['token']
#token_yandex = config["TOKEN"]['token_yandex']
#url = config["TOKEN"]['url']
Session = sessionmaker(bind=engine)
session = Session()


class Command:
    add_word = 'add words➕'
    next = 'next➡️'
    delete = 'delete🔙'

bot = telebot.TeleBot(token)

def search_user(user_id, user_name,chat_id):
    """
    Эта функция предназначена для проверки есть ли пользователь в БД и дальнейшем добавлении его,
    она проверяет есть ли user с id, chat_id с совпадающим user_name в таблице User.
    :param user_id:
    :param user_name:
    :param chat_id:
    :return:
    """
    user = session.query(User).filter_by(user_id=user_id).first()
    if not user:
        new_user = User(user_name = user_name, chat_id = chat_id, user_id = user_id)
        session.add(new_user)
        session.commit()
        #print(f"✅ Пользователь {user_name} добавлен в БД")
        bot.send_message(chat_id, f"✅ Пользователь {user_name} добавлен в БД чтобы начать напиши /go⬇️ если нужно остановиться пиши /stop")
    else:
        print(f"⚠️ Пользователь {user_name} уже есть в БД")
@bot.message_handler(commands=['start'])
def start_bot(message):
    chat_id = message.chat.id
    bot.send_message(chat_id,
                     'Привет 👋 Давай попрактикуемся в английском языке. Тренировки можешь проходить в удобном для себя темпе.')
    search_user(message.from_user.id, message.from_user.username, message.chat.id)
def create_progress(user_id, words_id, status="learned"):
    """
        Создаёт или обновляет прогресс пользователя по изучению слов.

        :param user_id: ID пользователя в Telegram.
        :param words_id: ID изучаемого слова в таблице Word.
        :param status: Статус изучения слова (по умолчанию "learned").
        :return: None
        """
    progress = session.query(UserProgress).filter_by(user_id=user_id, words_id=words_id).first()
    if not progress:
        new_progress = UserProgress(user_id=user_id, words_id=words_id, status=status)
        session.add(new_progress)
    else:
        progress.status = status

    session.commit()
    print(f"✅ Прогресс обновлён: Пользователь {user_id} выучил слово {words_id}")

def random_word():
    """
        Выбирает случайное слово из таблицы Word.

        :return: Объект слова из БД или None, если слов нет.
        """
    words = session.query(Word).all()
    if not words:
        return None
    return random.choice(words)

user_data = {}

@bot.message_handler(commands=['go'])
def go_bot(message):
    """
            Запускает процесс изучения слов. Показывает пользователю слово и варианты перевода.

            :param message: Объект сообщения от пользователя.
            :return: None
            """
    search_user(message.from_user.id, message.from_user.username, message.chat.id)
    markup = types.ReplyKeyboardMarkup(row_width=2)

    all_words = session.query(Word).all()
    if not all_words:
        bot.send_message(message.chat.id, "Словарь пуст. Добавьте слова командой 'add words'")
        return

    all_progress = [i[0] for i in session.query(UserProgress.words_id).filter_by(user_id=message.from_user.id).all()]

    unlearned_words = [word for word in all_words if word.words_id not in all_progress]

    if not unlearned_words:
        bot.send_message(message.chat.id, "🎉 Вы выучили все слова! Добавьте новые.")
        return

    word = random.choice(unlearned_words)

    russian_word = word.words_ru
    first_word = word.words_en

    all_words_en = [w.words_en for w in all_words if w.words_en != first_word]
    ofter_words = random.sample(all_words_en, min(3, len(all_words_en)))

    first_value_btn = types.KeyboardButton(first_word)
    ofter_words_btn = [types.KeyboardButton(words) for words in ofter_words]

    together = [first_value_btn] + ofter_words_btn
    random.shuffle(together)

    add_word_btn = types.KeyboardButton(Command.add_word)
    next_btn = types.KeyboardButton(Command.next)
    delete_btn = types.KeyboardButton(Command.delete)

    together.extend([add_word_btn, next_btn, delete_btn])
    markup.add(*together)

    bot.send_message(message.chat.id, f'Слово для раздумий "{russian_word}"', reply_markup=markup)

    user_data[message.chat.id] = {
        'first_word': first_word,
        'word_id': word.words_id
    }
@bot.message_handler(func=lambda message: message.text == 'add words➕')
def add_words(message):
    """
        Запрашивает у пользователя слово на русском языке для добавления в БД.

        :param message: Объект сообщения от пользователя.
        :return: None
        """
    msg = bot.send_message(message.chat.id, "Введите слово на русском:")
    bot.register_next_step_handler(msg, create_ru_word, message.chat.id)

def create_ru_word(message, chat_id):
    """
        Получает русское слово от пользователя и запрашивает английский перевод.

        :param message: Объект сообщения от пользователя.
        :param chat_id: ID чата, в котором работает бот.
        :return: None
        """
    ru_word = message.text.strip()
    msg = bot.send_message(chat_id, "Введите слово на английском:")
    bot.register_next_step_handler(msg, create_en_word, ru_word, chat_id)

def create_en_word(message, ru_word, chat_id):
    """
        Получает английское слово от пользователя и добавляет его в БД, если оно отсутствует.

        :param message: Объект сообщения от пользователя.
        :param ru_word: Русское слово, введённое пользователем.
        :param chat_id: ID чата, в котором работает бот.
        :return: None
        """
    en_word = message.text.strip()
    exists = session.query(Word).filter(
        (Word.words_ru == ru_word) | (Word.words_en == en_word)
    ).first()
    if exists:
        bot.send_message(message.chat.id, "⚠️ Такое слово уже есть в базе")
        return

    new_word = Word(words_ru=ru_word, words_en=en_word, user_id=message.from_user.id)
    session.add(new_word)
    session.commit()
    bot.send_message(chat_id, "✅ Слово добавлено! /go")



@bot.message_handler(func=lambda message: message.text == 'delete🔙')
def learn_word(message):
    """
        Запрашивает у пользователя слово для удаления.

        :param message: Объект сообщения от пользователя.
        :return: None
        """
    msg = bot.send_message(message.chat.id, 'какое слово удалить,можно написать анг или ру, если передумал напиши "стоп')
    if msg == 'стоп':# if user write stop, command stops
        start_bot(message)
    bot.register_next_step_handler(msg, process_delete)

def process_delete(message):
    """
        Удаляет указанное пользователем слово из БД, если оно существует.

        :param message: Объект сообщения от пользователя.
        :return: None
        """
    word_to_delete = message.text.strip()
    word = session.query(Word).filter(
        (Word.words_ru == word_to_delete) | (Word.words_en == word_to_delete)
    ).first()

    if not word:
        bot.send_message(message.chat.id, '⚠️ Такое слово не найдено в базе.')
        return

    session.delete(word)
    session.commit()
    bot.send_message(message.chat.id, f'✅ Слово "{word_to_delete}" удалено!')

@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    """
        Обрабатывает ответы пользователя. Проверяет правильность перевода, обновляет прогресс изучения.

        :param message: Объект сообщения от пользователя.
        :return: None
        """

    chat_id = message.chat.id
    if chat_id not in user_data:
        bot.send_message(chat_id, "Сначала напиши команду /start")
        return

    data = user_data[chat_id]
    correct_word = data['first_word']
    word_id = data['word_id']

    if message.text == correct_word:
        create_progress(message.from_user.id, word_id)
        bot.send_message(chat_id, '✅ Правильно! Молодец!')
        random_word()
        go_bot(message)
    elif message.text == 'next➡️':
        random_word()
        go_bot(message)
    elif message.text == '/stop':
        bot.send_message(chat_id, 'До новых встреч')
    else:
        bot.send_message(chat_id, '❌ Неправильно. Попробуйте еще раз!')


if __name__ == '__main__': # ну тут документация наврятли нужна
    print("Стартуем")
    bot.polling()

    # params = {
    #
    #     'Authorization': token_yandex,
    #     'lang': 'ru-en',
    #     'text': ru_word,
    #     'ui': 'ru'
    # }
    # responses = requests.get(url, params=params)
    # if 200 <= responses.status_code < 300:
    #     contents = responses.json()
    #
    #     trans_word = contents['def'][0]['tr'][0]['text'] норм работает но токен всего по 12ч