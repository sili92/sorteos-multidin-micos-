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

# --- ESTADOS GLOBALES ---
sorteos = {}

quiz_juego = {
    "fase": "inactivo",        # "inactivo", "lobby", "jugando"
    "chat_id": None,
    "thread_id": None,
    "premio": "",
    "participantes": {},       # {user_id: username}
    "sobrevivientes": {},      # {user_id: username}
    "respondieron_correcto": set(),
    "pregunta_actual": None,
    "ronda": 0,
    "msg_lobby_id": None,
    "preguntas_usadas": []
}

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
    {"p": "¿en qué año comenzó la primera guerra mundial?", "o": ["1914", "1918", "1939"], "c": 0},
    {"p": "¿quién pintó la famosa obra 'la noche estrellada'?", "o": ["Pablo Picasso", "Vincent van Gogh", "Leonardo da Vinci"], "c": 1},
    {"p": "¿cuál es el idioma más hablado en el mundo por hablantes nativos?", "o": ["Inglés", "Español", "Chino mandarín"], "c": 2},
    {"p": "¿qué filósofo griego fue maestro de alejandro magno?", "o": ["Sócrates", "Platón", "Aristóteles"], "c": 2},
    {"p": "¿cuál es la capital de australia?", "o": ["Sídney", "Melbourne", "Canberra"], "c": 2},
    {"p": "¿en qué continente se encuentra el desierto de gobi?", "o": ["África", "Asia", "Oceanía"], "c": 1},
    {"p": "¿cuál es el país con mayor superficie terrestre en el mundo?", "o": ["Canadá", "Rusia", "Estados Unidos"], "c": 1},
    {"p": "¿cuál es la unidad básica de la vida?", "o": ["Átomo", "Célula", "Molécula"], "c": 1},
    {"p": "¿qué pigmento le da el color verde a las plantas?", "o": ["Clorofila", "Caroteno", "Melanina"], "c": 0},
    {"p": "¿qué órgano del cuerpo humano es responsable de bombear la sangre?", "o": ["Pulmón", "Hígado", "Corazón"], "c": 2},
    {"p": "¿a qué grupo de animales pertenecen las ballenas?", "o": ["Peces", "Mamíferos", "Anfibios"], "c": 1},
    {"p": "¿cuánto es 7 x 8?", "o": ["54", "56", "64"], "c": 1},
    {"p": "¿cuál es la raíz cuadrada de 81?", "o": ["8", "9", "12"], "c": 1},
    {"p": "¿cómo se llama un triángulo que tiene sus tres lados de igual longitud?", "o": ["Isósceles", "Escaleno", "Equilátero"], "c": 2},
    {"p": "si un ángulo mide exactamente 90 grados, ¿cómo se clasifica?", "o": ["Agudo", "Recto", "Obtuso"], "c": 1},
    {"p": "¿qué científico formuló la ley de la gravitación universal?", "o": ["Albert Einstein", "Isaac Newton", "Galileo Galilei"], "c": 1}
]

# --- FUNCIONES AUXILIARES ---
def get_thread_id(message):
    return message.message_thread_id if message.is_topic_message else None

def normalizar_texto(texto):
    if not texto: return ""
    rem = (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"))
    s = texto.lower().strip()
    for a, b in rem:
        s = s.replace(a, b)
    return s

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

@bot.message_handler(commands=['beg'])
def suplicar_robux(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)
    user_id = message.from_user.id
    first_name = message.from_user.first_name

    mencion_nickname = f'<a href="tg://user?id={user_id}">{first_name}</a>'

    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        target_mencion = f'<a href="tg://user?id={target_user.id}">{target_user.first_name}</a>'
        texto = f"ㅤ૮  .ܸ  .ܸ ྀི ა  ㅤ{mencion_nickname} le está suplicando a {target_mencion} por robux...ㅤ"
    else:
        texto = f"ㅤ૮  .ܸ  .ܸ ྀི ა  ㅤ{mencion_nickname} suplica por robux...ㅤ"

    bot.send_message(chat_id, texto, parse_mode="HTML", message_thread_id=thread_id, reply_to_message_id=message.message_id)

    if STICKERS_CHERRIE:
        try:
            bot.send_sticker(chat_id, random.choice(STICKERS_CHERRIE), message_thread_id=thread_id)
        except Exception:
            pass

# --- QUIZ DE BATALLA ESTÉTICO ---
def generar_texto_lobby():
    premio = quiz_juego["premio"]
    part_str = "\n".join([f"✦    @{user}" for user in quiz_juego["participantes"].values()])
    if not part_str:
        part_str = "✦    *(Aún no hay participantes)*"

    return (
        f"ㅤ ꯳⃘꤫ ㅤㅤ¡hora del Quiz de Batalla!\n"
        f"—  únete a la batalla para demostrar tus conocimientos y llevarte {premio}.\n\n"
        f"participantes:\n{part_str}\n\n"
        f"— para iniciar ; /quizstart."
    )

@bot.message_handler(commands=['quiz'])
def iniciar_lobby_quiz(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)

    if quiz_juego["fase"] != "inactivo":
        bot.send_message(chat_id, " (╥﹏╥)  ya hay una partida activa.", message_thread_id=thread_id)
        return

    partes = message.text.split(maxsplit=1)
    if len(partes) < 2:
        bot.send_message(chat_id, " (╥﹏╥)  ¡recuerda! debes especificar el premio. Ejemplo: /quiz 5 robux", message_thread_id=thread_id)
        return

    quiz_juego["fase"] = "lobby"
    quiz_juego["chat_id"] = chat_id
    quiz_juego["thread_id"] = thread_id
    quiz_juego["premio"] = partes[1]
    quiz_juego["participantes"] = {}
    quiz_juego["sobrevivientes"] = {}
    quiz_juego["ronda"] = 0
    quiz_juego["preguntas_usadas"] = []

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_quiz"))

    msg = bot.send_message(chat_id, generar_texto_lobby(), reply_markup=markup, message_thread_id=thread_id)
    quiz_juego["msg_lobby_id"] = msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "unirse_quiz")
def unirse_quiz_callback(call):
    if quiz_juego["fase"] != "lobby":
        bot.answer_callback_query(call.id, "El lobby ya está cerrado.", show_alert=True)
        return

    user_id = call.from_user.id
    username = call.from_user.username or call.from_user.first_name

    if user_id in quiz_juego["participantes"]:
        bot.answer_callback_query(call.id, "Ya estás participando.", show_alert=True)
        return

    quiz_juego["participantes"][user_id] = username
    bot.answer_callback_query(call.id, "¡Te has unido!")

    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_quiz"))
        bot.edit_message_text(generar_texto_lobby(), quiz_juego["chat_id"], quiz_juego["msg_lobby_id"], reply_markup=markup)
    except Exception:
        pass

@bot.message_handler(commands=['quizstart'])
def comenzar_quiz_batalla(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)

    if quiz_juego["fase"] != "lobby":
        bot.send_message(chat_id, " (╥﹏╥)  no hay ningún lobby abierto.", message_thread_id=thread_id)
        return

    if len(quiz_juego["participantes"]) < 1:
        bot.send_message(chat_id, " (╥﹏╥)  se necesita al menos 1 participante.", message_thread_id=thread_id)
        return

    quiz_juego["fase"] = "jugando"
    quiz_juego["sobrevivientes"] = dict(quiz_juego["participantes"])

    bot.send_message(chat_id, "ㅤ ꯳⃘꤫ ㅤ ¡Lobby cerrado! La batalla del Quiz comienza ahora...", message_thread_id=thread_id)

    hilo_juego = threading.Thread(target=bucle_quiz_batalla, daemon=True)
    hilo_juego.start()

def bucle_quiz_batalla():
    chat_id = quiz_juego["chat_id"]
    thread_id = quiz_juego["thread_id"]

    while quiz_juego["fase"] == "jugando" and len(quiz_juego["sobrevivientes"]) > 1:
        quiz_juego["ronda"] += 1
        
        # Reducción progresiva de tiempo: 18s, 16s, 14s, 12s, mínimo 10s
        tiempo_ronda = max(10, 18 - (quiz_juego["ronda"] - 1) * 2)

        disponibles = [q for q in BANCO_PREGUNTAS if q["p"] not in quiz_juego["preguntas_usadas"]]
        if not disponibles:
            quiz_juego["preguntas_usadas"] = []
            disponibles = BANCO_PREGUNTAS

        pregunta = random.choice(disponibles)
        quiz_juego["preguntas_usadas"].append(pregunta["p"])
        quiz_juego["pregunta_actual"] = pregunta
        quiz_juego["respondieron_correcto"].clear()

        cant_sob = len(quiz_juego["sobrevivientes"])
        
        # Formatear primera letra en mayúscula para la pregunta
        p_texto = pregunta['p']
        p_formateada = p_texto[0].upper() + p_texto[1:] if p_texto else p_texto

        texto_pregunta = (
            f"ㅤㅤㅤㅤㅤ୭ৎ ࣪ ׅ ㅤRonda {quiz_juego['ronda']}ㅤ (Sobrevivientes: {cant_sob})\n\n"
            f"𓂃   Pregunta: {p_formateada} ¡Tienen {tiempo_ronda} segundos para responder!"
        )

        bot.send_message(chat_id, texto_pregunta, message_thread_id=thread_id)
        time.sleep(tiempo_ronda)

        if quiz_juego["fase"] != "jugando":
            return

        correctos = set(quiz_juego["respondieron_correcto"])
        respuesta_correcta_str = pregunta["o"][pregunta["c"]]

        if len(correctos) > 0:
            eliminados = [u for uid, u in quiz_juego["sobrevivientes"].items() if uid not in correctos]
            quiz_juego["sobrevivientes"] = {uid: u for uid, u in quiz_juego["sobrevivientes"].items() if uid in correctos}
        else:
            eliminados = []

        str_eliminados = ", ".join([f"@{u}" for u in eliminados]) if eliminados else "Nadie"
        cant_vivos = len(quiz_juego["sobrevivientes"])

        resumen = (
            f"(๑>ᴗ<๑)  ¡tiempo agotado!\n\n"
            f"𓂃   La respuesta correcta era  :  {respuesta_correcta_str}\n\n"
            f"𓂃   Eliminados de la ronda  :  {str_eliminados}\n"
            f"𓂃   Sobrevivientes  :  {cant_vivos}\n"
            f"✦⠀¡Siguiente ronda en 5 segundos! Prepárense... ૮₍ ˶•⤙•˶ ₎ა"
        )

        bot.send_message(chat_id, resumen, message_thread_id=thread_id)
        time.sleep(5)

    if quiz_juego["fase"] == "jugando":
        if len(quiz_juego["sobrevivientes"]) == 1:
            ganador = list(quiz_juego["sobrevivientes"].values())[0]
            texto_fin = (
                f"ㅤㅤㅤㅤㅤ୭ৎ ࣪ ׅ ㅤ¡FIN DEL QUIZ!ㅤ\n\n"
                f"ㅤㅤㅤᡣ𐭩ㅤ¡felicidades @{ganador}! fuiste el único sobreviviente y ganaste {quiz_juego['premio']} ♡."
            )
            bot.send_message(chat_id, texto_fin, message_thread_id=thread_id)
        else:
            bot.send_message(chat_id, " (╥﹏╥)  el quiz terminó sin sobrevivientes.", message_thread_id=thread_id)

    quiz_juego["fase"] = "inactivo"

@bot.message_handler(func=lambda msg: quiz_juego["fase"] == "jugando")
def verificar_respuesta_chat(message):
    user_id = message.from_user.id
    if user_id in quiz_juego["sobrevivientes"]:
        pregunta = quiz_juego["pregunta_actual"]
        if pregunta:
            correcta = normalizar_texto(pregunta["o"][pregunta["c"]])
            intento = normalizar_texto(message.text)
            if intento == correcta:
                quiz_juego["respondieron_correcto"].add(user_id)

@bot.message_handler(commands=['endquiz'])
def finalizar_quiz_manual(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes finalizar el quiz.", message_thread_id=thread_id)
        return

    if quiz_juego["fase"] == "inactivo":
        bot.send_message(chat_id, " (╥﹏╥)  no hay ningún quiz activo.", message_thread_id=thread_id)
        return

    quiz_juego["fase"] = "inactivo"
    bot.send_message(chat_id, "(๑´`๑)  ¡El Quiz de Batalla ha sido finalizado manualmente por el administrador!", message_thread_id=thread_id)

# --- SISTEMA DE SORTEOS ---
def generar_texto_sorteo(premio, minutos_restantes=0, ganadores=1):
    return (
        "ㅤㅤㅤㅤㅤ୭ৎ ࣪ ׅ ㅤ¡Nuevo sorteo!ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ                 \n"
        f"𓂃   premio  :  {premio}\n"
        f"𓂃   tiempo restante  :  {minutos_restantes} minutos\n"
        f"𓂃   ganador/es  :  {ganadores} ganador/es\n\n"
        "ㅤᡣ𐭩ㅤpresiona el botón para unirte."
    )

def generar_texto_resultados(premio, ganador_str, admin_user="kirschteiinz"):
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
        if unidad == 'h': segundos = cantidad_tiempo * 3600
        elif unidad == 'd': segundos = cantidad_tiempo * 86400

        return premio, segundos, num_ganadores
    else:
        return args, 0, 1

@bot.message_handler(commands=['sorteo'])
def crear_sorteo(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar un sorteo.", message_thread_id=thread_id)
        return

    premio, segundos_duracion, num_ganadores = parsear_comando_sorteo(message.text)

    if not premio:
        bot.send_message(chat_id, "⌗  ¡recuerda! debes especificar el premio. Ejemplo: /sorteo 15 robux 15m 1", message_thread_id=thread_id)
        return

    tiempo_finalizacion = time.time() + segundos_duracion if segundos_duracion > 0 else None
    minutos_iniciales = max(1, segundos_duracion // 60) if segundos_duracion > 0 else 0

    sorteos[chat_id] = {
        "premio": premio, "participantes": set(), "mensaje_id": None,
        "ganadores_anteriores": [], "thread_id": thread_id,
        "num_ganadores": num_ganadores, "tiempo_fin": tiempo_finalizacion, "activo": True
    }

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_sorteo"))

    msg = bot.send_message(chat_id, generar_texto_sorteo(premio, minutos_iniciales, num_ganadores), reply_markup=markup, message_thread_id=thread_id)
    sorteos[chat_id]["mensaje_id"] = msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "unirse_sorteo")
def unirse_sorteo_callback(call):
    chat_id = call.message.chat.id
    username = call.from_user.username or call.from_user.first_name
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
        bot.send_message(chat_id, f"✦⠀¡nuevo participante! @{username}, mucha suerte :3", message_thread_id=thread_id)
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
    bot.send_message(chat_id, generar_texto_resultados(datos["premio"], str_ganadores), message_thread_id=thread_id)

@bot.message_handler(commands=['endsorteo'])
def finalizar_sorteo(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes finalizar el sorteo.", message_thread_id=thread_id)
        return

    if chat_id not in sorteos or not sorteos[chat_id]["activo"]:
        bot.send_message(chat_id, " (╥﹏╥)  no hay ningún sorteo activo en este chat.", message_thread_id=thread_id)
        return

    ejecutar_fin_sorteo(chat_id)

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
                            bot.edit_message_text(generar_texto_sorteo(datos["premio"], min_restantes, datos["num_ganadores"]), chat_id, datos["mensaje_id"], reply_markup=markup)
                        except Exception:
                            pass
        except Exception as e:
            print(f"Error en monitor de sorteos: {e}")
        time.sleep(30)

hilo_monitor = threading.Thread(target=monitor_sorteos, daemon=True)
hilo_monitor.start()

# --- EJECUCIÓN CONTINUA ---
if __name__ == '__main__':
    bot.infinity_polling()
