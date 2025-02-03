"""
Телеграм-бот для изучения английских слов.

Пользователи могут добавлять слова, изучать их, отмечать прогресс.
Слова хранятся в базе данных с разделением по пользователям и общим словам.

Используемые таблицы:
- User: информация о пользователях.
- Word: слова (русский и английский вариант), связь с пользователем.
- UserProgress: прогресс изучения слов пользователями.

Основные команды:
/start - начать работу с ботом.
/go - начать тренировку.
"""

from sqlalchemy import or_, func
from sqlalchemy.orm import sessionmaker
from create_bd import User, Word, UserProgress
from data_file import engine
import telebot
import random
import configparser
from telebot import types

config = configparser.ConfigParser()
config.read('settings.ini')
token = config["TOKEN"]['token']

Session = sessionmaker(bind=engine)
session = Session()


class Command:
    add_word = 'add words➕'
    next = 'next➡️'
    delete = 'delete🔙'


bot = telebot.TeleBot(token)


def search_user(user_id, user_name, chat_id):
    """
    Проверяет наличие пользователя в БД и создает нового при необходимости.

    :param user_id: ID пользователя в Telegram
    :param user_name: Имя пользователя
    :param chat_id: ID чата
    """
    user = session.query(User).filter_by(user_id=user_id).first()
    if not user:
        new_user = User(user_name=user_name, chat_id=chat_id, user_id=user_id)
        session.add(new_user)
        session.commit()


@bot.message_handler(commands=['start'])
def start_bot(message):
    """
    Обработчик команды /start. Регистрирует пользователя и приветствует.
    """
    chat_id = message.chat.id
    bot.send_message(chat_id,
                     'Привет 👋 Давай попрактикуемся в английском языке. Тренировки можешь проходить в удобном для себя темпе /go.')
    search_user(message.from_user.id, message.from_user.username, message.chat.id)


def create_progress(user_id, words_id):
    """
    Создает или обновляет запись о прогрессе изучения слова.

    :param user_id: ID пользователя
    :param words_id: ID слова
    """
    progress = session.query(UserProgress).filter_by(
        user_id=user_id,
        words_id=words_id
    ).first()

    if not progress:
        new_progress = UserProgress(
            user_id=user_id,
            words_id=words_id,
            is_learned=True
        )
        session.add(new_progress)
    else:
        progress.is_learned = True
    session.commit()


@bot.message_handler(commands=['go'])
def go_bot(message):
    """
    Запускает процесс тренировки, выводя слово и варианты перевода.
    """
    search_user(message.from_user.id, message.from_user.username, message.chat.id)

    # Получаем случайное невыученное слово
    unlearned_word = session.query(Word).filter(
        ~Word.words_id.in_(
            session.query(UserProgress.words_id)
            .filter(
                UserProgress.user_id == message.from_user.id,
                UserProgress.is_learned == True
            )
        ),
        or_(
            Word.user_id == message.from_user.id,
            Word.user_id == None
        )
    ).order_by(func.random()).first()

    if not unlearned_word:
        bot.send_message(message.chat.id, "🎉 Вы выучили все слова! Добавьте новые.")
        return

    markup = types.ReplyKeyboardMarkup(row_width=2)
    russian_word = unlearned_word.words_ru
    correct_answer = unlearned_word.words_en

    # Получаем варианты ответов
    other_words = session.query(Word).filter(
        or_(
            Word.user_id == message.from_user.id,
            Word.user_id == None
        ),
        Word.words_en != correct_answer
    ).order_by(func.random()).limit(3).all()

    options = [word.words_en for word in other_words]
    options.append(correct_answer)
    random.shuffle(options)

    # Создаем кнопки
    buttons = [types.KeyboardButton(opt) for opt in options]
    buttons.extend([
        types.KeyboardButton(Command.add_word),
        types.KeyboardButton(Command.next),
        types.KeyboardButton(Command.delete)
    ])
    markup.add(*buttons)

    bot.send_message(message.chat.id, f'Слово для перевода: "{russian_word}"', reply_markup=markup)
    user_data[message.chat.id] = {
        'correct_answer': correct_answer,
        'word_id': unlearned_word.words_id
    }


@bot.message_handler(func=lambda message: message.text == Command.add_word)
def add_words(message):
    """
    Инициирует процесс добавления нового слова.
    """
    msg = bot.send_message(message.chat.id, "Введите слово на русском:")
    bot.register_next_step_handler(msg, process_ru_word)


def process_ru_word(message):
    """
    Обрабатывает русское слово и запрашивает перевод.
    """
    ru_word = message.text.strip()
    msg = bot.send_message(message.chat.id, "Введите перевод на английском:")
    bot.register_next_step_handler(msg, process_en_word, ru_word)


def process_en_word(message, ru_word):
    """
    Обрабатывает английское слово и сохраняет в БД.
    """
    en_word = message.text.strip()

    # Проверка на существование слова
    exists = session.query(Word).filter(
        ((Word.words_ru == ru_word) | (Word.words_en == en_word)) &
        (or_(Word.user_id == message.from_user.id, Word.user_id == None))
    ).first()

    if exists:
        bot.send_message(message.chat.id, "⚠️ Такое слово уже существует!")
        return

    new_word = Word(
        words_ru=ru_word,
        words_en=en_word,
        user_id=message.from_user.id
    )
    session.add(new_word)
    session.commit()
    bot.send_message(message.chat.id, "✅ Слово успешно добавлено! /go")


@bot.message_handler(func=lambda message: message.text == Command.delete)
def handle_delete(message):
    """
    Инициирует процесс удаления слова.
    """
    msg = bot.send_message(message.chat.id, "Введите слово для удаления (рус/англ) или 'стоп' для отмены:")
    bot.register_next_step_handler(msg, process_delete)


def process_delete(message):
    """
    Обрабатывает удаление слова из БД.
    """
    if message.text.lower() == 'стоп':
        bot.send_message(message.chat.id, "❌ Удаление отменено.")
        return

    target = message.text.strip()
    word = session.query(Word).filter(
        ((Word.words_ru == target) | (Word.words_en == target)) &
        (Word.user_id == message.from_user.id)
    ).first()

    if not word:
        bot.send_message(message.chat.id, "⚠️ Слово не найдено или нет прав для удаления!")
        return

    session.delete(word)
    session.commit()
    bot.send_message(message.chat.id, f"✅ Слово '{target}' удалено!")


@bot.message_handler(func=lambda message: True)
def check_answer(message):
    """
    Проверяет ответ пользователя и обновляет прогресс.
    """
    chat_id = message.chat.id
    if chat_id not in user_data:
        bot.send_message(chat_id, "⚠️ Сначала начните тренировку командой /go")
        return

    user_answer = message.text
    correct_data = user_data[chat_id]

    if user_answer == correct_data['correct_answer']:
        create_progress(message.from_user.id, correct_data['word_id'])
        bot.send_message(chat_id, "✅ Правильно! Молодец!")
    else:
        bot.send_message(chat_id, "❌ Неправильно. Попробуйте еще раз!")

    go_bot(message)


if __name__ == '__main__':
    user_data = {}
    print("Бот запущен")
    bot.polling()