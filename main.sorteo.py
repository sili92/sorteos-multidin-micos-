import os
import random
import re
import threading
import time
import telebot
from telebot import types

# Carga el TOKEN desde las variables de entorno de Railway
TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# --- PACK DE STICKERS DE CHERRIEBOT ---
STICKERS_CHERRIE = [
    "CAACAgEAAxkBAANHaoVbwH1bR16BovjZpvbzdmYAAcv5AAJKCAACh1YpROPnWzoUB7hkPQQ",
    "CAACAgEAAxkBAANJaoVbxFwCt6v7Dc4Bq5MBVviJkq0AAkIGAAKaKilEw6n5UhHxucY9BA",
    "CAACAgEAAxkBAANLaoVbxu0C4Pf13Q4h4--008tHtA0AAjwHAALY5ShExZIILPgB8XU9BA",
    "CAACAgEAAxkBAANNaoVbx0HIrfh3HaoEnRnq2TiF2FYAAgoHAAJDLjFED9e__RIuw0g9BA",
    "CAACAgEAAxkBAANPaoVbyYS2PuWDTuGSdGdWwcA7onQAAp8IAALviDFErpsOg5jJa4g9BA",
    "CAACAgEAAxkBAANRaoVby-CNkO8cMAw7x6E2yUThMaoAAtkGAALl9SlEbGxRRm1A0vM9BA"
]

# --- ESTADOS GLOBALES ---
sorteos = {}
puntos_sistema = {}          # {username: puntos_int}
quiz_aciertos = {}          # {username: total_aciertos_int}

quiz_juego = {
    "fase": "inactivo",
    "chat_id": None,
    "thread_id": None,
    "premio": "",
    "participantes": set(),
    "participantes_activos": set(),
    "pregunta_actual": None,
    "opcion_correcta": None,
    "respuestas": {},
    "msg_lobby_id": None,
    "msg_pregunta_id": None,
    "dificultad": 1
}

mineria_juego = {
    "fase": "inactivo",
    "chat_id": None,
    "thread_id": None,
    "premio": "",
    "participantes": [],
    "puntos": {},
    "turnos_restantes": {},
    "turno_actual_index": 0,
    "msg_lobby_id": None
}

loteria_juego = {
    "fase": "inactivo",
    "chat_id": None,
    "thread_id": None,
    "premio": "",
    "tickets_vendidos": {}, # {ticket_code: username}
    "usuarios_registrados": set(),
    "ticket_ganador": None,
    "ganador_esperado": None,
    "tiempo_limite": 0,
    "reclamado": False
}

# --- DETECTAR APARTADO/TEMA ACTUAL ---
def get_thread_id(message):
    return message.message_thread_id if message.is_topic_message else None

# --- OBTENER FILE_ID DE CUALQUIER STICKER ---
@bot.message_handler(content_types=['sticker'])
def capturar_sticker_id(message):
    file_id = message.sticker.file_id
    pack_name = message.sticker.set_name if message.sticker.set_name else "Desconocido"
    bot.reply_to(
        message, 
        f"Sticker capturado\n\nPack: {pack_name}\nFile ID:\n{file_id}", 
        parse_mode="Markdown"
    )

# --- COMANDOS BÁSICOS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type == 'private':
        nombre_usuario = message.from_user.first_name
        bot.send_message(
            message.chat.id, 
            f"૮₍˶ᵔ ᵕ ᵔ˶₎ა   ¡holi, {nombre_usuario}! soy cherrie, el bot oficial de cherrys que ayuda en dinámicas para que tú te diviertas y consigas los mejores premios ♡."
        )

@bot.message_handler(commands=['help'])
def send_help(message):
    thread_id = get_thread_id(message)
    if message.chat.type != 'private':
        nombre_usuario = message.from_user.first_name
        bot.send_message(
            message.chat.id, 
            f"૮₍˶ᵔ ᵕ ᵔ˶₎ა   ¡holi, {nombre_usuario}! soy cherrie, el bot oficial de cherrys que ayuda en dinámicas para que tú te diviertas y consigas los mejores premios ♡.",
            message_thread_id=thread_id,
            reply_to_message_id=message.message_id
        )

# --- COMANDO /BEG ---
@bot.message_handler(commands=['beg'])
def suplicar_robux(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)
    user_id = message.from_user.id
    first_name = message.from_user.first_name

    mencion_nickname = f'<a href="tg://user?id={user_id}">{first_name}</a>'

    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        bot.send_message(
            chat_id,
            f"¡{mencion_nickname} le está pidiendo Robux a {target_user.first_name}! 🥺🤲",
            parse_mode="HTML",
            message_thread_id=thread_id
        )
    else:
        bot.send_message(
            chat_id,
            f"¡{mencion_nickname} está suplicando por Robux a la nada! 🥺🤲",
            parse_mode="HTML",
            message_thread_id=thread_id
        )

# Mantiene el bot activo 24/7 en el servidor
if __name__ == '__main__':
    bot.infinity_polling()