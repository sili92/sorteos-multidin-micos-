import os
import random
import re
import threading
import time
import telebot
from telebot import types

# --- CONFIGURACIÓN DE TOKEN Y BOT ---
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

# --- BANCO DE PREGUNTAS (QUIZ CON OPCIONES A, B, C) ---
BANCO_QUIZ = [
    {"topic": "cultura general", "p": "¿Cuál es el río más largo del mundo?", "o": ["Amazonas", "Nilo", "Misisipi"], "c": 0},
    {"topic": "cultura general", "p": "¿En qué año llegó el hombre a la luna?", "o": ["1965", "1969", "1972"], "c": 1},
    {"topic": "ciencia", "p": "¿Elemento químico más abundante en el universo?", "o": ["Oxígeno", "Helio", "Hidrógeno"], "c": 2},
    {"topic": "geografía", "p": "¿Qué país tiene forma de bota?", "o": ["España", "Grecia", "Italia"], "c": 2},
    {"topic": "arte", "p": "¿Quién pintó la Mona Lisa?", "o": ["Vincent van Gogh", "Leonardo da Vinci", "Pablo Picasso"], "c": 1},
    {"topic": "matemáticas", "p": "¿Cuánto es 33 + 292?", "o": ["325", "330", "335"], "c": 0},
    {"topic": "música", "p": "¿Quién interpreta 'Hannah Montana'?", "o": ["Selena Gomez", "Miley Cyrus", "Sabrina Carpenter"], "c": 1},
    {"topic": "películas", "p": "¿Quién NO es una princesa de Disney oficial?", "o": ["Aurora", "Bella", "Elsa"], "c": 2}
]

# --- TABLA DE PREMIOS MINERÍA (PESOS Y PUNTOS) ---
PREMIOS_MINERIA = [
    {"peso": 20, "puntos": 0, "msg": "✦ @{user}, encontraste...\n\nnada... ( ꩜ ᯅ ꩜;)\n¡suerte para la próxima!"},
    {"peso": 15, "puntos": 3, "msg": "✦ @{user}, encontraste... una piedrita común...\n૮ • ﻌ - ა ¡tienes 3 puntos!"},
    {"peso": 12, "puntos": 5, "msg": "✦ @{user}, encontraste... un pedacito de carbón...\n(´๑•_•๑) no es mucho, pero sirve...\n¡tienes 5 puntos!"},
    {"peso": 10, "puntos": 8, "msg": "✦ @{user}, encontraste... una piedra que brilla un poquito...\n૮₍´｡• ᵕ •｡₎ა ¡tienes 8 puntos!"},
    {"peso": 8, "puntos": 12, "msg": "✦ @{user}, encontraste... un cristal de cuarzo pequeño...\n(ᐡ･ ﻌ ･ᐡ) ¡qué bonito!\n¡tienes 12 puntos!"},
    {"peso": 7, "puntos": 18, "msg": "✦ @{user}, encontraste... una pequeña cueva con honguitos brillantes...\n꒰◍ॢ•ᴗ•◍ॢ꒱ ¡tienes 18 puntos!"},
    {"peso": 6, "puntos": 25, "msg": "✦ @{user}, encontraste... un fragmento de hierro antiguo...\n૮₍˶• . • ⑅₎ა parece útil...\n¡tienes 25 puntos!"},
    {"peso": 5, "puntos": 32, "msg": "✦ @{user}, encontraste... un cristal azul escondido...\n૮₍˶ᵔ ᵕ ᵔ˶₎ა ¡qué hallazgo tan lindo!\n¡tienes 32 puntos!"},
    {"peso": 4, "puntos": 40, "msg": "✦ @{user}, encontraste... una moneda vieja enterrada...\n૮꒰ต´˘ต꒱ა alguien la perdió hace mucho...\n¡tienes 40 puntos!"},
    {"peso": 3, "puntos": 50, "msg": "✦ @{user}, encontraste... una amatista brillante...\n(∗˃̶ ᵕ ˂̶∗) ¡encontraste algo especial!\n¡tienes 50 puntos!"},
    {"peso": 2.5, "puntos": 60, "msg": "✦ @{user}, encontraste... un cristal con energía extraña...\n૮꒰˶˃̵ ^ ˂̵˵꒱ა ¡brilla muchísimo!\n¡tienes 60 puntos!"},
    {"peso": 2, "puntos": 70, "msg": "✦ @{user}, encontraste... un pequeño cofre bajo las rocas...\n૮꒰⑅ᐢ ᵕ ᵕ ᐢ⑅꒱ ¡¿qué habrá dentro?!\n¡tienes 70 puntos!"},
    {"peso": 1.5, "puntos": 78, "msg": "✦ @{user}, encontraste... una perla escondida bajo la tierra...\n(⑅˘͈ ᵕ ˘͈ )  ¡es preciosa!\n¡tienes 78 puntos!"},
    {"peso": 1, "puntos": 85, "msg": "✦ @{user}, encontraste... una pequeña veta de oro...\n໒꒰ྀི ∩ ˃ ᵕ ˂ ∩ ꒱ྀི১ ¡qué suerte!\n¡tienes 85 puntos!"},
    {"peso": 0.8, "puntos": 90, "msg": "✦ @{user}, encontraste... un zafiro muy raro...\n૮꒰ྀི ᵔ ๑ ᵔ ꒱ა ¡tuviste mucha suerte!\n¡tienes 90 puntos!"},
    {"peso": 0.5, "puntos": 95, "msg": "✦ @{user}, encontraste... un diamante rosa brillante...\n♡ ᖭི(ˊᗜˋ*)ᖫྀ ¡ES HERMOSO!\n¡tienes 95 puntos!"},
    {"peso": 0.2, "puntos": 100, "msg": "✦ @{user}, encontraste... el tesoro secreto de Cherrie...\n(♡´𓈒𓂂˘˘`♡) ¡encontraste algo que casi nadie encuentra!\n¡tienes 100 puntos!"}
]

# --- ESTADOS GLOBALES DE LOS JUEGOS ---
sorteos = {}         # {chat_id: data}
quiz_juego = {
    "fase": "inactivo", "topic": "", "pregunta": None, "votos": {}, 
    "stats": {}, "chat_id": None, "thread_id": None, "top1_prev": None,
    "ganadores_orden": []
}
mineria_juego = {
    "fase": "inactivo", "participantes": [], "turno_index": 0, 
    "puntos": {}, "chat_id": None, "thread_id": None
}
loteria_juego = {
    "fase": "inactiva", "premio": "", "tickets": {}, "boletos_vendidos": [],
    "ticket_ganador": None, "ganador_user": None, "esperando_reclamo": False,
    "chat_id": None, "thread_id": None
}

# --- FUNCIONES AUXILIARES ---
def get_thread_id(message):
    return message.message_thread_id if message.is_topic_message else None

def es_admin(chat_id, user_id):
    try:
        status = bot.get_chat_member(chat_id, user_id).status
        return status in ['administrator', 'creator']
    except Exception:
        return False

# --- COMANDOS BÁSICOS & BEG ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type == 'private':
        nickname = message.from_user.first_name
        bot.send_message(
            message.chat.id, 
            f"૮₍˶ᵔ ᵕ ᵔ˶₎ა   ¡holi, {nickname}!\nsoy cherrie, el bot oficial de cherrys que ayuda en dinámicas para que tú te diviertas y consigas los mejores premios ♡."
        )

@bot.message_handler(commands=['beg'])
def suplicar_robux(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    mencion = f'<a href="tg://user?id={user_id}">{first_name}</a>'

    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
        target_mencion = f'<a href="tg://user?id={target.id}">{target.first_name}</a>'
        texto = f"ㅤ૮  .ܸ  .ܸ ྀི ა  ㅤ{mencion} le está suplicando a {target_mencion} por robux...ㅤ"
    else:
        texto = f"ㅤ૮  .ܸ  .ܸ ྀི ა  ㅤ{mencion} suplica por robux...ㅤ"

    bot.send_message(chat_id, texto, parse_mode="HTML", message_thread_id=thread_id, reply_to_message_id=message.message_id)
    if STICKERS_CHERRIE:
        try: bot.send_sticker(chat_id, random.choice(STICKERS_CHERRIE), message_thread_id=thread_id)
        except Exception: pass

# --- SISTEMA DE SORTEOS CON /resortear ---
def generar_texto_sorteo(premio, tiempo_str, ganadores_num):
    return (
        "ㅤㅤㅤㅤㅤㅤ୭ৎ ࣪ ׅ ㅤㅤㅤ ¡Nuevo sorteo!ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ\n\n"
        f"𓂃   premio  :  {premio}\n"
        f"𓂃   tiempo restante  :  {tiempo_str}\n"
        f"𓂃   ganador/es  :  {ganadores_num} ganador/es\n\n"
        "ㅤㅤㅤㅤᡣ𐭩ㅤㅤpresiona el botón para unirte."
    )

def generar_texto_resultados(premio, ganadores_str, admin_user):
    return (
        "ㅤㅤㅤ୭ৎ ࣪ ׅ ㅤㅤㅤ ¡Resultados!\n\n"
        f"𓂃   premio  :  {premio}\n"
        f"𓂃   ganador/es  :  {ganadores_str}\n\n"
        f"ㅤㅤㅤㅤᡣ𐭩ㅤㅤ¡felicidades! reclama con @{admin_user}"
    )

@bot.message_handler(commands=['sorteo'])
def crear_sorteo(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥) no eres admin.", message_thread_id=thread_id)
        return

    partes = message.text.split(maxsplit=3)
    if len(partes) < 4:
        bot.send_message(chat_id, "Uso: /sorteo [premio] [tiempo en min] [num_ganadores]", message_thread_id=thread_id)
        return

    premio = partes[1]
    minutos = int(re.sub(r'\D', '', partes[2]) or 1)
    num_ganadores = int(re.sub(r'\D', '', partes[3]) or 1)
    admin_username = message.from_user.username or message.from_user.first_name

    segundos = minutos * 60
    tiempo_fin = time.time() + segundos

    sorteos[chat_id] = {
        "premio": premio, "participantes": set(), "mensaje_id": None,
        "num_ganadores": num_ganadores, "tiempo_fin": tiempo_fin,
        "admin_user": admin_username, "thread_id": thread_id, "activo": True
    }

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_sorteo"))

    msg = bot.send_message(chat_id, generar_texto_sorteo(premio, f"{minutos} minutos", num_ganadores), reply_markup=markup, message_thread_id=thread_id)
    sorteos[chat_id]["mensaje_id"] = msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "unirse_sorteo")
def unirse_sorteo_cb(call):
    chat_id = call.message.chat.id
    username = call.from_user.username or call.from_user.first_name
    thread_id = get_thread_id(call.message)

    if chat_id not in sorteos or not sorteos[chat_id]["activo"]:
        bot.answer_callback_query(call.id, "Este sorteo ya cerró.", show_alert=True)
        return

    if username in sorteos[chat_id]["participantes"]:
        bot.answer_callback_query(call.id, "Ya estás participando.", show_alert=True)
        return

    sorteos[chat_id]["participantes"].add(username)
    bot.answer_callback_query(call.id, "¡Te has unido al sorteo!")
    bot.send_message(chat_id, f"✦⠀¡nuevo participante! @{username}, mucha suerte :3", message_thread_id=thread_id)

def finalizar_sorteo_automatico(chat_id):
    if chat_id not in sorteos or not sorteos[chat_id]["activo"]: return
    data = sorteos[chat_id]
    data["activo"] = False

    try: bot.edit_message_reply_markup(chat_id, data["mensaje_id"], reply_markup=None)
    except Exception: pass

    parts = list(data["participantes"])
    if not parts:
        bot.send_message(chat_id, " (╥﹏╥) Sorteo finalizado sin participantes.", message_thread_id=data["thread_id"])
        return

    c = min(len(parts), data["num_ganadores"])
    ganadores = random.sample(parts, c)
    g_str = ", ".join([f"@{g}" for g in ganadores])

    bot.send_message(chat_id, generar_texto_resultados(data["premio"], g_str, data["admin_user"]), message_thread_id=data["thread_id"])

@bot.message_handler(commands=['resortear'])
def resortear(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)
    if not es_admin(chat_id, message.from_user.id): return

    if chat_id not in sorteos or not sorteos[chat_id]["participantes"]:
        bot.send_message(chat_id, " (╥﹏╥) No hay participantes guardados para resortear.", message_thread_id=thread_id)
        return

    data = sorteos[chat_id]
    parts = list(data["participantes"])
    c = min(len(parts), data["num_ganadores"])
    nuevos_ganadores = random.sample(parts, c)
    g_str = ", ".join([f"@{g}" for g in nuevos_ganadores])

    bot.send_message(chat_id, generar_texto_resultados(data["premio"], g_str, data["admin_user"]), message_thread_id=thread_id)

def monitor_sorteos():
    while True:
        ahora = time.time()
        for cid, d in list(sorteos.items()):
            if d["activo"] and ahora >= d["tiempo_fin"]:
                finalizar_sorteo_automatico(cid)
        time.sleep(5)

threading.Thread(target=monitor_sorteos, daemon=True).start()

# --- JUEGO 2: QUIZ CON OPCIONES Y /quizlegends ---
@bot.message_handler(commands=['quiz'])
def iniciar_quiz(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)

    if quiz_juego["fase"] == "jugando":
        bot.send_message(chat_id, " (╥﹏╥) Ya hay una pregunta en curso.", message_thread_id=thread_id)
        return

    q = random.choice(BANCO_QUIZ)
    quiz_juego["fase"] = "jugando"
    quiz_juego["pregunta"] = q
    quiz_juego["votos"] = {}
    quiz_juego["chat_id"] = chat_id
    quiz_juego["thread_id"] = thread_id

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"✦  Opción A : {q['o'][0]}", callback_data="quiz_opt_0"))
    markup.add(types.InlineKeyboardButton(f"✦  Opción B : {q['o'][1]}", callback_data="quiz_opt_1"))
    markup.add(types.InlineKeyboardButton(f"✦  Opción C : {q['o'][2]}", callback_data="quiz_opt_2"))

    texto = f"ㅤㅤᡣ𐭩ㅤㅤㅤ¡prueba tu conocimiento en {q['topic']}!\nㅤ𓂃ㅤㅤ{q['p']}..."
    bot.send_message(chat_id, texto, reply_markup=markup, message_thread_id=thread_id)

    threading.Thread(target=timer_quiz, args=(chat_id, thread_id), daemon=True).start()

@bot.callback_query_handler(func=lambda c: c.data.startswith("quiz_opt_"))
def quiz_voto(call):
    if quiz_juego["fase"] != "jugando":
        bot.answer_callback_query(call.id, "Ronda terminada.", show_alert=True)
        return
    idx = int(call.data.split("_")[2])
    user = call.from_user.username or call.from_user.first_name
    quiz_juego["votos"][user] = idx
    bot.answer_callback_query(call.id, "¡Respuesta registrada!")

def timer_quiz(chat_id, thread_id):
    time.sleep(45)
    if quiz_juego["fase"] == "jugando":
        evaluar_quiz(chat_id, thread_id)

def evaluar_quiz(chat_id, thread_id):
    quiz_juego["fase"] = "inactivo"
    q = quiz_juego["pregunta"]
    correcta_idx = q["c"]

    ganadores = [u for u, opt in quiz_juego["votos"].items() if opt == correcta_idx]
    perdedores = [u for u, opt in quiz_juego["votos"].items() if opt != correcta_idx]

    g_str = ", ".join([f"@{u}" for u in ganadores]) if ganadores else "Nadie"
    p_str = ", ".join([f"@{u}" for u in perdedores]) if perdedores else "Nadie"

    res = f"(๑>ᴗ<๑)    ¡todos respondieron!\n𓂃   ¡Ganadores! : {g_str}\n𓂃   Perdedores... : {p_str}"
    bot.send_message(chat_id, res, message_thread_id=thread_id)

    # Actualizar estadisticas
    for g in ganadores:
        quiz_juego["stats"][g] = quiz_juego["stats"].get(g, 0) + 1
        if g not in quiz_juego["ganadores_orden"]:
            quiz_juego["ganadores_orden"].append(g)

    # Mensaje de acomulacion si hay victorias
    if quiz_juego["stats"]:
        mostrar_quiz_legends(chat_id, thread_id)

@bot.message_handler(commands=['quizlegends'])
def comando_quizlegends(message):
    mostrar_quiz_legends(message.chat.id, get_thread_id(message))

def mostrar_quiz_legends(chat_id, thread_id):
    if not quiz_juego["stats"]:
        bot.send_message(chat_id, " (╥﹏╥) Aún no hay registros en Quiz Legends.", message_thread_id=thread_id)
        return

    # Ordenar por victorias
    sorted_stats = sorted(quiz_juego["stats"].items(), key=lambda x: (-x[1], quiz_juego["ganadores_orden"].index(x[0])))

    lines = ["      ‿︵       𝘘𝘶𝘪𝘻 𝘓𝘦𝘨𝘦𝘯𝘥𝘴 !\n"]
    for user, vic in sorted_stats:
        lines.append(f"✦ @{user} — {vic} victorias.")
    
    msg_stats = "\n".join(lines)

    # Evaluación de Mensajitos dinámicos al final
    extra_msg = ""
    top1_user, top1_vic = sorted_stats[0]

    if len(sorted_stats) >= 2:
        top2_user, top2_vic = sorted_stats[1]
        
        # Empate en 1er lugar
        if top1_vic == top2_vic:
            extra_msg = f"\n\n¡@{top1_user} y @{top2_user} compiten por el primer puesto..."
        # Remontada
        elif quiz_juego["top1_prev"] and quiz_juego["top1_prev"] != top1_user:
            extra_msg = f"\n\n¡Remontada de @{top1_user} ٩(ˊᗜˋ*)و ♡"
        # Ventaja clara (2-3 más)
        elif top1_vic >= top2_vic + 2:
            extra_msg = f"\n\nCuidado con @{top1_user}...  ૮₍•᷄ ࡇ •᷅₎ა"
    else:
        if top1_vic >= 3:
            extra_msg = f"\n\nCuidado con @{top1_user}...  ૮₍•᷄ ࡇ •᷅₎ა"

    quiz_juego["top1_prev"] = top1_user
    bot.send_message(chat_id, msg_stats + extra_msg, message_thread_id=thread_id)

@bot.message_handler(commands=['endquiz'])
def endquiz(message):
    if es_admin(message.chat.id, message.from_user.id):
        quiz_juego["fase"] = "inactivo"
        quiz_juego["stats"].clear()
        quiz_juego["ganadores_orden"].clear()
        quiz_juego["top1_prev"] = None
        bot.send_message(message.chat.id, " (╥﹏╥) Quiz finalizado y estadísticas reiniciadas.", message_thread_id=get_thread_id(message))

# --- JUEGO 3: MINERÍA ---
@bot.message_handler(commands=['mineria'])
def iniciar_mineria(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)
    if not es_admin(chat_id, message.from_user.id): return

    mineria_juego["fase"] = "lobby"
    mineria_juego["participantes"] = []
    mineria_juego["puntos"] = {}
    mineria_juego["chat_id"] = chat_id
    mineria_juego["thread_id"] = thread_id

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_mineria"))

    texto = "ㅤㅤᡣ𐭩ㅤㅤㅤ¡hora de minar!\nprueba tu suerte y únete para ganar o perder minery points."
    bot.send_message(chat_id, texto, reply_markup=markup, message_thread_id=thread_id)

@bot.callback_query_handler(func=lambda c: c.data == "unirse_mineria")
def join_mineria(call):
    if mineria_juego["fase"] != "lobby":
        bot.answer_callback_query(call.id, "Lobby cerrado.", show_alert=True)
        return
    u = call.from_user.username or call.from_user.first_name
    if u not in mineria_juego["participantes"]:
        mineria_juego["participantes"].append(u)
        bot.answer_callback_query(call.id, "¡Te uniste a la minería!")
        bot.send_message(call.message.chat.id, f"✦ @{u} se ha unido. ¿listo para minar?", message_thread_id=get_thread_id(call.message))

@bot.message_handler(commands=['mineriastart'])
def start_mineria(message):
    if not es_admin(message.chat.id, message.from_user.id): return
    if mineria_juego["fase"] != "lobby" or not mineria_juego["participantes"]: return

    mineria_juego["fase"] = "jugando"
    mineria_juego["turno_index"] = 0
    siguiente_turno_mineria()

def siguiente_turno_mineria():
    parts = mineria_juego["participantes"]
    idx = mineria_juego["turno_index"] % len(parts)
    actual = parts[idx]

    texto = f"ㅤ$&nbsp; ࣪ ׅ ㅤㅤ¡turno de @{actual}!\nㅤ— ㅤㅤusa /minar para probar tu suerte."
    bot.send_message(mineria_juego["chat_id"], texto, message_thread_id=mineria_juego["thread_id"])

@bot.message_handler(commands=['minar'])
def minar_cmd(message):
    if mineria_juego["fase"] != "jugando": return
    user = message.from_user.username or message.from_user.first_name
    parts = mineria_juego["participantes"]
    actual = parts[mineria_juego["turno_index"] % len(parts)]

    if user != actual:
        return

    # Selección aleatoria ponderada
    opciones = PREMIOS_MINERIA
    pesos = [o["peso"] for o in opciones]
    premio = random.choices(opciones, weights=pesos, k=1)[0]

    mineria_juego["puntos"][user] = mineria_juego["puntos"].get(user, 0) + premio["puntos"]
    bot.send_message(message.chat.id, premio["msg"].format(user=user), message_thread_id=get_thread_id(message))

    mineria_juego["turno_index"] += 1
    siguiente_turno_mineria()

@bot.message_handler(commands=['checkmineria'])
def check_mineria(message):
    if not mineria_juego["puntos"]:
        bot.send_message(message.chat.id, " (╥﹏╥) No hay puntos registrados.", message_thread_id=get_thread_id(message))
        return
    sorted_p = sorted(mineria_juego["puntos"].items(), key=lambda x: x[1], reverse=True)
    lines = ["      ‿︵       𝘉𝘦𝘴𝘵 𝘔𝘪𝘯𝘦𝘳𝘴 !\n"]
    for u, p in sorted_p:
        lines.append(f"✦ @{u} — {p} puntos.")
    bot.send_message(message.chat.id, "\n".join(lines), message_thread_id=get_thread_id(message))

@bot.message_handler(commands=['endmineria'])
def endmineria(message):
    if es_admin(message.chat.id, message.from_user.id):
        mineria_juego["fase"] = "inactivo"
        mineria_juego["puntos"].clear()
        mineria_juego["participantes"].clear()
        bot.send_message(message.chat.id, " (╥﹏╥) Minería finalizada y puntos reiniciados.", message_thread_id=get_thread_id(message))

# --- JUEGO 4: LOTERÍA CHERRIE ---
@bot.message_handler(commands=['loteria'])
def iniciar_loteria(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)
    if not es_admin(chat_id, message.from_user.id): return

    partes = message.text.split(maxsplit=1)
    premio = partes[1] if len(partes) > 1 else "5 robux"

    loteria_juego["fase"] = "activa"
    loteria_juego["premio"] = premio
    loteria_juego["tickets"].clear()
    loteria_juego["boletos_vendidos"].clear()
    loteria_juego["esperando_reclamo"] = False
    loteria_juego["chat_id"] = chat_id
    loteria_juego["thread_id"] = thread_id

    texto = f"ㅤ୭ৎ ࣪ ׅ ㅤㅤ¡ha empezado la lotería!\nprueba tu suerte comprando tus tickets, usa /tickets para recibir 5 oportunidades para ganar el premio mayor, {premio}."
    bot.send_message(chat_id, texto, message_thread_id=thread_id)

@bot.message_handler(commands=['tickets'])
def pedir_tickets(message):
    if loteria_juego["fase"] != "activa": return
    user = message.from_user.username or message.from_user.first_name

    if user in loteria_juego["tickets"]:
        bot.send_message(message.chat.id, f" (╥﹏╥) @{user}, ya compraste tus 5 boletos.", message_thread_id=get_thread_id(message))
        return

    mis_tickets = []
    for _ in range(5):
        num = f"CHERRY{random.randint(1000, 9999)}"
        mis_tickets.append(num)
        loteria_juego["boletos_vendidos"].append((num, user))

    loteria_juego["tickets"][user] = mis_tickets
    
    # Formato monoespaciado exacto
    tickets_fmt = "\n".join([f"`{t}`" for t in mis_tickets])
    bot.send_message(message.chat.id, tickets_fmt, parse_mode="Markdown", message_thread_id=get_thread_id(message))

@bot.message_handler(commands=['jugarloteria'])
def jugar_loteria(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)
    if not es_admin(chat_id, message.from_user.id): return

    if not loteria_juego["boletos_vendidos"]:
        bot.send_message(chat_id, " (╥﹏╥) No se ha vendido ningún ticket aún.", message_thread_id=thread_id)
        return

    ticket_win, winner_user = random.choice(loteria_juego["boletos_vendidos"])
    loteria_juego["ticket_ganador"] = ticket_win
    loteria_juego["ganador_user"] = winner_user
    loteria_juego["esperando_reclamo"] = True

    texto = (
        f"ㅤㅤᡣ𐭩ㅤㅤㅤresultados de la lotería cherrie . . .\n"
        f"         —         nuestro ticket ganador es el `{ticket_win}`.\n"
        f"el ganador tiene 45 segundos para escribir ¡lotería! en el chat y asegurar su victoria."
    )
    bot.send_message(chat_id, texto, parse_mode="Markdown", message_thread_id=thread_id)

    threading.Thread(target=timer_loteria, args=(chat_id, thread_id), daemon=True).start()

def timer_loteria(chat_id, thread_id):
    time.sleep(45)
    if loteria_juego["esperando_reclamo"]:
        loteria_juego["esperando_reclamo"] = False
        user = loteria_juego["ganador_user"]
        bot.send_message(chat_id, f"✦   @{user} no reclamó su lotería... (´๑•_•๑)", message_thread_id=thread_id)

@bot.message_handler(func=lambda m: loteria_juego["esperando_reclamo"])
def escuchar_loteria_claim(message):
    user = message.from_user.username or message.from_user.first_name
    texto = message.text.strip().lower()

    if user == loteria_juego["ganador_user"] and ("¡lotería!" in texto or "loteria" in texto or "¡loteria!" in texto):
        loteria_juego["esperando_reclamo"] = False
        bot.send_message(message.chat.id, f"✦  ¡@{user}  es el ganador de la lotería!", message_thread_id=get_thread_id(message))

# --- INICIO DEL BOT ---
if __name__ == '__main__':
    bot.infinity_polling()
