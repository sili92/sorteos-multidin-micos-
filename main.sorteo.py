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
puntos_sistema = {}          # {username: puntos_int}
quiz_aciertos = {}           # {username: total_aciertos_int}

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
        f"🌸 Sticker capturado\n\nPack: {pack_name}\nFile ID:\n{file_id}", 
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

    # Mención por nickname (first_name) vinculada en HTML
    mencion_nickname = f'<a href="tg://user?id={user_id}">{first_name}</a>'

    # Verificar si el comando se usó en respuesta a un mensaje de otra persona
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        target_id = target_user.id
        target_name = target_user.first_name
        target_mencion = f'<a href="tg://user?id={target_id}">{target_name}</a>'
        texto = f"ㅤ૮  .ܸ  .ܸ ྀི ა  ㅤ{mencion_nickname} le está suplicando a {target_mencion} por robux...ㅤ"
    else:
        # Si no se responde a nadie, solo muestra al usuario que usó el comando
        texto = f"ㅤ૮  .ܸ  .ܸ ྀི ა  ㅤ{mencion_nickname} suplica por robux...ㅤ"

    # 1. Envío del mensaje formateado en HTML
    bot.send_message(
        chat_id, 
        texto, 
        parse_mode="HTML", 
        message_thread_id=thread_id, 
        reply_to_message_id=message.message_id
    )

    # 2. Envío de sticker aleatorio del pack
    if STICKERS_CHERRIE:
        sticker_elegido = random.choice(STICKERS_CHERRIE)
        try:
            bot.send_sticker(chat_id, sticker_elegido, message_thread_id=thread_id)
        except Exception as e:
            print(f"Error enviando sticker: {e}")

# --- COMANDO /CANCELAR (GLOBAL) ---
@bot.message_handler(commands=['cancelar'])
def cancelar_juego_activo(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    thread_id = get_thread_id(message)

    try:
        if bot.get_chat_member(chat_id, user_id).status not in ['administrator', 'creator']:
            bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes cancelar partidas.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
            return
    except Exception:
        pass

    juego_cancelado = None

    if chat_id in sorteos and sorteos[chat_id]["activo"]:
        sorteos[chat_id]["activo"] = False
        juego_cancelado = "sorteo"

    if quiz_juego["fase"] != "inactivo":
        quiz_juego["fase"] = "inactivo"
        juego_cancelado = "quiz de batalla"

    if mineria_juego["fase"] != "inactivo":
        mineria_juego["fase"] = "inactivo"
        juego_cancelado = "minería"

    if loteria_juego["fase"] != "inactivo":
        loteria_juego["fase"] = "inactivo"
        juego_cancelado = "lotería"

    if juego_cancelado:
        texto = f"ㅤ ୨୧ ࣪ ׅ ㅤla partida de {juego_cancelado} fue cancelada por un admin. ૮₍ ˶•⤙•˶ ₎ა"
        bot.send_message(chat_id, texto, message_thread_id=thread_id)
    else:
        bot.send_message(chat_id, " (╥﹏╥)  no hay ninguna partida activa para cancelar.", message_thread_id=thread_id, reply_to_message_id=message.message_id)

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
    try:
        if bot.get_chat_member(chat_id, user_id).status not in ['administrator', 'creator']:
            bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar un sorteo.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
            return
    except Exception:
        pass

    raw_text = message.text
    premio, segundos_duracion, num_ganadores = parsear_comando_sorteo(raw_text)

    if not premio:
        bot.send_message(chat_id, "⌗  ¡recuerda! debes especificar el premio. Ejemplo: /sorteo 15 robux 15m 1", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    tiempo_finalizacion = time.time() + segundos_duracion if segundos_duracion > 0 else None
    minutos_iniciales = max(1, segundos_duracion // 60) if segundos_duracion > 0 else 0

    sorteos[chat_id] = {
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
    texto_ganador = generar_texto_resultados(datos["premio"], str_ganadores)
    bot.send_message(chat_id, texto_ganador, message_thread_id=thread_id)

@bot.message_handler(commands=['endsorteo'])
def finalizar_sorteo(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    try:
        if bot.get_chat_member(chat_id, user_id).status not in ['administrator', 'creator']:
            bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes finalizar el sorteo.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
            return
    except Exception:
        pass

    if chat_id not in sorteos or not sorteos[chat_id]["activo"]:
        bot.send_message(chat_id, " (╥﹏╥)  no hay ningún sorteo activo en este chat.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    ejecutar_fin_sorteo(chat_id)

@bot.message_handler(commands=['resorteo'])
def resortear(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    try:
        if bot.get_chat_member(chat_id, user_id).status not in ['administrator', 'creator']:
            bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes resortear.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
            return
    except Exception:
        pass

    if chat_id not in sorteos or not sorteos[chat_id]["participantes"]:
        bot.send_message(chat_id, " (╥﹏╥)  no hay un sorteo reciente con participantes para volver a sortear.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    datos = sorteos[chat_id]
    elegibles = [p for p in datos["participantes"] if p not in datos["ganadores_anteriores"]]
    
    if not elegibles:
        bot.send_message(chat_id, " (╥﹏╥)  no quedan más participantes disponibles para resortear.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    bot.send_message(chat_id, "(๑´`๑)  vaya... al admin no le agradó ese resultado. ¡se elegirán nuevos ganadores en breve!", message_thread_id=thread_id)
    time.sleep(2)

    nuevo_ganador = random.choice(elegibles)
    datos["ganadores_anteriores"].append(nuevo_ganador)

    texto_nuevo_ganador = generar_texto_resultados(datos["premio"], f"@{nuevo_ganador}")
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

# --- ARRANQUE ROBUSTO 24/7 EN RAILWAY ---
if __name__ == '__main__':
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"Error en polling (reiniciando): {e}")
            time.sleep(5)
