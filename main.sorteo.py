import telebot
from telebot import types
import random
import threading
import time
import re
import os

TOKEN = os.environ["TOKEN"]
bot = telebot.TeleBot(TOKEN)

# --- CONFIGURACIÓN Y PERSISTENCIA DE PERMISOS GLOBAL ---
ADMINS_FILE = "admins.txt"
ADMINS_PERMITIDOS = set()
SUPER_ADMIN = "kirschteiinz"  # Usuario de telegram autorizado sin @

def cargar_admins():
    """Carga los IDs de administradores guardados de forma permanente."""
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line.isdigit():
                    ADMINS_PERMITIDOS.add(int(line))

def guardar_admins():
    """Guarda de forma permanente la lista actual de administradores."""
    with open(ADMINS_FILE, "w") as f:
        for admin_id in ADMINS_PERMITIDOS:
            f.write(f"{admin_id}\n")

# Cargar admins al iniciar la aplicación
cargar_admins()

def es_admin(chat_id, user_id):
    return user_id in ADMINS_PERMITIDOS

# --- PACK DE STICKERS DE CHERRIEBOT ---
STICKERS_CHERRIE = [
    "CAACAgEAAxkBAANHaoVbwH1bR16BovjZpvbzdmYAAcv5AAJKCAACh1YpROPnWzoUB7hkPQQ",
    "CAACAgEAAxkBAANJaoVbxFwCt6v7Dc4Bq5MBVviJkq0AAkIGAAKaKilEw6n5UhHxucY9BA",
    "CAACAgEAAxkBAANLaoVbxu0C4Pf13Q4h4--008tHtA0AAjwHAALY5ShExZIILPgB8XU9BA",
    "CAACAgEAAxkBAANNaoVbx0HIrfh3HaoEnRnq2TiF2FYAAgoHAAJDLjFED9e__RIuw0g9BA",
    "CAACAgEAAxkBAANPaoVbyYS2PuWDTuGSdGdWwcA7onQAAp8IAALviDFErpsOg5jJa4g9BA",
    "CAACAgEAAxkBAANRaoVby-CNkO8cMAw7x6E2yUThMaoAAtkGAALl9SlEbGxRRm1A0vM9BA"
]

STICKER_RED = "CAACAgEAAxkBAAMEaoniIkZBty-fZAaO2qRWlnmSLz8AArEKAAKZBFFE4Fo8s2EZTbU9BA"
STICKER_PINK = "CAACAgEAAxkBAAMCaoniHkzsWaDk9R6Omme6uuj8vUAAAgkLAAK8SFBEsHO2EgaHmJs9BA"

# --- ESTADOS GLOBALES Y REGISTROS ---
sorteos = {}
puntos_sistema = {}          # {username: puntos_int}
quiz_aciertos = {}           # {username: total_aciertos_int}
mineria_historico = {}       # {username: puntos_acumulados_int}
victorias_historico = {}     # {username: total_victorias_int}
usuarios_ids = {}            # {username: user_id} para poder enviar PM

def registrar_victoria(username):
    victorias_historico[username] = victorias_historico.get(username, 0) + 1

quiz_juego = {
    "fase": "inactivo",
    "chat_id": None,
    "thread_id": None,
    "admin_id": None,
    "premio": "",
    "participantes": set(),
    "participantes_activos": set(),
    "pregunta_actual": None,
    "opcion_correcta": None,
    "respuestas": {},
    "msg_lobby_id": None,
    "msg_pregunta_id": None,
    "dificultad": 1,
    "preguntas_usadas": []
}

mineria_juego = {
    "fase": "inactivo",
    "chat_id": None,
    "thread_id": None,
    "admin_id": None,
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
    "admin_id": None,
    "premio": "",
    "tickets_vendidos": {},
    "usuarios_registrados": set(),
    "ticket_ganador": None,
    "ganador_esperado": None,
    "tiempo_limite": 0,
    "reclamado": False,
    "msg_lobby_id": None # Añadido para consistencia
}

redpink_juego = {
    "fase": "inactivo",
    "chat_id": None,
    "thread_id": None,
    "admin_id": None,
    "premio": "",
    "participantes": set(),
    "elecciones": {},
    "msg_lobby_id": None,
    "msg_apuestas_id": None # Para editar/eliminar después
}

carrera_juego = {
    "fase": "inactivo",
    "chat_id": None,
    "thread_id": None,
    "admin_id": None,
    "premio": "",
    "participantes": [],
    "emojis_asignados": {},
    "posiciones": {},
    "pistas": [],
    "msg_carrera_id": None,
    "msg_lobby_id": None
}

cherrybomb_juego = {
    "fase": "inactivo",
    "modo": None,
    "chat_id": None,
    "thread_id": None,
    "admin_id": None,
    "premio": "",
    "participantes": [],
    "participantes_activos": [],
    "tablero": {},
    "podridas_monto": {},
    "turno_index": 0,
    "elecciones_privadas": {},
    "msg_tablero_id": None,
    "msg_lobby_id": None,
    "timer_eat": None
}

EMOJIS_CARRERA = ["🍒", "🍓", "🍉", "🍊", "🍍", "🍋‍🟩", "🍏", "🫐", "🍇", "🍐", "🥭", "🍌", "🥝", "🍑"]

def get_thread_id(message):
    return message.message_thread_id if message.is_topic_message else None

# --- GESTIÓN DE ADMINS POR ID ---
@bot.message_handler(commands=['admin'])
def agregar_admin_por_id(message):
    username = message.from_user.username
    if not username or username.lower() != SUPER_ADMIN.lower():
        return

    args = message.text.split()
    if len(args) < 2:
        bot.send_message(message.chat.id, "✦ Estructura incorrecta. Uso: /admin + [ID_del_usuario]")
        return

    try:
        user_id_add = int(args[1].replace('+', '').strip())
        ADMINS_PERMITIDOS.add(user_id_add)
        guardar_admins()
        bot.send_message(message.chat.id, f"ㅤ♡ㅤ¡Usuario {user_id_add} agregado a la lista de admins autorizados!")
    except ValueError:
        bot.send_message(message.chat.id, "✦ ID no válida. Asegúrate de colocar un ID numérico entero.")

@bot.message_handler(commands=['unadmin'])
def quitar_admin_por_id(message):
    username = message.from_user.username
    if not username or username.lower() != SUPER_ADMIN.lower():
        return

    args = message.text.split()
    if len(args) < 2:
        bot.send_message(message.chat.id, "✦ Estructura incorrecta. Uso: /unadmin + [ID_del_usuario]")
        return

    try:
        user_id_remove = int(args[1].replace('+', '').strip())
        if user_id_remove in ADMINS_PERMITIDOS:
            ADMINS_PERMITIDOS.remove(user_id_remove)
            guardar_admins()
            bot.send_message(message.chat.id, f"✦ El usuario {user_id_remove} ha sido removido de la lista de administradores.")
        else:
            bot.send_message(message.chat.id, f" (╥﹏╥)  El usuario {user_id_remove} no se encuentra en la lista de admins.")
    except ValueError:
        bot.send_message(message.chat.id, "✦ ID no válida. Asegúrate de colocar un ID numérico entero.")

@bot.message_handler(commands=['admins'])
def listar_administradores(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin autorizado, no puedes usar este comando.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if not ADMINS_PERMITIDOS:
        bot.send_message(chat_id, " (╥﹏╥)  no hay administradores registrados actualmente.", message_thread_id=thread_id)
        return

    lineas = []
    for uid in list(ADMINS_PERMITIDOS):
        try:
            user_chat = bot.get_chat(uid)
            u_name = f"@{user_chat.username}" if user_chat.username else user_chat.first_name
        except Exception:
            u_name = "Desconocido"
        lineas.append(f"✦ ID: `{uid}` — {u_name}")

    texto = "      ‿︵       𝘈𝘥𝘮𝘪𝘯𝘪𝘴𝘵𝘳𝘢𝘥𝘰𝘳𝘦𝘴 𝘈𝘶𝘵𝘰𝘳𝘪𝘻𝘢𝘥𝘰𝘴 !\n\n" + "\n".join(lineas)
    bot.send_message(chat_id, texto, parse_mode="Markdown", message_thread_id=thread_id)

# --- COMANDOS BÁSICOS Y LISTA GENERAL ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    username = message.from_user.username if message.from_user.username else message.from_user.first_name
    usuarios_ids[username] = message.from_user.id
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

@bot.message_handler(commands=['comandos'])
def mostrar_comandos(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if message.chat.type != 'private' and not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin autorizado, no puedes usar este comando.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    texto = (
        "  丙        ◟     Lista de Comandos.           𝆬          \n\n"
        "✦ /sorteo [premio] [tiempo] [ganadores] 𓂃 Inicia un nuevo sorteo.\n"
        "✦ /endsorteo 𓂃 Finaliza el sorteo activo inmediatamente.\n"
        "✦ /resorteo 𓂃 Elige un nuevo ganador del sorteo actual.\n"
        "✦ /quiz [premio] 𓂃 Abre el lobby para la batalla de preguntas.\n"
        "✦ /quizstart 𓂃 Empieza las rondas del quiz activo.\n"
        "✦ /quizlegends 𓂃 Muestra el top de personas con más aciertos.\n"
        "✦ /cherrybomb [modo] [premio] 𓂃 Inicia Cherry Bomb (admin/players).\n"
        "✦ /cherrybombstart 𓂃 Inicia la partida de Cherry Bomb.\n"
        "✦ /eat [número] 𓂃 Elige una cereza en tu turno de Cherry Bomb.\n"
        "✦ /mineria [premio] 𓂃 Abre el lobby para el juego de minería.\n"
        "✦ /mineriastart 𓂃 Inicia las rondas de minería.\n"
        "✦ /minar 𓂃 Realiza una acción de minería en tu turno.\n"
        "✦ /bestminers 𓂃 Muestra el top de puntos de minería.\n"
        "✦ /endmineria 𓂃 Finaliza la minería manualmente.\n"
        "✦ /loteria [premio] 𓂃 Inicia la compra de tickets de lotería.\n"
        "✦ /tickets 𓂃 Recibe 5 tickets para la lotería.\n"
        "✦ /jugarloteria 𓂃 Realiza el sorteo de la lotería.\n"
        "✦ /redpink [premio] 𓂃 Abre la partida de Red or Pink.\n"
        "✦ /redpinkstart 𓂃 Inicia las apuestas del Red or Pink.\n"
        "✦ /redpinknow 𓂃 Cierra las apuestas, sortea apuestas faltantes y revela el resultado.\n"
        "✦ /carrera [premio] 𓂃 Abre la carrera anónima.\n"
        "✦ /carrerastart 𓂃 Da inicio a la carrera.\n"
        "✦ /wins 𓂃 Muestra las victorias acumuladas de todos los usuarios.\n"
        "✦ /admins 𓂃 Muestra la lista de administradores autorizados.\n"
        "✦ /unadmin [ID] 𓂃 Remueve el privilegio de admin a una ID.\n"
        "✦ /add @usuario [monto] 𓂃 Añade puntos a la cartilla.\n"
        "✦ /rest @usuario [monto] 𓂃 Resta puntos a un usuario.\n"
        "✦ /check 𓂃 Muestra la cartilla de puntos.\n"
        "✦ /clear 𓂃 Reinicia la cartilla de puntos.\n"
        "✦ /cancelar 𓂃 Cancela cualquier juego o sorteo activo.\n"
        "✦ /beg 𓂃 Suplica por robux con animación."
    )
    bot.send_message(chat_id, texto, message_thread_id=thread_id)

@bot.message_handler(commands=['wins'])
def mostrar_victorias(message):
    thread_id = get_thread_id(message)
    if not victorias_historico:
        bot.send_message(message.chat.id, " (╥﹏╥)  aún no hay registros de victorias.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    ordenados = sorted(victorias_historico.items(), key=lambda x: x[1], reverse=True)
    lineas = [f"@{u} — {v:02d} victorias" for u, v in ordenados]
    texto = "      ‿︵       𝘝𝘪𝘤𝘵𝘰𝘳𝘪𝘢𝘴 𝘎𝘭𝘰𝘣𝘢𝘭𝘦𝘴 !\n\n" + "\n".join(lineas)
    bot.send_message(message.chat.id, texto, message_thread_id=thread_id)

# --- GESTIÓN DE CARTILLA DE PUNTOS ---
@bot.message_handler(commands=['add'])
def agregar_puntos(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes añadir puntos.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    args = message.text.split()
    if len(args) < 3:
        bot.send_message(chat_id, "✦ Estructura incorrecta: /add @usuario [monto]", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    usuario = args[1].replace('@', '')
    try:
        monto = int(args[2])
    except ValueError:
        bot.send_message(chat_id, " (╥﹏╥)  el monto debe ser un número entero.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    puntos_sistema[usuario] = puntos_sistema.get(usuario, 0) + monto
    bot.send_message(chat_id, f"✦  ¡se le añadieron {monto} puntos a @{usuario}! ♡", message_thread_id=thread_id)

@bot.message_handler(commands=['rest'])
def restar_puntos(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes restar puntos.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    args = message.text.split()
    if len(args) < 3:
        bot.send_message(chat_id, "✦ Estructura incorrecta: /rest @usuario [monto]", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    usuario = args[1].replace('@', '')
    try:
        monto = int(args[2])
    except ValueError:
        bot.send_message(chat_id, " (╥﹏╥)  el monto debe ser un número entero.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    puntos_sistema[usuario] = max(0, puntos_sistema.get(usuario, 0) - monto)
    bot.send_message(chat_id, f"✦ Se restaron {monto} puntos a @{usuario}. Total: {puntos_sistema[usuario]} pts.", message_thread_id=thread_id)

@bot.message_handler(commands=['check'])
def ver_puntos(message):
    thread_id = get_thread_id(message)
    if not puntos_sistema:
        bot.send_message(message.chat.id, " (╥﹏╥)  la cartilla de puntos está vacía.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    ordenados = sorted(puntos_sistema.items(), key=lambda x: x[1], reverse=True)
    lineas = [f"{idx:02d}  ;  @{u} ({pts} pts)" for idx, (u, pts) in enumerate(ordenados, start=1)]
    total_pts = sum(puntos_sistema.values())
    
    texto = "丙        ◟     point list.           𝆬          \n\n" + "\n".join(lineas) + f"\n\n   ୨୧        𝅄     total   ;    {total_pts} pts"
    bot.send_message(message.chat.id, texto, message_thread_id=thread_id)

@bot.message_handler(commands=['clear'])
def reiniciar_puntos(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes reiniciar la cartilla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    puntos_sistema.clear()
    bot.send_message(chat_id, "✦ ¡La cartilla de puntos ha sido reiniciada con éxito!", message_thread_id=thread_id)

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
        texto = f"ㅤ૮  .ܸ  .ܸ ྀི ა  ㅤ{mencion_nickname} está suplicando a {target_mencion} por robux...ㅤ"
    else:
        texto = f"ㅤ૮  .ܸ  .ܸ ྀི ა  ㅤ{mencion_nickname} está suplicando por robux...ㅤ"

    time.sleep(3)
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
        except Exception:
            pass

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

    if redpink_juego["fase"] != "inactivo":
        if redpink_juego["admin_id"] != user_id:
            bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla o cancelarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
            return
        redpink_juego["fase"] = "inactivo"
        juego_cancelado = "red or pink"

    if carrera_juego["fase"] != "inactivo":
        if carrera_juego["admin_id"] != user_id:
            bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla o cancelarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
            return
        carrera_juego["fase"] = "inactivo"
        juego_cancelado = "carrera anónima"

    if cherrybomb_juego["fase"] != "inactivo":
        if cherrybomb_juego["admin_id"] != user_id:
            bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla o cancelarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
            return
        cherrybomb_juego["fase"] = "inactivo"
        juego_cancelado = "cherry bomb"

    if juego_cancelado:
        texto = f"ㅤ ୨୧ ࣪ ׅ ㅤla partida de {juego_cancelado} fue cancelada por su admin. ૮ ˶• ˔ •˶ ა"
        bot.send_message(chat_id, texto, message_thread_id=thread_id)
    else:
        bot.send_message(chat_id, " (╥﹏╥)  no hay ninguna partida activa para cancelar.", message_thread_id=thread_id, reply_to_message_id=message.message_id)

# --- SORTEOS ---
def generar_texto_sorteo(premio, minutos_restantes=0, ganadores=1):
    return (
        "ㅤㅤㅤ୭ৎ ࣪ ׅ ㅤㅤ ¡Nuevo sorteo!ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ\n\n"
        f"𓂃   premio  :  {premio}\n"
        f"𓂃   tiempo restante  :  {minutos_restantes}m\n"
        f"𓂃   ganador/es  :  {ganadores}\n\n"
        "ㅤᡣ𐭩ㅤㅤpresiona el botón para unirte."
    )

def generar_texto_resultados(premio, ganador_str, admin_user):
    return (
        "ㅤㅤㅤㅤㅤ୭ৎ ࣪ ׅ ㅤ¡Resultados!ㅤ\n\n"
        f"𓂃   premio  :  {premio}\n"
        f"𓂃   ganador/es  :  {ganador_str}\n\n"
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
        bot.send_message(chat_id, "✦ Estructura incorrecta. Ejemplo: /sorteo 15 robux 20m 1", message_thread_id=thread_id, reply_to_message_id=message.message_id)
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

    time.sleep(3)
    texto_inicial = generar_texto_sorteo(premio, minutos_restantes=minutos_iniciales, ganadores=num_ganadores)
    msg = bot.send_message(chat_id, texto_inicial, reply_markup=markup, message_thread_id=thread_id)
    sorteos[chat_id]["mensaje_id"] = msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "unirse_sorteo")
def unirse_sorteo_callback(call):
    chat_id = call.message.chat.id
    username = call.from_user.username if call.from_user.username else call.from_user.first_name
    usuarios_ids[username] = call.from_user.id
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

    for g in ganadores:
        registrar_victoria(g)

    str_ganadores = ", ".join([f"@{g}" for g in ganadores])
    texto_ganador = generar_texto_resultados(datos["premio"], str_ganadores, datos["admin_username"])
    time.sleep(3)
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

