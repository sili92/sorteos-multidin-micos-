import telebot
from telebot import types
import random
import threading
import time
import re

TOKEN = __import__("os").environ["TOKEN"]
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
quiz_aciertos = {}           # {username: total_aciertos_int}
mineria_historico = {}       # {username: puntos_acumulados_int} (Para /bestminers)

quiz_juego = {
    "fase": "inactivo",
    "chat_id": None,
    "thread_id": None,
    "admin_id": None,        # Exclusividad de admin
    "premio": "",
    "participantes": set(),
    "participantes_activos": set(),
    "pregunta_actual": None,
    "opcion_correcta": None,
    "respuestas": {},        # {username: {"opcion": int, "tiempo": float}}
    "msg_lobby_id": None,
    "msg_pregunta_id": None,
    "dificultad": 1,
    "preguntas_usadas": []
}

mineria_juego = {
    "fase": "inactivo",
    "chat_id": None,
    "thread_id": None,
    "admin_id": None,        # Exclusividad de admin
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
    "admin_id": None,        # Exclusividad de admin
    "premio": "",
    "tickets_vendidos": {},  # {ticket_code: username}
    "usuarios_registrados": set(),
    "ticket_ganador": None,
    "ganador_esperado": None,
    "tiempo_limite": 0,
    "reclamado": False
}

# --- AUXILIARES ---
def get_thread_id(message):
    return message.message_thread_id if message.is_topic_message else None

def es_admin(chat_id, user_id):
    try:
        status = bot.get_chat_member(chat_id, user_id).status
        return status in ['administrator', 'creator']
    except Exception:
        return False

# --- COMANDOS BÁSICOS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type == 'private':
        nombre_usuario = message.from_user.first_name
        bot.send_message(
            message.chat.id, 
            f"૮ ˶• ˔ •˶ ა   ¡holi, {nombre_usuario}! soy cherrie, el bot oficial de cherrys que ayuda en dinámicas para que tú te diviertas y consigas los mejores premios ♡."
        )

@bot.message_handler(commands=['help'])
def send_help(message):
    thread_id = get_thread_id(message)
    if message.chat.type != 'private':
        nombre_usuario = message.from_user.first_name
        bot.send_message(
            message.chat.id, 
            f"૮ ˶• ˔ •˶ ა   ¡holi, {nombre_usuario}! soy cherrie, el bot oficial de cherrys que ayuda en dinámicas para que tú te diviertas y consigas los mejores premios ♡.",
            message_thread_id=thread_id,
            reply_to_message_id=message.message_id
        )

# --- COMANDO /COMANDOS ---
@bot.message_handler(commands=['comandos'])
def mostrar_comandos(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if message.chat.type != 'private' and not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes usar este comando.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    texto = (
        "  丙        ◟     Lista de Comandos.           𝆬          \n\n"
        "✦ /sorteo [premio] [tiempo] [ganadores] 𓂃 Inicia un nuevo sorteo.\n"
        "✦ /endsorteo 𓂃 Finaliza el sorteo activo inmediatamente.\n"
        "✦ /resorteo 𓂃 Elige un nuevo ganador del sorteo actual.\n"
        "✦ /quiz [premio] 𓂃 Abre el lobby para la batalla de preguntas.\n"
        "✦ /quizstart 𓂃 Empieza las rondas del quiz activo.\n"
        "✦ /quizlegends 𓂃 Muestra el top de personas con más aciertos.\n"
        "✦ /mineria [premio] 𓂃 Abre el lobby para el juego de minería.\n"
        "✦ /mineriastart 𓂃 Inicia las rondas de minería.\n"
        "✦ /minar 𓂃 Realiza una acción de minería en tu turno.\n"
        "✦ /bestminers 𓂃 Muestra el top de puntos de minería.\n"
        "✦ /endmineria 𓂃 Finaliza la minería manualmente.\n"
        "✦ /loteria [premio] 𓂃 Inicia la compra de tickets de lotería.\n"
        "✦ /tickets 𓂃 Recibe 5 tickets para la lotería.\n"
        "✦ /jugarloteria 𓂃 Realiza el sorteo de la lotería.\n"
        "✦ /add @usuario [monto] 𓂃 Añade puntos a la cartilla.\n"
        "✦ /rest @usuario [monto] 𓂃 Resta puntos a un usuario.\n"
        "✦ /check 𓂃 Muestra la cartilla de puntos.\n"
        "✦ /clear 𓂃 Reinicia la cartilla de puntos.\n"
        "✦ /cancelar 𓂃 Cancela cualquier juego o sorteo activo.\n"
        "✦ /beg 𓂃 Suplica por robux con animación.\n"
        "✦ /questions 𓂃 Muestra la base de datos de preguntas."
    )
    bot.send_message(chat_id, texto, message_thread_id=thread_id)

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
        target_id = target_user.id
        target_name = target_user.first_name
        target_mencion = f'<a href="tg://user?id={target_id}">{target_name}</a>'
        texto = f"ㅤ૮  .ܸ  .ܸ ྀི ა  ㅤ{mencion_nickname} que usó beg está suplicando a {target_mencion} por robux...ㅤ"
    else:
        texto = f"ㅤ૮  .ܸ  .ܸ ྀི ა  ㅤ{mencion_nickname} que usó beg está suplicando por robux...ㅤ"

    bot.send_message(
        chat_id, 
        texto, 
        parse_mode="HTML", 
        message_thread_id=thread_id, 
        reply_to_message_id=message.message_id
    )

    if STICKERS_CHERRIE:
        sticker_elegido = random.choice(STICKERS_CHERRIE)
        try:
            bot.send_sticker(chat_id, sticker_elegido, message_thread_id=thread_id)
        except Exception as e:
            print(f"Error enviando sticker: {e}")

# --- COMANDO /CANCELAR (GLOBAL) ---
@bot.message_handler(commands=['cancelar'])
def cancelar_juego_activo(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes cancelar partidas.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    juego_cancelado = None

    if chat_id in sorteos and sorteos[chat_id]["activo"]:
        if sorteos[chat_id]["admin_id"] != user_id:
            bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla o cancelarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
            return
        sorteos[chat_id]["activo"] = False
        juego_cancelado = "sorteo"

    if quiz_juego["fase"] != "inactivo":
        if quiz_juego["admin_id"] != user_id:
            bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla o cancelarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
            return
        quiz_juego["fase"] = "inactivo"
        juego_cancelado = "quiz de batalla"

    if mineria_juego["fase"] != "inactivo":
        if mineria_juego["admin_id"] != user_id:
            bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla o cancelarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
            return
        mineria_juego["fase"] = "inactivo"
        juego_cancelado = "minería"

    if loteria_juego["fase"] != "inactivo":
        if loteria_juego["admin_id"] != user_id:
            bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla o cancelarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
            return
        loteria_juego["fase"] = "inactivo"
        juego_cancelado = "lotería"

    if juego_cancelado:
        texto = f"ㅤ ୨୧ ࣪ ׅ ㅤla partida de {juego_cancelado} fue cancelada por su admin. ૮ ˶• ˔ •˶ ა"
        bot.send_message(chat_id, texto, message_thread_id=thread_id)
    else:
        bot.send_message(chat_id, " (╥﹏╥)  no hay ninguna partida activa para cancelar.", message_thread_id=thread_id, reply_to_message_id=message.message_id)

# --- SISTEMA DE SORTEOS ---
def generar_texto_sorteo(premio, minutos_restantes=0, ganadores=1):
    return (
        "ㅤㅤㅤ୭ৎ ࣪ ׅ ㅤㅤ ¡Nuevo sorteo!ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ\n\n"
        f"𓂃   premio  :  {premio}\n"
        f"𓂃   tiempo restante  :  {minutos_restantes} minutos\n"
        f"𓂃   ganador/es  :  {ganadores} ganador/es\n\n"
        "ㅤᡣ𐭩ㅤㅤpresiona el botón para unirte."
    )

def generar_texto_resultados(premio, ganador_str, admin_user):
    return (
        "ㅤㅤㅤㅤㅤ୭ৎ ࣪ ׅ ㅤ¡Resultados!ㅤ\n\n"
        f"𓂃   premio  :  {premio}\n"
        f"𓂃   ganador/es  :  [{ganador_str}]\n\n"
        f"ㅤㅤㅤᡣ𐭩ㅤ¡felicidades! reclama con @{admin_user}"
    )

def parsear_comando_sorteo(texto):
    args = texto[7:].strip()
    match = re.search(r'^(.*?)\s+(\d+)([mhdMHD])(?:\s+(\d+))?$', args)
    if match:
        premio = match.group(1).strip()
        cantidad_tiempo = int(match.group(2))
        unidad = match.group(3).lower()
        num_ganadores = int(match.group(4)) if match.group(4) else 1

        segundos = cantidad_tiempo * 60
        if unidad == 'h':
            segundos = cantidad_tiempo * 3600
        elif unidad == 'd':
            segundos = cantidad_tiempo * 86400

        return premio, segundos, num_ganadores
    else:
        return args, 0, 1

@bot.message_handler(commands=['sorteo'])
def crear_sorteo(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar un sorteo.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if chat_id in sorteos and sorteos[chat_id].get("activo"):
        bot.send_message(chat_id, " (╥﹏╥)  ya hay un sorteo en curso.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    raw_text = message.text
    premio, segundos_duracion, num_ganadores = parsear_comando_sorteo(raw_text)

    if not premio:
        bot.send_message(chat_id, "✦ ¡recuerda! debes especificar el premio. Ejemplo: /sorteo 15 robux 20m 1", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    tiempo_finalizacion = time.time() + segundos_duracion if segundos_duracion > 0 else None
    minutos_iniciales = max(1, segundos_duracion // 60) if segundos_duracion > 0 else 0

    admin_username = message.from_user.username if message.from_user.username else message.from_user.first_name

    sorteos[chat_id] = {
        "admin_id": user_id,
        "admin_username": admin_username,
        "premio": premio,
        "participantes": set(),
        "mensaje_id": None,
        "ganadores_anteriores": [],
        "thread_id": thread_id,
        "num_ganadores": num_ganadores,
        "tiempo_fin": tiempo_finalizacion,
        "activo": True
    }

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_sorteo"))

    texto_inicial = generar_texto_sorteo(premio, minutos_restantes=minutos_iniciales, ganadores=num_ganadores)
    msg = bot.send_message(chat_id, texto_inicial, reply_markup=markup, message_thread_id=thread_id)
    sorteos[chat_id]["mensaje_id"] = msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "unirse_sorteo")
def unirse_sorteo_callback(call):
    chat_id = call.message.chat.id
    username = call.from_user.username if call.from_user.username else call.from_user.first_name
    thread_id = call.message.message_thread_id if call.message.is_topic_message else None

    if chat_id not in sorteos or not sorteos[chat_id]["activo"]:
        bot.answer_callback_query(call.id, "Este sorteo ya no está activo.", show_alert=True)
        return

    if username in sorteos[chat_id]["participantes"]:
        bot.answer_callback_query(call.id, "Ya estás participando en este sorteo.", show_alert=True)
        return

    sorteos[chat_id]["participantes"].add(username)
    bot.answer_callback_query(call.id, "¡Te has unido al sorteo!")

    try:
        bot.send_message(chat_id, f"✦⠀¡nuevo participante! @{username}, mucha suerte ♡", message_thread_id=thread_id)
    except Exception:
        pass

def ejecutar_fin_sorteo(chat_id):
    if chat_id not in sorteos or not sorteos[chat_id]["activo"]:
        return

    datos = sorteos[chat_id]
    datos["activo"] = False
    thread_id = datos["thread_id"]
    participantes = list(datos["participantes"])

    try:
        bot.edit_message_reply_markup(chat_id, datos["mensaje_id"], reply_markup=None)
    except Exception:
        pass

    if not participantes:
        bot.send_message(chat_id, " (╥﹏╥)  el sorteo finalizó pero no hubo participantes.", message_thread_id=thread_id)
        del sorteos[chat_id]
        return

    cantidad = min(len(participantes), datos["num_ganadores"])
    ganadores = random.sample(participantes, cantidad)
    datos["ganadores_anteriores"].extend(ganadores)

    str_ganadores = ", ".join([f"@{g}" for g in ganadores])
    texto_ganador = generar_texto_resultados(datos["premio"], str_ganadores, datos["admin_username"])
    bot.send_message(chat_id, texto_ganador, message_thread_id=thread_id)

@bot.message_handler(commands=['endsorteo'])
def finalizar_sorteo(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes finalizar el sorteo.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if chat_id not in sorteos or not sorteos[chat_id]["activo"]:
        bot.send_message(chat_id, " (╥﹏╥)  no hay ningún sorteo activo en este chat.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if sorteos[chat_id]["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    ejecutar_fin_sorteo(chat_id)

@bot.message_handler(commands=['resorteo'])
def resortear(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes resortear.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if chat_id not in sorteos or not sorteos[chat_id]["participantes"]:
        bot.send_message(chat_id, " (╥﹏╥)  no hay un sorteo reciente con participantes para volver a sortear.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if sorteos[chat_id]["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    datos = sorteos[chat_id]
    elegibles = [p for p in datos["participantes"] if p not in datos["ganadores_anteriores"]]
    
    if not elegibles:
        bot.send_message(chat_id, " (╥﹏╥)  no quedan más participantes disponibles para resortear.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    bot.send_message(chat_id, "✦  vaya... al admin no le agradó ese resultado. ¡se elegirán nuevos ganadores en breve!", message_thread_id=thread_id)
    time.sleep(2)

    nuevo_ganador = random.choice(elegibles)
    datos["ganadores_anteriores"].append(nuevo_ganador)

    texto_nuevo_ganador = generar_texto_resultados(datos["premio"], f"@{nuevo_ganador}", datos["admin_username"])
    bot.send_message(chat_id, texto_nuevo_ganador, message_thread_id=thread_id)

def monitor_sorteos():
    while True:
        try:
            ahora = time.time()
            for chat_id, datos in list(sorteos.items()):
                if datos["activo"] and datos["tiempo_fin"]:
                    if ahora >= datos["tiempo_fin"]:
                        ejecutar_fin_sorteo(chat_id)
                    else:
                        min_restantes = max(1, int((datos["tiempo_fin"] - ahora) // 60))
                        try:
                            markup = types.InlineKeyboardMarkup()
                            markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_sorteo"))
                            nuevo_texto = generar_texto_sorteo(datos["premio"], minutos_restantes=min_restantes, ganadores=datos["num_ganadores"])
                            bot.edit_message_text(nuevo_texto, chat_id, datos["mensaje_id"], reply_markup=markup)
                        except Exception:
                            pass
        except Exception as e:
            print(f"Error en monitor de sorteos: {e}")
        time.sleep(30)

hilo_monitor = threading.Thread(target=monitor_sorteos)
hilo_monitor.daemon = True
hilo_monitor.start()

# --- BANCO COMPLETO DE PREGUNTAS ---
BANCO_PREGUNTAS = [
    {"p": "¿cuál es el río más largo del mundo?", "o": ["Amazonas", "Nilo", "Misisipi", "Yangtsé"], "c": 0},
    {"p": "¿en qué año llegó el hombre a la luna?", "o": ["1965", "1969", "1972", "1959"], "c": 1},
    {"p": "¿cuál es el elemento químico más abundante en el universo?", "o": ["Oxígeno", "Helio", "Hidrógeno", "Carbono"], "c": 2},
    {"p": "¿qué país tiene forma de bota?", "o": ["España", "Grecia", "Italia", "Portugal"], "c": 2},
    {"p": "¿cuál es el planeta más grande del sistema solar?", "o": ["Júpiter", "Saturno", "Neptuno", "Marte"], "c": 0},
    {"p": "¿quién pintó la mona lisa?", "o": ["Vincent van Gogh", "Leonardo da Vinci", "Pablo Picasso", "Claude Monet"], "c": 1},
    {"p": "¿cuál es la capital de japón?", "o": ["Kioto", "Osaka", "Tokio", "Hokkaido"], "c": 2},
    {"p": "¿cuántos huesos tiene el cuerpo humano adulto?", "o": ["206", "210", "198", "205"], "c": 0},
    {"p": "¿cuál es el océano más grande del mundo?", "o": ["Atlántico", "Índico", "Pacífico", "Ártico"], "c": 2},
    {"p": "¿en qué continente se encuentra egipto?", "o": ["Asia", "África", "Europa", "Oceanía"], "c": 1},
    {"p": "capital de canadá", "o": ["Ottawa", "Washington", "Varsovia", "Moscú"], "c": 0},
    {"p": "cuál es la pintura de da vinci", "o": ["La noche estrellada", "La última cena", "El grito", "La joven de la perla"], "c": 1},
    {"p": "cuánto es 33 + 292", "o": ["325", "330", "335", "315"], "c": 0},
    {"p": "quién escribió don quijote de la mancha?", "o": ["Gabriel García Márquez", "Miguel de Cervantes Saavedra", "Mario Vargas Llosa", "Isabel Allende"], "c": 1},
    {"p": "cuál es el órgano más grande del ser humano", "o": ["Cerebro", "Piel", "Pulmones", "Intestino delgado"], "c": 1},
    {"p": "cuál es el animal terrestre más rápido", "o": ["León", "Guepardo", "Leopardo", "Puma"], "c": 1},
    {"p": "qué proceso permite a las plantas producir su propio alimento", "o": ["Fotosíntesis", "Respiración celular", "Fermentación", "Transpiración"], "c": 0},
    {"p": "cuál de estas opciones NO pertenece a una célula animal", "o": ["Núcleo", "Membrana plasmática", "Pared celular", "Ribosoma"], "c": 2},
    {"p": "si tengo 6 manzanas y me regalaron 13 más, ¿cuántas tendré en total?", "o": ["19", "20", "18", "67"], "c": 0},
    {"p": "qué youtuber es conocido por saludar como 'hey, buenas a todos, guapísimos...'", "o": ["Germán Garmendia", "Willyrex", "Vegetta777", "ElRubius"], "c": 2},
    {"p": "qué elemento de la tabla periódica es el más electronegativo", "o": ["Bromo", "Flúor", "Oxígeno", "Nitrógeno"], "c": 1},
    {"p": "qué establece la tercera ley de newton?", "o": ["Conservación de energía", "Gravedad", "Acción y reacción", "Inercia"], "c": 2},
    {"p": "qué ocasiona un terremoto", "o": ["Placas tectónicas", "Apertura de la tierra", "Tsunami", "Marea alta"], "c": 0},
    {"p": "quién interpreta a hannah montana", "o": ["Selena Gomez", "Sabrina Carpenter", "Miley Cyrus", "Sofia Carson"], "c": 2},
    {"p": "quién de estas opciones NO es una princesa", "o": ["Aurora", "Bella", "Ariel", "Elsa"], "c": 3},
    {"p": "qué parte del ojo nos permite ver (colores y luz)", "o": ["Retina", "Cristalino", "Córnea", "Pupila"], "c": 0},
    {"p": "un cubo de hielo flota en el agua porque...", "o": ["Es más denso que el agua", "Es menos denso que el agua", "Está en menor proporción", "Por el frío"], "c": 1},
    {"p": "cómo se llama el primer hijo de goku en dragon ball", "o": ["Goten", "Trunks", "Gohan", "Krillin"], "c": 2},
    {"p": "¿en qué año comenzó la primera guerra mundial?", "o": ["1914", "1918", "1939", "1945"], "c": 0},
    {"p": "¿quién pintó la famosa obra 'la noche estrellada'?", "o": ["Pablo Picasso", "Vincent van Gogh", "Leonardo da Vinci", "Salvador Dalí"], "c": 1},
    {"p": "¿cuál es el idioma más hablado en el mundo por hablantes nativos?", "o": ["Inglés", "Español", "Chino mandarín", "Hindi"], "c": 2},
    {"p": "¿qué filósofo griego fue maestro de alejandro magno?", "o": ["Sócrates", "Platón", "Aristóteles", "Pitágoras"], "c": 2},
    {"p": "¿cuál es la capital de australia?", "o": ["Sídney", "Melbourne", "Canberra", "Perth"], "c": 2},
    {"p": "¿en qué continente se encuentra el desierto de gobi?", "o": ["África", "Asia", "Oceanía", "América"], "c": 1},
    {"p": "¿cuál es el país con mayor superficie terrestre en el mundo?", "o": ["Canadá", "Rusia", "Estados Unidos", "China"], "c": 1},
    {"p": "¿cuál es la unidad básica de la vida?", "o": ["Átomo", "Célula", "Molécula", "Tejido"], "c": 1},
    {"p": "¿qué pigmento le da el color verde a las plantas?", "o": ["Clorofila", "Caroteno", "Melanina", "Hemoglobina"], "c": 0},
    {"p": "¿qué órgano del cuerpo humano es responsable de bombear la sangre?", "o": ["Pulmón", "Hígado", "Corazón", "Riñón"], "c": 2},
    {"p": "¿a qué grupo de animales pertenecen las ballenas?", "o": ["Peces", "Mamíferos", "Anfibios", "Reptiles"], "c": 1},
    {"p": "¿cuánto es 7 x 8?", "o": ["54", "56", "64", "48"], "c": 1},
    {"p": "¿cuál es la raíz cuadrada de 81?", "o": ["8", "9", "12", "7"], "c": 1},
    {"p": "¿cómo se llama un triángulo que tiene sus tres lados de igual longitud?", "o": ["Isósceles", "Escaleno", "Equilátero", "Rectángulo"], "c": 2},
    {"p": "si un ángulo mide exactamente 90 grados, ¿cómo se clasifica?", "o": ["Agudo", "Recto", "Obtuso", "Llano"], "c": 1},
    {"p": "¿qué científico formuló la ley de la gravitación universal?", "o": ["Albert Einstein", "Isaac Newton", "Galileo Galilei", "Nikola Tesla"], "c": 1},
    {"p": "¿qué banda femenina de k-pop lanzó 'ddu-du ddu-du'?", "o": ["TWICE", "BLACKPINK", "Red Velvet", "Aespa"], "c": 1},
    {"p": "¿cómo se llama el fandom oficial del grupo bts?", "o": ["BLINK", "ONCE", "ARMY", "STAY"], "c": 2},
    {"p": "¿qué canción de psy se convirtió en un fenómeno viral en 2012?", "o": ["Gangnam Style", "Gentleman", "Dynamite", "Butter"], "c": 0},
    {"p": "¿qué artista pop es conocida por álbumes como 1989 y folklore?", "o": ["Ariana Grande", "Taylor Swift", "Katy Perry", "Billie Eilish"], "c": 1},
    {"p": "¿cuál es el nombre del hermano de mario en nintendo?", "o": ["Wario", "Yoshi", "Luigi", "Toad"], "c": 2},
    {"p": "¿en qué juego construyes estructuras con bloques?", "o": ["Roblox", "Minecraft", "Terraria", "Fortnite"], "c": 1},
    {"p": "¿quién dirigió la película jurassic park (1993)?", "o": ["James Cameron", "Steven Spielberg", "Christopher Nolan", "George Lucas"], "c": 1},
    {"p": "¿qué película sobre un naufragio ganó el óscar en 1998?", "o": ["Titanic", "Avatar", "Gladiador", "Inception"], "c": 0},
    {"p": "¿cuál es el nombre del villano principal en la trilogía original de star wars?", "o": ["Voldemort", "Darth Vader", "Sauron", "Thanos"], "c": 1}
]

# --- VER LISTA DE PREGUNTAS (/QUESTIONS) ---
@bot.message_handler(commands=['questions'])
def ver_todas_las_preguntas(message):
    username = message.from_user.username
    if message.chat.type == 'private' and username and username.lower() == 'kirschteiinz':
        texto = "      ‿︵       𝘉𝘢𝘯𝘤𝘰 𝘥𝘦 𝘗𝘳𝘦𝘨𝘶𝘯𝘵𝘢𝘴   Cherrie !\n\n"
        for idx, q in enumerate(BANCO_PREGUNTAS, start=1):
            texto += f"**{idx}. {q['p']}**\n"
            for o_idx, opcion in enumerate(q['o']):
                es_correcta = " (✓)" if o_idx == q['c'] else ""
                texto += f"᭍᭭ {opcion}{es_correcta}\n"
            texto += "\n"
            if len(texto) > 3500:
                bot.send_message(message.chat.id, texto, parse_mode="Markdown")
                texto = ""
        if texto:
            bot.send_message(message.chat.id, texto, parse_mode="Markdown")

# --- SISTEMA DE QUIZ ---
def generar_texto_lobby_quiz():
    participantes_str = "\n".join([f"✦    @{p}" for p in quiz_juego["participantes"]]) if quiz_juego["participantes"] else "✦    (esperando participantes...)"
    return (
        "ㅤ ꯳⃘꤫ ㅤㅤ¡hora del Quiz de Batalla!\n"
        f"—  únete a la batalla para demostrar tus conocimientos y llevarte {quiz_juego['premio']}.\n\n"
        "participantes:\n"
        f"{participantes_str}\n\n"
        "— para iniciar ; /quizstart."
    )

@bot.message_handler(commands=['quiz'])
def crear_lobby_quiz(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar un quiz.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if quiz_juego["fase"] != "inactivo":
        bot.send_message(chat_id, " (╥﹏╥)  ya hay un quiz en proceso o un lobby abierto.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    premio = message.text[5:].strip()
    if not premio:
        bot.send_message(chat_id, "✦ ¡recuerda! debes especificar el premio. Ejemplo: /quiz VIP Mensual", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    quiz_juego["fase"] = "lobby"
    quiz_juego["chat_id"] = chat_id
    quiz_juego["thread_id"] = thread_id
    quiz_juego["admin_id"] = user_id
    quiz_juego["premio"] = premio
    quiz_juego["participantes"].clear()
    quiz_juego["participantes_activos"].clear()
    quiz_juego["dificultad"] = 1
    quiz_juego["preguntas_usadas"].clear()

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_quiz_lobby"))

    msg = bot.send_message(chat_id, generar_texto_lobby_quiz(), reply_markup=markup, message_thread_id=thread_id)
    quiz_juego["msg_lobby_id"] = msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "unirse_quiz_lobby")
def unirse_quiz_callback(call):
    if quiz_juego["fase"] != "lobby":
        bot.answer_callback_query(call.id, "El lobby ya no está disponible.", show_alert=True)
        return

    username = call.from_user.username if call.from_user.username else call.from_user.first_name
    if username in quiz_juego["participantes"]:
        bot.answer_callback_query(call.id, "Ya estás en el lobby.", show_alert=True)
        return

    quiz_juego["participantes"].add(username)
    bot.answer_callback_query(call.id, "¡Te has unido al Quiz!")

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_quiz_lobby"))
    try:
        bot.edit_message_text(generar_texto_lobby_quiz(), quiz_juego["chat_id"], quiz_juego["msg_lobby_id"], reply_markup=markup)
    except Exception:
        pass

@bot.message_handler(commands=['quizstart'])
def iniciar_partida_quiz(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar el quiz.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if quiz_juego["fase"] != "lobby":
        bot.send_message(chat_id, " (╥﹏╥)  no hay ningún lobby esperando para iniciar.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if quiz_juego["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if len(quiz_juego["participantes"]) < 2:
        bot.send_message(chat_id, " (╥﹏╥)  se necesitan al menos 2 participantes para comenzar.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    try:
        bot.edit_message_reply_markup(chat_id, quiz_juego["msg_lobby_id"], reply_markup=None)
    except Exception:
        pass

    quiz_juego["fase"] = "jugando"
    quiz_juego["participantes_activos"] = set(quiz_juego["participantes"])

    bot.send_message(chat_id, "ㅤ ꯳⃘꤫ ㅤ ¡Lobby cerrado! La batalla del Quiz comienza ahora...", message_thread_id=thread_id)
    lanzar_siguiente_pregunta(chat_id)

def lanzar_siguiente_pregunta(chat_id):
    thread_id = quiz_juego["thread_id"]
    if len(quiz_juego["participantes_activos"]) <= 1:
        finalizar_juego_quiz(chat_id)
        return

    disponibles = [q for q in BANCO_PREGUNTAS if q["p"] not in quiz_juego["preguntas_usadas"]]
    if not disponibles:
        quiz_juego["preguntas_usadas"].clear()
        disponibles = BANCO_PREGUNTAS

    pregunta_obj = random.choice(disponibles)
    quiz_juego["preguntas_usadas"].append(pregunta_obj["p"])
    quiz_juego["pregunta_actual"] = pregunta_obj
    quiz_juego["opcion_correcta"] = pregunta_obj["c"]
    quiz_juego["respuestas"].clear()

    tiempo_limite = max(5, 20 - (quiz_juego["dificultad"] - 1) * 2)

    texto_pregunta = (
        f"ㅤㅤㅤㅤㅤfn୭ৎ ࣪ ׅ ㅤRonda {quiz_juego['dificultad']}ㅤ (Sobrevivientes: {len(quiz_juego['participantes_activos'])})\n\n"
        f"𓂃   **Pregunta:** {pregunta_obj['p']}\n\n"
        f"⏱️ ¡Tienen **{tiempo_limite} segundos** para responder!"
    )

    markup = types.InlineKeyboardMarkup()
    for idx, opcion in enumerate(pregunta_obj["o"]):
        markup.add(types.InlineKeyboardButton(f"᭍᭭ {opcion}", callback_data=f"quiz_ans_{idx}"))

    msg = bot.send_message(chat_id, texto_pregunta, reply_markup=markup, parse_mode="Markdown", message_thread_id=thread_id)
    quiz_juego["msg_pregunta_id"] = msg.message_id

    hilo_timer = threading.Thread(target=temporizador_pregunta, args=(chat_id, quiz_juego["dificultad"], tiempo_limite))
    hilo_timer.daemon = True
    hilo_timer.start()

@bot.callback_query_handler(func=lambda call: call.data.startswith("quiz_ans_"))
def procesar_respuesta_quiz(call):
    if quiz_juego["fase"] != "jugando":
        bot.answer_callback_query(call.id, "No hay ningún quiz activo.", show_alert=True)
        return

    username = call.from_user.username if call.from_user.username else call.from_user.first_name

    if username not in quiz_juego["participantes_activos"]:
        bot.answer_callback_query(call.id, "Ya fuiste eliminado o no estabas en esta partida.", show_alert=True)
        return

    if username in quiz_juego["respuestas"]:
        bot.answer_callback_query(call.id, "Ya enviaste tu respuesta para esta pregunta.", show_alert=True)
        return

    opcion_elegida = int(call.data.split("_")[2])
    quiz_juego["respuestas"][username] = {
        "opcion": opcion_elegida,
        "tiempo": time.time()
    }
    bot.answer_callback_query(call.id, "¡Respuesta registrada!")

def temporizador_pregunta(chat_id, dificultad_objetivo, segundos):
    time.sleep(segundos)
    if quiz_juego["fase"] == "jugando" and quiz_juego["dificultad"] == dificultad_objetivo:
        evaluar_resultados_ronda(chat_id)

def evaluar_resultados_ronda(chat_id):
    thread_id = quiz_juego["thread_id"]
    try:
        bot.edit_message_reply_markup(chat_id, quiz_juego["msg_pregunta_id"], reply_markup=None)
    except Exception:
        pass

    correcta_idx = quiz_juego["opcion_correcta"]
    texto_correcta = quiz_juego["pregunta_actual"]["o"][correcta_idx]
    
    acertaron = []
    eliminados_ronda = set()

    for p in list(quiz_juego["participantes_activos"]):
        if p in quiz_juego["respuestas"]:
            resp = quiz_juego["respuestas"][p]
            if resp["opcion"] == correcta_idx:
                acertaron.append((p, resp["tiempo"]))
                quiz_aciertos[p] = quiz_aciertos.get(p, 0) + 1
            else:
                eliminados_ronda.add(p)
        else:
            eliminados_ronda.add(p)

    es_ultima_ronda_2p = (len(quiz_juego["participantes_activos"]) == 2)
    mensaje_eliminacion_especial = ""

    if es_ultima_ronda_2p and len(acertaron) == 2:
        acertaron.sort(key=lambda x: x[1])  # Ordenar por tiempo (el más rápido primero)
        mas_lento = acertaron[1][0]
        eliminados_ronda.add(mas_lento)
        sobrevivientes_ronda = {acertaron[0][0]}
        mensaje_eliminacion_especial = f"¡todos acertaron! pero @{mas_lento}, al ser el último en responder, quedó descalificado."
    else:
        sobrevivientes_ronda = {p for p, t in acertaron}

    if len(sobrevivientes_ronda) == 0:
        texto_resumen = (
            " (๑>ᴗ<๑)  ¡tiempo agotado!\n\n"
            f"𓂃   La respuesta correcta era  :  **{texto_correcta}**\n\n"
            "✦   ¡Nadie acertó en esta ronda! Todos se salvan por piedad y continúan... ٩(ˊᗜˋ*)o"
        )
    else:
        quiz_juego["participantes_activos"] = sobrevivientes_ronda
        
        if mensaje_eliminacion_especial:
            texto_resumen = (
                " (๑>ᴗ<๑)  ¡tiempo agotado!\n\n"
                f"𓂃   La respuesta correcta era  :  **{texto_correcta}**\n\n"
                f"✦   {mensaje_eliminacion_especial}"
            )
        else:
            str_eliminados = ", ".join([f"@{e}" for e in eliminados_ronda]) if eliminados_ronda else "Nadie"
            texto_resumen = (
                " (๑>ᴗ<๑)  ¡tiempo agotado!\n\n"
                f"𓂃   La respuesta correcta era  :  **{texto_correcta}**\n\n"
                f"𓂃   Eliminados / AFK  :  {str_eliminados}\n"
                f"𓂃   Sobrevivientes  :  {len(sobrevivientes_ronda)}"
            )

    bot.send_message(chat_id, texto_resumen, parse_mode="Markdown", message_thread_id=thread_id)

    if len(quiz_juego["participantes_activos"]) <= 1:
        finalizar_juego_quiz(chat_id)
    else:
        quiz_juego["dificultad"] += 1
        bot.send_message(chat_id, "✦⠀¡Siguiente ronda en 5 segundos! Prepárense... ૮ ˶• ˔ •˶ ა", message_thread_id=thread_id)
        time.sleep(5)
        lanzar_siguiente_pregunta(chat_id)

def finalizar_juego_quiz(chat_id):
    thread_id = quiz_juego["thread_id"]
    if len(quiz_juego["participantes_activos"]) == 1:
        ganador = list(quiz_juego["participantes_activos"])[0]
        texto_final = (
            "ㅤㅤㅤㅤㅤfn୭ৎ ࣪ ׅ ㅤ¡FIN DEL QUIZ!ㅤ\n\n"
            f"ㅤㅤㅤᡣ𐭩ㅤ¡felicidades @{ganador}! fuiste el único sobreviviente y ganaste {quiz_juego['premio']} ♡."
        )
    else:
        texto_final = " (╥﹏╥)  ¡todos fueron eliminados! no hay ganador para este quiz."

    bot.send_message(chat_id, texto_final, message_thread_id=thread_id)
    quiz_juego["fase"] = "inactivo"

@bot.message_handler(commands=['quizlegends'])
def ver_leyendas_quiz(message):
    thread_id = get_thread_id(message)
    if not quiz_aciertos:
        bot.send_message(message.chat.id, " (╥﹏╥)  aún no hay registros de aciertos en el quiz.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    ordenados = sorted(quiz_aciertos.items(), key=lambda x: x[1], reverse=True)
    lineas = [f"{idx:02d}. @{u} — {aciertos} rondas acertadas" for idx, (u, aciertos) in enumerate(ordenados, start=1)]
    texto = "      ‿︵       𝘘𝘶𝘪𝘻 𝘓𝘦𝘨𝘦𝘯𝘥𝘴 !\n\n" + "\n".join(lineas)
    bot.send_message(message.chat.id, texto, message_thread_id=thread_id)

# --- JUEGO DE MINERÍA ---
OPCIONES_MINERIA = [
    {"probabilidad": 20, "puntos": 0, "texto": "nada... ( ꩜ ᯅ ꩜;)\n¡suerte para la próxima!"},
    {"probabilidad": 18, "puntos": 3, "texto": " una piedrita común...\n૮ • ﻌ - a ¡tienes 3 puntos!"},
    {"probabilidad": 15, "puntos": 5, "texto": " un pedacito de carbón...\n(´๑•_•๑) no es mucho, pero sirve...\n¡tienes 5 puntos!"},
    {"probabilidad": 12, "puntos": 8, "texto": "✦ una piedra que brilla un poquito...\n૮₍´｡• ᵕ •｡`₎a ¡tienes 8 puntos!"},
    {"probabilidad": 10, "puntos": 12, "texto": " un cristal de cuarzo pequeño...\n(ᐡ･ ﻌ ･ᐡ) ¡qué bonito!\n¡tienes 12 puntos!"},
    {"probabilidad": 8, "puntos": 18, "texto": " una pequeña cueva con honguitos brillantes...\n꒰◍ॢ•ᴗ•◍ॢ꒱ ¡tienes 18 puntos!"},
    {"probabilidad": 6, "puntos": 25, "texto": "⚙ un fragmento de hierro antiguo...\n૮₍˶• . • ⑅₎a parece útil...\n¡tienes 25 puntos!"},
    {"probabilidad": 4, "puntos": 32, "texto": " un cristal azul escondido...\n૮ ˶• ˔ •˶ a ¡qué hallazgo tan lindo!\n¡tienes 32 puntos!"},
    {"probabilidad": 3, "puntos": 40, "texto": " una moneda vieja enterrada...\n૮꒰ต´˘`ต꒱a alguien la perdió hace mucho...\n¡tienes 40 puntos!"},
    {"probabilidad": 2, "puntos": 50, "texto": " una amatista brillante...\n(∗˃̶ ᵕ ˂̶∗) ¡encontraste algo especial!\n¡tienes 50 puntos!"},
    {"probabilidad": 1.5, "puntos": 60, "texto": " un cristal con energía extraña...\n૮꒰˶˃̵ ^ ˂̵˵꒱a ¡brilla muchísimo!\n¡tienes 60 puntos!"},
    {"probabilidad": 1.0, "puntos": 70, "texto": " un pequeño cofre bajo las rocas...\n૮꒰⑅ᐢ ᵕ ᵕ ᐢ⑅꒱ ¡¿qué habrá dentro?!\n¡tienes 70 puntos!"},
    {"probabilidad": 0.8, "puntos": 78, "texto": " una perla escondida bajo la tierra...\n(⑅˘͈ ᵕ ˘͈ )  ¡es preciosa!\n¡tienes 78 puntos!"},
    {"probabilidad": 0.5, "puntos": 85, "texto": "✦ una pequeña veta de oro...\n໒꒰ྀི ∩ ˃ ᵕ ˂ ∩ ꒱ྀི১ ¡qué suerte!\n¡tienes 85 puntos!"},
    {"probabilidad": 0.3, "puntos": 90, "texto": " un zafiro muy raro...\n૮꒰ྀི ᵔ ๑ ᵔ ꒱a ¡tuviste mucha suerte!\n¡tienes 90 puntos!"},
    {"probabilidad": 0.2, "puntos": 95, "texto": " un diamante rosa brillante...\n♡ ᖭི(ˊᗜˋ*)ᖫྀ ¡ES HERMOSO!\n¡tienes 95 puntos!"},
    {"probabilidad": 0.1, "puntos": 100, "texto": " el tesoro secreto de Cherrie...\n(♡´𓈒𓂂˘˘`♡) ¡encontraste algo que casi nadie encuentra!\n¡tienes 100 puntos!"}
]

def generar_texto_lobby_mineria():
    participantes_str = "\n".join([f"✦ @{p} se ha unido. ¿listo para minar?" for p in mineria_juego["participantes"]]) if mineria_juego["participantes"] else "✦ (esperando participantes...)"
    return (
        "ㅤㅤᡣ𐭩ㅤㅤㅤ¡hora de minar!\n"
        "prueba tu suerte y únete para ganar o perder minery points.\n\n"
        f"{participantes_str}"
    )

@bot.message_handler(commands=['mineria'])
def crear_lobby_mineria(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar minería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if mineria_juego["fase"] != "inactivo":
        bot.send_message(chat_id, " (╥﹏╥)  ya hay una sesión de minería en proceso o un lobby abierto.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    premio = message.text[8:].strip()
    if not premio:
        bot.send_message(chat_id, "✦ ¡recuerda! debes especificar el premio. Ejemplo: /mineria 5 robux", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    mineria_juego["fase"] = "lobby"
    mineria_juego["chat_id"] = chat_id
    mineria_juego["thread_id"] = thread_id
    mineria_juego["admin_id"] = user_id
    mineria_juego["premio"] = premio
    mineria_juego["participantes"].clear()
    mineria_juego["puntos"].clear()
    mineria_juego["turnos_restantes"].clear()
    mineria_juego["turno_actual_index"] = 0

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("fn୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_mineria_lobby"))

    msg = bot.send_message(chat_id, generar_texto_lobby_mineria(), reply_markup=markup, message_thread_id=thread_id)
    mineria_juego["msg_lobby_id"] = msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "unirse_mineria_lobby")
def unirse_mineria_callback(call):
    if mineria_juego["fase"] != "lobby":
        bot.answer_callback_query(call.id, "El lobby ya no está disponible.", show_alert=True)
        return

    username = call.from_user.username if call.from_user.username else call.from_user.first_name
    if username in mineria_juego["participantes"]:
        bot.answer_callback_query(call.id, "Ya estás en el lobby.", show_alert=True)
        return

    mineria_juego["participantes"].append(username)
    mineria_juego["puntos"][username] = 0
    mineria_juego["turnos_restantes"][username] = random.randint(3, 4)
    bot.answer_callback_query(call.id, "¡Te has unido a la minería!")

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("fn୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_mineria_lobby"))
    try:
        bot.edit_message_text(generar_texto_lobby_mineria(), mineria_juego["chat_id"], mineria_juego["msg_lobby_id"], reply_markup=markup)
    except Exception:
        pass

@bot.message_handler(commands=['mineriastart'])
def iniciar_partida_mineria(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar la minería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if mineria_juego["fase"] != "lobby":
        bot.send_message(chat_id, " (╥﹏╥)  no hay ningún lobby esperando para iniciar.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if mineria_juego["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if not mineria_juego["participantes"]:
        bot.send_message(chat_id, " (╥﹏╥)  se necesita al menos 1 participante para comenzar.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    try:
        bot.edit_message_reply_markup(chat_id, mineria_juego["msg_lobby_id"], reply_markup=None)
    except Exception:
        pass

    mineria_juego["fase"] = "jugando"
    random.shuffle(mineria_juego["participantes"])
    mineria_juego["turno_actual_index"] = 0

    anunciar_turno_mineria()

def anunciar_turno_mineria():
    chat_id = mineria_juego["chat_id"]
    thread_id = mineria_juego["thread_id"]
    
    usuario_actual = mineria_juego["participantes"][mineria_juego["turno_actual_index"]]
    texto = (
        f"ㅤ୭ৎ ࣪ ׅ ㅤㅤ¡turno de @{usuario_actual}!\n"
        "ㅤ— ㅤㅤusa /minar para probar tu suerte."
    )
    bot.send_message(chat_id, texto, message_thread_id=thread_id)

@bot.message_handler(commands=['minar'])
def realizar_accion_minar(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)

    if mineria_juego["fase"] != "jugando":
        return

    username = message.from_user.username if message.from_user.username else message.from_user.first_name
    usuario_esperado = mineria_juego["participantes"][mineria_juego["turno_actual_index"]]

    if username != usuario_esperado:
        bot.send_message(chat_id, f"(´.•﹏•`)  @{username}, aún no es tu turno. Es el turno de @{usuario_esperado}.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    pesos = [o["probabilidad"] for o in OPCIONES_MINERIA]
    resultado = random.choices(OPCIONES_MINERIA, weights=pesos, k=1)[0]

    mineria_juego["puntos"][username] += resultado["puntos"]
    mineria_historico[username] = mineria_historico.get(username, 0) + resultado["puntos"]
    mineria_juego["turnos_restantes"][username] -= 1

    texto_resultado = f"✦ @{username}, encontraste...\n\n{resultado['texto']}"
    bot.send_message(chat_id, texto_resultado, message_thread_id=thread_id)

    avanzar_turno_mineria()

def avanzar_turno_mineria():
    todos_terminaron = all(mineria_juego["turnos_restantes"][p] <= 0 for p in mineria_juego["participantes"])
    
    if todos_terminaron:
        finalizar_juego_mineria()
        return

    num_p = len(mineria_juego["participantes"])
    for _ in range(num_p):
        mineria_juego["turno_actual_index"] = (mineria_juego["turno_actual_index"] + 1) % num_p
        u_siguiente = mineria_juego["participantes"][mineria_juego["turno_actual_index"]]
        if mineria_juego["turnos_restantes"][u_siguiente] > 0:
            break

    time.sleep(5)
    anunciar_turno_mineria()

@bot.message_handler(commands=['bestminers'])
def ver_top_mineria(message):
    thread_id = get_thread_id(message)

    if not mineria_historico:
        bot.send_message(message.chat.id, " (╥﹏╥)  no hay ningún registro histórico de minería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    ordenados = sorted(mineria_historico.items(), key=lambda x: x[1], reverse=True)
    lineas = [f"{idx:02d}. @{u} — {pts} pts" for idx, (u, pts) in enumerate(ordenados, start=1)]
    texto = "      ‿︵       𝘉𝘦𝘴𝘵 𝘔𝘪𝘯𝘦𝘳𝘴 (Historico) !\n\n" + "\n".join(lineas)
    bot.send_message(message.chat.id, texto, message_thread_id=thread_id)

def finalizar_juego_mineria():
    chat_id = mineria_juego["chat_id"]
    thread_id = mineria_juego["thread_id"]

    ordenados = sorted(mineria_juego["puntos"].items(), key=lambda x: x[1], reverse=True)
    
    if not ordenados:
        bot.send_message(chat_id, " (╥﹏╥)  la minería terminó sin registros.", message_thread_id=thread_id)
        mineria_juego["fase"] = "inactivo"
        return

    ganador, pts_ganador = ordenados[0]
    lineas_clasificacion = [f"{idx:02d}. @{user} — {pts} pts" for idx, (user, pts) in enumerate(ordenados, start=1)]
    texto_clasificacion = "\n".join(lineas_clasificacion)

    texto_final = (
        f"¡tenemos un ganador! @{ganador} se ha convertido en el mejor minero y se lleva consigo {mineria_juego['premio']}\n\n"
        "      ‿︵       𝘉𝘦𝘴𝘵 𝘔𝘪𝘯𝘦𝘳𝘴 !\n\n"
        f"{texto_clasificacion}"
    )

    bot.send_message(chat_id, texto_final, message_thread_id=thread_id)
    mineria_juego["fase"] = "inactivo"

@bot.message_handler(commands=['endmineria'])
def terminar_mineria_manual(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes finalizar la minería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if mineria_juego["fase"] == "inactivo":
        bot.send_message(chat_id, " (╥﹏╥)  no hay ninguna minería activa.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if mineria_juego["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    finalizar_juego_mineria()

# --- JUEGO DE LOTERÍA ---
@bot.message_handler(commands=['loteria'])
def iniciar_loteria(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar la lotería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if loteria_juego["fase"] != "inactivo":
        bot.send_message(chat_id, " (╥﹏╥)  ya hay una lotería activa.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    premio = message.text[8:].strip()
    if not premio:
        bot.send_message(chat_id, "✦ ¡recuerda! debes especificar el premio. Ejemplo: /loteria 15 robux", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    loteria_juego["fase"] = "comprando"
    loteria_juego["chat_id"] = chat_id
    loteria_juego["thread_id"] = thread_id
    loteria_juego["admin_id"] = user_id
    loteria_juego["premio"] = premio
    loteria_juego["tickets_vendidos"].clear()
    loteria_juego["usuarios_registrados"].clear()
    loteria_juego["ticket_ganador"] = None
    loteria_juego["ganador_esperado"] = None
    loteria_juego["reclamado"] = False

    texto = (
        "ㅤ୭ৎ ࣪ ׅ ㅤㅤ¡ha empezado la lotería!\n"
        f"prueba tu suerte comprando tus tickets, usa /tickets para recibir 5 oportunidades para ganar el premio mayor, {premio}."
    )
    bot.send_message(chat_id, texto, message_thread_id=thread_id)

@bot.message_handler(commands=['tickets'])
def obtener_tickets(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)

    if loteria_juego["fase"] != "comprando":
        return

    username = message.from_user.username if message.from_user.username else message.from_user.first_name

    if username in loteria_juego["usuarios_registrados"]:
        bot.send_message(chat_id, f"(´.•﹏•`) @{username}, ya recibiste tus 5 tickets para esta lotería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    loteria_juego["usuarios_registrados"].add(username)
    
    tickets_generados = []
    for _ in range(5):
        num_code = f"{random.randint(1000, 9999)}"
        code_str = f"CHERRY{num_code}"
        loteria_juego["tickets_vendidos"][code_str] = username
        tickets_generados.append(f"`{code_str}`")

    texto_res = "\n".join(tickets_generados)
    bot.send_message(chat_id, texto_res, parse_mode="Markdown", message_thread_id=thread_id, reply_to_message_id=message.message_id)

@bot.message_handler(commands=['jugarloteria'])
def jugar_loteria(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes lanzar la lotería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if loteria_juego["fase"] != "comprando" or not loteria_juego["tickets_vendidos"]:
        bot.send_message(chat_id, " (╥﹏╥)  no hay tickets vendidos para realizar el sorteo.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if loteria_juego["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    ticket_ganador, dueno = random.choice(list(loteria_juego["tickets_vendidos"].items()))
    loteria_juego["ticket_ganador"] = ticket_ganador
    loteria_juego["ganador_esperado"] = dueno
    loteria_juego["fase"] = "esperando_reclamo"

    texto = (
        "ㅤㅤᡣ𐭩ㅤㅤㅤresultados de la lotería cherrie . . .\n"
        f"         —         nuestro ticket ganador es el `{ticket_ganador}`.\n"
        "el ganador tiene 45 segundos para escribir ¡lotería! en el chat y asegurar su victoria."
    )
    bot.send_message(chat_id, texto, parse_mode="Markdown", message_thread_id=thread_id)

    hilo_reclamo = threading.Thread(target=temporizador_reclamo_loteria, args=(chat_id, dueno, thread_id))
    hilo_reclamo.daemon = True
    hilo_reclamo.start()

def temporizador_reclamo_loteria(chat_id, dueno, thread_id):
    time.sleep(45)
    if loteria_juego["fase"] == "esperando_reclamo" and not loteria_juego["reclamado"]:
        texto = f"✦   @{dueno} no reclamó su lotería... (´๑•_•๑)"
        bot.send_message(chat_id, texto, message_thread_id=thread_id)
        loteria_juego["fase"] = "inactivo"

@bot.message_handler(func=lambda m: m.text and m.text.strip().lower() in ['¡lotería!', '¡loteria!', 'loteria', 'lotería'])
def reclamar_loteria(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)

    if loteria_juego["fase"] == "esperando_reclamo" and not loteria_juego["reclamado"]:
        username = message.from_user.username if message.from_user.username else message.from_user.first_name
        if username == loteria_juego["ganador_esperado"]:
            loteria_juego["reclamado"] = True
            texto = f"✦  ¡@{username}  es el ganador de la lotería! ha ganado {loteria_juego['premio']} ♡"
            bot.send_message(chat_id, texto, message_thread_id=thread_id)
            loteria_juego["fase"] = "inactivo"

# --- SISTEMA DE PUNTOS MANUALES ---
@bot.message_handler(commands=['add'])
def agregar_puntos(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes añadir puntos.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    partes = message.text.split()
    if len(partes) < 3 or not partes[1].startswith('@') or not (partes[2].isdigit() or (partes[2].startswith('-') and partes[2][1:].isdigit())):
        bot.send_message(chat_id, "✦  Uso correcto: /add @usuario [monto]", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    usuario = partes[1].replace('@', '').strip()
    monto = int(partes[2])

    puntos_sistema[usuario] = puntos_sistema.get(usuario, 0) + monto
    bot.send_message(chat_id, f"✦  ¡se le añadieron {monto} puntos a @{usuario}! ♡", message_thread_id=thread_id, reply_to_message_id=message.message_id)

@bot.message_handler(commands=['rest'])
def restar_puntos(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes restar puntos.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    partes = message.text.split()
    if len(partes) < 3 or not partes[1].startswith('@') or not (partes[2].isdigit() or (partes[2].startswith('-') and partes[2][1:].isdigit())):
        bot.send_message(chat_id, "✦  Uso correcto: /rest @usuario [monto]", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    usuario = partes[1].replace('@', '').strip()
    monto = int(partes[2])

    puntos_sistema[usuario] = puntos_sistema.get(usuario, 0) - monto
    bot.send_message(chat_id, f"✦  ¡se le restaron {monto} puntos a @{usuario}! ♡", message_thread_id=thread_id, reply_to_message_id=message.message_id)

@bot.message_handler(commands=['check'])
def ver_cartilla_puntos(message):
    thread_id = get_thread_id(message)

    if not puntos_sistema:
        bot.send_message(message.chat.id, " (╥﹏╥)  no hay puntos registrados por el momento.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    ordenados = sorted(puntos_sistema.items(), key=lambda x: x[1], reverse=True)
    
    lineas_top = []
    for idx, (user, pts) in enumerate(ordenados, start=1):
        lineas_top.append(f"{idx:02d}  ;  @{user} ({pts} pts)")

    top_texto = "\n".join(lineas_top)
    
    total_a_pagar = sum(pts for pts in puntos_sistema.values() if pts > 0)

    cartilla = (
        "  丙        ◟     point list.           𝆬          \n\n"
        f"{top_texto}\n\n"
        f"   ୨୧        𝅄     total   ;    {total_a_pagar}"
    )
    bot.send_message(message.chat.id, cartilla, message_thread_id=thread_id)

@bot.message_handler(commands=['clear'])
def reiniciar_puntos(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes reiniciar los puntos.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    puntos_sistema.clear()
    bot.send_message(chat_id, "✦  ¡la lista de puntos ha sido reiniciada por completo! ♡", message_thread_id=thread_id, reply_to_message_id=message.message_id)

# --- MANEJO DE COMANDOS INVÁLIDOS ---
@bot.message_handler(func=lambda message: message.text and message.text.startswith('/') and message.text.split()[0] not in [
    '/start', '/help', '/sorteo', '/endsorteo', '/resorteo', '/quiz', '/quizstart', '/endquiz', '/quizlegends', 
    '/mineria', '/mineriastart', '/minar', '/bestminers', '/endmineria', '/add', '/rest', '/check', '/clear',
    '/cancelar', '/beg', '/loteria', '/tickets', '/jugarloteria', '/questions', '/comandos', '/refe'
])
def manejar_comandos_invalidos(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if es_admin(chat_id, user_id):
        bot.send_message(chat_id, "(´.•﹏•`) comando no disponible.", message_thread_id=thread_id, reply_to_message_id=message.message_id)

# --- INICIALIZACIÓN PROTEGIDA ---
if __name__ == '__main__':
    print("Bot Cherrie en funcionamiento...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"Alerta: Se interrumpió la conexión ({e}). Reconectando en 5 segundos...")
            time.sleep(5)
