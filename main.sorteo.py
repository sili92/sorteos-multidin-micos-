
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
usuarios_ids = {}            # {username: user_id}

def registrar_victoria(username):
    victorias_historico[username] = victorias_historico.get(username, 0) + 1

quiz_juego = {
    "fase": "inactivo",
    "chat_id": None,
    "thread_id": None,
    "admin_id": None,
    "premio": "",
    "participantes": [],
    "participantes_activos": [],
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
    "tickets_vendidos": {},  # {ticket_str: username}
    "usuarios_registrados": set(),
    "ticket_ganador": None,
    "ganador_esperado": None,
    "tiempo_limite": 0,
    "reclamado": False
}

redpink_juego = {
    "fase": "inactivo",
    "chat_id": None,
    "thread_id": None,
    "admin_id": None,
    "premio": "",
    "participantes": set(),
    "elecciones": {},
    "msg_lobby_id": None
}

carrera_juego = {
    "fase": "inactivo",
    "chat_id": None,
    "thread_id": None,
    "admin_id": None,
    "premio": "",
    "participantes": [], # Lista ordenada de usernames según se unieron
    "emojis_asignados": {}, # {username: emoji}
    "posiciones": {}, # {username: int_pos (0 a 20)}
    "emojis_orden_pista": [], # Lista con el orden mezclado de los usernames en la pista
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
    "tablero_explosivas": [],
    "podridas_info": {},
    "cerezas_comidas": set(),
    "turno_index": 0,
    "elecciones_privadas": {},
    "msg_tablero_id": None,
    "msg_lobby_id": None,
    "timer_eat": None
}

EMOJIS_CARRERA = ["🍒", "🍓", "🍉", "🍊", "🍍", "🍋‍🟩", "🍏", "🫐", "🍇", "🍐", "🥭", "🍌", "🥝", "🍑"]

def get_thread_id(message):
    return message.message_thread_id if message.is_topic_message else None

# --- GESTIÓN DE ADMINS POR ID MULTIPLE ---

@bot.message_handler(commands=['admin'])
def agregar_admin_por_id(message):
    username = message.from_user.username
    if not username or username.lower() != SUPER_ADMIN.lower():
        return

    args = message.text.split()[1:]
    if not args:
        bot.send_message(message.chat.id, "✦ Estructura incorrecta. Uso: /admin ID1 ID2 ID3")
        return

    agregados = []
    for arg in args:
        arg_clean = arg.replace('+', '').strip()
        if arg_clean.isdigit():
            user_id_add = int(arg_clean)
            ADMINS_PERMITIDOS.add(user_id_add)
            agregados.append(str(user_id_add))

    if agregados:
        guardar_admins()
        bot.send_message(message.chat.id, f"ㅤ♡ㅤ¡Usuario(s) {', '.join(agregados)} agregado(s) a la lista de admins autorizados!")
    else:
        bot.send_message(message.chat.id, "✦ No se ingresó ningún ID válido numérico.")

@bot.message_handler(commands=['unadmin'])
def quitar_admin_por_id(message):
    username = message.from_user.username
    if not username or username.lower() != SUPER_ADMIN.lower():
        return

    args = message.text.split()[1:]
    if not args:
        bot.send_message(message.chat.id, "✦ Estructura incorrecta. Uso: /unadmin ID")
        return

    for arg in args:
        arg_clean = arg.replace('+', '').strip()
        if arg_clean.isdigit():
            user_id_remove = int(arg_clean)
            if user_id_remove in ADMINS_PERMITIDOS:
                ADMINS_PERMITIDOS.remove(user_id_remove)
                guardar_admins()
                bot.send_message(message.chat.id, f"✦ El usuario {user_id_remove} ha sido removido de la lista de administradores.")
            else:
                bot.send_message(message.chat.id, f" (╥﹏╥)  El usuario {user_id_remove} no se encuentra en la lista de admins.")

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

@bot.message_handler(commands=['games'])
def mostrar_games(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)
    
    texto = (
        "⠀⠀ ㅤㅤ    ೨   ⠀⠀  ℳy games... ◝\n\n"
        "ㅤ𖥻ㅤ/sorteo para iniciar un sorteo aleatorio. ₍ᐢ..ᐢ₎  \n"
        "ㅤ𖥻ㅤ/quiz para iniciar una partida de quiz. ₍ᐢ..ᐢ₎  \n"
        "ㅤ𖥻ㅤ/cherrybomb para iniciar una partida de cerezas explosivas. ₍ᐢ..ᐢ₎  \n"
        "ㅤ𖥻ㅤ/mineria para iniciar una partida de mineria. ₍ᐢ..ᐢ₎  \n"
        "ㅤ𖥻ㅤ/loteria para iniciar el sorteo de lotería. ₍ᐢ..ᐢ₎  \n"
        "ㅤ𖥻ㅤ/redpink para iniciar una partida de red or pink. ₍ᐢ..ᐢ₎  \n"
        "ㅤ𖥻ㅤ/carrera para iniciar una carrera anónima. ₍ᐢ..ᐢ₎  \n\n"
        "ㅤㅤㅤᨳㅤ¡ℛecuerda! puedes usar /add y /rest para\n"
        "ㅤㅤㅤactualizar los puntos de un usuario, etiquetandolo."
    )
    bot.send_message(chat_id, texto, message_thread_id=thread_id)

@bot.message_handler(commands=['comandos'])
def mostrar_comandos(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if message.chat.type != 'private' and not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin autorizado, no puedes usar este comando.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    texto = (
        "  丙        ◟     Lista de Comandos.           𝆬          \n\n"
        "✦ /games 𓂃 Muestra el listado rápido de juegos.\n"
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
        "✦ /checkmineria 𓂃 Muestra el top global acumulado de minería.\n"
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

    puntos_sistema[usuario] = puntos_sistema.get(usuario, 0) - monto
    bot.send_message(chat_id, f"✦ Se restaron {monto} puntos a @{usuario}. Total: {puntos_sistema[usuario]} pts.", message_thread_id=thread_id)

@bot.message_handler(commands=['check'])
def ver_puntos(message):
    thread_id = get_thread_id(message)
    if not puntos_sistema:
        bot.send_message(message.chat.id, " (╥﹏╥)  la cartilla de puntos está vacía.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    ordenados = sorted(puntos_sistema.items(), key=lambda x: x[1], reverse=True)
    lineas = [f"{idx:02d}  ;  @{u} ({pts} pts)" for idx, (u, pts) in enumerate(ordenados, start=1)]
    total_pts = sum(pts for pts in puntos_sistema.values() if pts > 0)

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

# --- COMANDO /beg ---

@bot.message_handler(commands=['beg'])
def suplicar_robux(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)
    
    sender_name = message.from_user.first_name
    sender_id = message.from_user.id
    nickname1 = f"[{sender_name}](tg://user?id={sender_id})"

    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        target_name = target_user.first_name
        target_id = target_user.id
        nickname2 = f"[{target_name}](tg://user?id={target_id})"
        texto = f"ㅤ૮  .ܸ  .ܸ ྀི ა  ㅤ{nickname1} está suplicando a {nickname2} por robux...ㅤ"
    else:
        texto = f"ㅤ૮  .ܸ  .ܸ ྀི ა  ㅤ{nickname1} está suplicando por robux...ㅤ"

    bot.send_message(
        chat_id, 
        texto, 
        parse_mode="Markdown",
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

    bot.send_message(chat_id, "(๑´๑)  vaya... al admin no le agradó ese resultado. ¡se elegirán nuevos ganadores en breve!", message_thread_id=thread_id)
    time.sleep(3)

    nuevo_ganador = random.choice(elegibles)
    datos["ganadores_anteriores"].append(nuevo_ganador)
    registrar_victoria(nuevo_ganador)

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
                        min_restantes = max(0, int((datos["tiempo_fin"] - ahora) // 60))
                        try:
                            markup = types.InlineKeyboardMarkup()
                            markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_sorteo"))
                            nuevo_texto = generar_texto_sorteo(datos["premio"], minutos_restantes=min_restantes, ganadores=datos["num_ganadores"])
                            bot.edit_message_text(nuevo_texto, chat_id, datos["mensaje_id"], reply_markup=markup)
                        except Exception:
                            pass
        except Exception:
            pass
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

# --- SISTEMA DE QUIZ ---

def generar_texto_lobby_quiz():
    parts = "\n".join([f"        ⊹    @{p}" for p in quiz_juego["participantes"]]) if quiz_juego["participantes"] else "        ⊹    (esperando participantes...)"
    return (
        "ㅤㅤ ✿ㅤㅤ¡𝓝ueva partida de quiz!ㅤㅤㅤㅤㅤㅤㅤㅤ\n"
        "⠀ ᨭ⠀   prueba tus conocimientos jugando,\n"
        f"si eres el más listo, ¡puedes llevarte {quiz_juego['premio']}!\n\n"
        "  ⠀⎯ ⠀  𝗽︩︩︪articipantes     :\n"
        f"{parts}\n\n"
        "₍˄..˄₎꠹     presiona el botón para poder participar...\n"
        "admin, puedes colocar /quizstart para dar inicio a la partida."
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
        bot.send_message(chat_id, "✦ Estructura incorrecta. Ejemplo: /quiz VIP Mensual", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    quiz_juego["fase"] = "lobby"
    quiz_juego["chat_id"] = chat_id
    quiz_juego["thread_id"] = thread_id
    quiz_juego["admin_id"] = user_id
    quiz_juego["premio"] = premio
    quiz_juego["participantes"] = []
    quiz_juego["participantes_activos"] = []
    quiz_juego["dificultad"] = 1
    quiz_juego["preguntas_usadas"] = []

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_quiz_lobby"))

    time.sleep(1)
    msg = bot.send_message(chat_id, generar_texto_lobby_quiz(), reply_markup=markup, message_thread_id=thread_id)
    quiz_juego["msg_lobby_id"] = msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "unirse_quiz_lobby")
def unirse_quiz_callback(call):
    if quiz_juego["fase"] != "lobby":
        bot.answer_callback_query(call.id, "El lobby ya no está disponible.", show_alert=True)
        return

    username = call.from_user.username if call.from_user.username else call.from_user.first_name
    usuarios_ids[username] = call.from_user.id

    if username in quiz_juego["participantes"]:
        bot.answer_callback_query(call.id, "Ya estás en el lobby.", show_alert=True)
        return

    quiz_juego["participantes"].append(username)
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
    quiz_juego["participantes_activos"] = list(quiz_juego["participantes"])

    bot.send_message(chat_id, "ㅤꕮ⠀ㅤ¡𝑳obby cerrado!ㅤㅤㅤㅤㅤ\n    ⊹       iniciando la partida...", message_thread_id=thread_id)
    time.sleep(2)
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

    tiempo_limite = max(5, 15 - (quiz_juego["dificultad"] - 1))

    texto_pregunta = (
        f"ㅤㅤㅤ୭ৎ ࣪ ׅ ㅤℛonda {quiz_juego['dificultad']}ㅤ !\n"
        f"ㅤ𖥻ㅤ{pregunta_obj['p']}\n\n"
        f"ㅤ₍⑅ᐢ..ᐢ₎ㅤtienen {tiempo_limite} segundos para responder..."
    )

    markup = types.InlineKeyboardMarkup()
    for idx, opcion in enumerate(pregunta_obj["o"]):
        markup.add(types.InlineKeyboardButton(f"᭍᭭ {opcion}", callback_data=f"quiz_ans_{idx}"))

    msg = bot.send_message(chat_id, texto_pregunta, reply_markup=markup, message_thread_id=thread_id)
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
    usuarios_ids[username] = call.from_user.id

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
    eliminados_incorrecta = []
    eliminados_afk = []

    for p in list(quiz_juego["participantes_activos"]):
        if p in quiz_juego["respuestas"]:
            resp = quiz_juego["respuestas"][p]
            if resp["opcion"] == correcta_idx:
                acertaron.append((p, resp["tiempo"]))
                quiz_aciertos[p] = quiz_aciertos.get(p, 0) + 1
            else:
                eliminados_incorrecta.append(p)
        else:
            eliminados_afk.append(p)

    tenia_mas_de_dos = len(quiz_juego["participantes"]) > 2
    es_final_dos = len(quiz_juego["participantes_activos"]) == 2

    if tenia_mas_de_dos and es_final_dos and len(acertaron) == 2:
        acertaron.sort(key=lambda x: x[1])
        ganador_veloz = acertaron[0][0]
        mas_lento = acertaron[1][0]
        
        quiz_juego["participantes_activos"] = [ganador_veloz]
        texto_resumen = (
            "ㅤㅤㅤㅤ(๑>ᴗ<๑)  ¡tiempo agotado!\n\n"
            f"    ⊹       la respuesta correcta era  :  {texto_correcta}\n\n"
            f"๑  ¡todos acertaron! pero @{mas_lento}, al ser el último en responder, quedó descalificado."
        )
    else:
        sobrevivientes = [p for p, t in acertaron]
        quiz_juego["participantes_activos"] = sobrevivientes

        lineas_fallos = []
        for e in eliminados_incorrecta:
            lineas_fallos.append(f"๑  @{e} respuesta incorrecta...")
        for a in eliminados_afk:
            lineas_fallos.append(f"๑  @{a} demoró mucho...")

        str_fallos = "\n".join(lineas_fallos) if lineas_fallos else ""

        texto_resumen = (
            "ㅤㅤㅤㅤ(๑>ᴗ<๑)  ¡tiempo agotado!\n\n"
            f"    ⊹       la respuesta correcta era  :  {texto_correcta}\n"
        )
        if str_fallos:
            texto_resumen += f"\n{str_fallos}"

    time.sleep(1)
    bot.send_message(chat_id, texto_resumen, message_thread_id=thread_id)

    if len(quiz_juego["participantes_activos"]) <= 1:
        time.sleep(2)
        finalizar_juego_quiz(chat_id)
    else:
        quiz_juego["dificultad"] += 1
        time.sleep(3)
        lanzar_siguiente_pregunta(chat_id)

def finalizar_juego_quiz(chat_id):
    thread_id = quiz_juego["thread_id"]
    if len(quiz_juego["participantes_activos"]) == 1:
        ganador = quiz_juego["participantes_activos"][0]
        registrar_victoria(ganador)
        texto_final = (
            f"ㅤㅤ⸜(*ˊᗜˋ*)⸝ㅤㅤ¡felicidades @{ganador}! \n"
            f"has ganado la competencia y te llevas el premio: {quiz_juego['premio']} ♡."
        )
    else:
        texto_final = " (╥﹏╥)  el quiz ha finalizado sin ningún ganador."

    bot.send_message(chat_id, texto_final, message_thread_id=thread_id)
    quiz_juego["fase"] = "inactivo"

@bot.message_handler(commands=['quizlegends'])
def mostrar_quiz_legends(message):
    thread_id = get_thread_id(message)
    if not quiz_aciertos:
        bot.send_message(message.chat.id, " (╥﹏╥)  aún no hay estadísticas registradas de quiz.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    ordenados = sorted(quiz_aciertos.items(), key=lambda x: x[1], reverse=True)[:10]
    lineas = [f"{idx:02d}  ;  @{u} ({pts} respuestas correctas)" for idx, (u, pts) in enumerate(ordenados, start=1)]
    texto = "      ‿︵       𝘝𝘪𝘤𝘵𝘰𝘳𝘪𝘢𝘴 / 𝘘𝘶𝘪𝘻 𝘓𝘦𝘨𝘦𝘯𝘥𝘴 !\n\n" + "\n".join(lineas)
    bot.send_message(message.chat.id, texto, message_thread_id=thread_id)

# --- CHERRY BOMB ---

def generar_tablero_grid():
    grid = "⠀⠀  ⎯  ⠀⠀⠀𝕿‌ ablero de cherries. \n\n"
    for fila in range(5):
        linea = []
        for col in range(1, 6):
            num = fila * 5 + col
            if num in cherrybomb_juego["cerezas_comidas"]:
                linea.append("❌")
            else:
                linea.append(f"{num:2d}".strip())
        grid += "   ".join(linea) + "\n"
    return grid.strip()

@bot.message_handler(commands=['cherrybomb'])
def crear_cherrybomb(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar cherry bomb.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if cherrybomb_juego["fase"] != "inactivo":
        bot.send_message(chat_id, " (╥﹏╥)  ya hay una partida de cherry bomb en curso.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3 or args[1].lower() not in ["admin", "players"]:
        bot.send_message(chat_id, "✦ Estructura incorrecta. Ejemplo: /cherrybomb admin VIP 100", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    modo = args[1].lower()
    premio = args[2].strip()

    cherrybomb_juego["fase"] = "lobby"
    cherrybomb_juego["modo"] = modo
    cherrybomb_juego["chat_id"] = chat_id
    cherrybomb_juego["thread_id"] = thread_id
    cherrybomb_juego["admin_id"] = user_id
    cherrybomb_juego["premio"] = premio
    cherrybomb_juego["participantes"].clear()
    cherrybomb_juego["participantes_activos"].clear()
    cherrybomb_juego["elecciones_privadas"].clear()
    cherrybomb_juego["podridas_info"].clear()
    cherrybomb_juego["cerezas_comidas"].clear()

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_cherry_lobby"))

    texto_lobby = (
        "ㅤꔫ    ㅤ  𝕷‌obby de cherry bomb iniciado.  \n\n"
        "ㅤᨳㅤhay un tablero de dulces cerezas frente a tí, ¡sé cuidadoso al escoger una para comer! podría explotar inesperadamente, mucha suerte.\n\n"
        "  ⠀⎯ ⠀  𝗽︩︩︪articipantes     :\n"
        "        ⊹    @\n\n"
        "₍˄..˄₎꠹     presiona el botón para poder elegir tus cerecitas...\n"
        "admin, puedes colocar /cherrybombstart para dar inicio a la partida."
    )
    msg = bot.send_message(chat_id, texto_lobby, reply_markup=markup, message_thread_id=thread_id)
    cherrybomb_juego["msg_lobby_id"] = msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "unirse_cherry_lobby")
def unirse_cherry_callback(call):
    if cherrybomb_juego["fase"] != "lobby":
        bot.answer_callback_query(call.id, "El lobby ya no está disponible.", show_alert=True)
        return

    username = call.from_user.username if call.from_user.username else call.from_user.first_name
    usuarios_ids[username] = call.from_user.id

    if username in cherrybomb_juego["participantes"]:
        bot.answer_callback_query(call.id, "Ya estás en la partida.", show_alert=True)
        return

    cherrybomb_juego["participantes"].append(username)
    bot.answer_callback_query(call.id, "¡Te has unido a Cherry Bomb!")

    parts = "\n".join([f"        ⊹    @{p}" for p in cherrybomb_juego["participantes"]])
    texto_lobby = (
        "ㅤꔫ    ㅤ  𝕷‌obby de cherry bomb iniciado.  \n\n"
        "ㅤᨳㅤhay un tablero de dulces cerezas frente a tí, ¡sé cuidadoso al escoger una para comer! podría explotar inesperadamente, mucha suerte.\n\n"
        "  ⠀⎯ ⠀  𝗽︩︩︪articipantes     :\n"
        f"{parts}\n\n"
        "₍˄..˄₎꠹     presiona el botón para poder elegir tus cerecitas...\n"
        "admin, puedes colocar /cherrybombstart para dar inicio a la partida."
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_cherry_lobby"))
    try:
        bot.edit_message_text(texto_lobby, cherrybomb_juego["chat_id"], cherrybomb_juego["msg_lobby_id"], reply_markup=markup)
    except Exception:
        pass

@bot.message_handler(commands=['cherrybombstart'])
def iniciar_cherrybomb_start(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if cherrybomb_juego["fase"] != "lobby":
        bot.send_message(chat_id, " (╥﹏╥)  no hay ningún lobby activo de cherry bomb.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if cherrybomb_juego["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if not cherrybomb_juego["participantes"]:
        bot.send_message(chat_id, " (╥﹏╥)  se requieren participantes para iniciar.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    try:
        bot.edit_message_reply_markup(chat_id, cherrybomb_juego["msg_lobby_id"], reply_markup=None)
    except Exception:
        pass

    cherrybomb_juego["fase"] = "jugando"
    cherrybomb_juego["participantes_activos"] = list(cherrybomb_juego["participantes"])

    if cherrybomb_juego["modo"] == "players":
        bot.send_message(chat_id, "ㅤ⸜(*ˊᗜˋ*)⸝ㅤ¡el admin inició la partida de cherry bomb!\n  ⎯ ⠀aguarden un momento mientras se eligen las cerezas explosivas. tienen 45 segundos para seleccionar su cereza mortal en mi privado.", message_thread_id=thread_id)
        iniciar_ronda_privada_players(chat_id)
    else:
        bot.send_message(chat_id, "ㅤ⸜(*ˊᗜˋ*)⸝ㅤ¡el admin inició la partida de cherry bomb!\n  ⎯ ⠀aguarden un momento mientras se eligen las cerezas explosivas... o algo más.", message_thread_id=thread_id)
        
        admin_nickname = message.from_user.first_name
        msg_admin = (
            f"ㅤ(๑>ᴗ<๑)ㅤholi, {admin_nickname}! has iniciado una partida de cherry bomb con modo admin. necesito que selecciones las cerezas que contienen bombas o sorpresas.\n\n"
            "✦ FUNCIONAMIENTO DE LA OPCIÓN PODRIDA:\n"
            "Si quieres que una cereza le reste robux/puntos a quien la coma sin eliminarlo de la partida, escribe la palabra podrida y el monto a restar al lado del número.\n\n"
            "Ejemplo de respuesta:\n"
            "5\n"
            "13 podrida 5\n"
            "18\n"
            "9 podrida 10\n\n"
            "(En este ejemplo: las cerezas 5 y 18 explotan y eliminan al jugador; la 13 resta 5 robux y la 9 resta 10 robux pero continúan en la partida).\n\n"
            "El juego en el grupo iniciará automáticamente luego de que el bot valide los números."
        )
        try:
            bot.send_message(user_id, msg_admin)
        except Exception:
            pass
        iniciar_ronda_privada_admin(chat_id)

def iniciar_ronda_privada_players(chat_id):
    cherrybomb_juego["elecciones_privadas"].clear()

    for p in cherrybomb_juego["participantes_activos"]:
        uid = usuarios_ids.get(p)
        if uid:
            nickname = p
            try:
                user_chat = bot.get_chat(uid)
                nickname = user_chat.first_name
            except Exception:
                pass

            msg_p = (
                f"ㅤ(๑>ᴗ<๑)ㅤholi, {nickname}! estás participando en una partida de cherry bomb con modo players. "
                "necesito que selecciones la cereza que deseas detonar, envíame únicamente un número del 1-25."
            )
            try:
                bot.send_message(uid, msg_p)
            except Exception:
                pass

    t = threading.Thread(target=timer_mode_players, args=(chat_id,))
    t.daemon = True
    t.start()

def iniciar_ronda_privada_admin(chat_id):
    cherrybomb_juego["elecciones_privadas"].clear()
    t = threading.Thread(target=timer_mode_admin, args=(chat_id,))
    t.daemon = True
    t.start()

@bot.message_handler(func=lambda m: cherrybomb_juego["fase"] == "jugando" and m.chat.type == 'private')
def procesar_privado_cherrybomb(message):
    uid = message.from_user.id
    username = message.from_user.username if message.from_user.username else message.from_user.first_name

    if cherrybomb_juego["modo"] == "admin" and uid == cherrybomb_juego["admin_id"]:
        lineas = message.text.strip().split("\n")
        explosivas = []
        podridas = {}
        for l in lineas:
            partes = l.strip().split()
            if not partes:
                continue
            if partes[0].isdigit():
                num = int(partes[0])
                if len(partes) >= 3 and partes[1].lower() == "podrida" and partes[2].isdigit():
                    podridas[num] = int(partes[2])
                else:
                    explosivas.append(num)

        cherrybomb_juego["tablero_explosivas"] = explosivas
        cherrybomb_juego["podridas_info"] = podridas
        bot.send_message(uid, "✦ Cerezas configuradas con éxito. ¡Iniciando la partida en el grupo!")
        return

    if cherrybomb_juego["modo"] == "players" and username in cherrybomb_juego["participantes_activos"]:
        if message.text.strip().isdigit():
            num = int(message.text.strip())
            if 1 <= num <= 25:
                cherrybomb_juego["elecciones_privadas"][username] = num
                bot.send_message(uid, f"✦ Cereza {num} registrada para detonar.")

def timer_mode_players(chat_id):
    time.sleep(45)
    if cherrybomb_juego["fase"] == "jugando":
        cherrybomb_juego["tablero_explosivas"] = list(cherrybomb_juego["elecciones_privadas"].values())
        comenzar_turnos_tablero(chat_id)

def timer_mode_admin(chat_id):
    time.sleep(30)
    if cherrybomb_juego["fase"] == "jugando":
        comenzar_turnos_tablero(chat_id)

def comenzar_turnos_tablero(chat_id):
    thread_id = cherrybomb_juego["thread_id"]
    grid = generar_tablero_grid()
    bot.send_message(chat_id, grid, message_thread_id=thread_id)

    cherrybomb_juego["turno_index"] = 0
    siguiente_turno_cherry(chat_id)

def siguiente_turno_cherry(chat_id):
    thread_id = cherrybomb_juego["thread_id"]

    if len(cherrybomb_juego["participantes_activos"]) <= 1:
        finalizar_cherrybomb(chat_id)
        return

    actual = cherrybomb_juego["participantes_activos"][cherrybomb_juego["turno_index"]]
    texto = (
        f"  ೨       ¡es el turno de @{actual}! por favor, usa /eat [número].\n"
        "  ೨      ¡el tiempo corre! si no eliges en 30 segundos, serás automáticamente eliminado."
    )
    bot.send_message(chat_id, texto, message_thread_id=thread_id)

    if cherrybomb_juego["timer_eat"]:
        cherrybomb_juego["timer_eat"].cancel()

    t = threading.Timer(30.0, descalificar_afk_cherry, args=[chat_id, actual])
    cherrybomb_juego["timer_eat"] = t
    t.start()

def descalificar_afk_cherry(chat_id, jugador):
    thread_id = cherrybomb_juego["thread_id"]
    if cherrybomb_juego["fase"] == "jugando":
        if cherrybomb_juego["participantes_activos"] and cherrybomb_juego["participantes_activos"][cherrybomb_juego["turno_index"]] == jugador:
            bot.send_message(chat_id, f"૮₍⇀‸↼‶₎ა   @{jugador}, demoraste mucho... quedas fuera de la partida.", message_thread_id=thread_id)
            cherrybomb_juego["participantes_activos"].remove(jugador)

            if len(cherrybomb_juego["participantes_activos"]) <= 1:
                finalizar_cherrybomb(chat_id)
            else:
                if cherrybomb_juego["turno_index"] >= len(cherrybomb_juego["participantes_activos"]):
                    cherrybomb_juego["turno_index"] = 0
                siguiente_turno_cherry(chat_id)

@bot.message_handler(commands=['eat'])
def comer_cereza(message):
    chat_id = message.chat.id
    username = message.from_user.username if message.from_user.username else message.from_user.first_name
    thread_id = get_thread_id(message)

    if cherrybomb_juego["fase"] != "jugando" or chat_id != cherrybomb_juego["chat_id"]:
        return

    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return

    num = int(args[1])
    if num < 1 or num > 25:
        return

    actual = cherrybomb_juego["participantes_activos"][cherrybomb_juego["turno_index"]]
    if username != actual:
        return

    if cherrybomb_juego["timer_eat"]:
        cherrybomb_juego["timer_eat"].cancel()

    cherrybomb_juego["cerezas_comidas"].add(num)

    if num in cherrybomb_juego["tablero_explosivas"]:
        bot.send_message(chat_id, f"(ᴗ‌ . ᴗ‌)     es una pena... @{username} comió la cereza equivocada, explotó en su estómago.", message_thread_id=thread_id)
        cherrybomb_juego["participantes_activos"].remove(username)

        if len(cherrybomb_juego["participantes_activos"]) <= 1:
            finalizar_cherrybomb(chat_id)
        else:
            bot.send_message(chat_id, "✦ ¡Se ha reiniciado el tablero! Todas las cerezas están disponibles de nuevo.", message_thread_id=thread_id)
            cherrybomb_juego["cerezas_comidas"].clear()
            if cherrybomb_juego["modo"] == "players":
                iniciar_ronda_privada_players(chat_id)
            else:
                iniciar_ronda_privada_admin(chat_id)
        return

    if cherrybomb_juego["modo"] == "admin" and num in cherrybomb_juego["podridas_info"]:
        cant = cherrybomb_juego["podridas_info"][num]
        puntos_sistema[username] = puntos_sistema.get(username, 0) - cant
        bot.send_message(chat_id, f"(´.•﹏•`)⠀ vaya... @{username} se ha comido una cereza podrida. por cortesía del admin, se te restarán -{cant} robux. la partida sigue.", message_thread_id=thread_id)
    else:
        bot.send_message(chat_id, f"⠀  ( ˘‌ ᵕ ˘‌♡)  ⠀buena elección, @{username} sigues dentro, la partida continúa.", message_thread_id=thread_id)

    cherrybomb_juego["turno_index"] = (cherrybomb_juego["turno_index"] + 1) % len(cherrybomb_juego["participantes_activos"])
    time.sleep(2)
    siguiente_turno_cherry(chat_id)

def finalizar_cherrybomb(chat_id):
    thread_id = cherrybomb_juego["thread_id"]
    if len(cherrybomb_juego["participantes_activos"]) == 1:
        ganador = cherrybomb_juego["participantes_activos"][0]
        registrar_victoria(ganador)
        texto = f"⸜(*ˊᗜˋ*)⸝ ¡tenemos un ganador! @{ganador} es el último en pie, muchísimas felicidades por sobrevivir a cherry bomb, te llevas {cherrybomb_juego['premio']}."
    else:
        texto = " (╥﹏╥)  Cherry Bomb terminó sin ningún ganador."

    bot.send_message(chat_id, texto, message_thread_id=thread_id)
    cherrybomb_juego["fase"] = "inactivo"

# --- MINERÍA ---

def generar_texto_lobby_mineria():
    return (
        "ㅤㅤᡣ𐭩ㅤㅤㅤ¡ℳineria iniciada!ㅤㅤㅤㅤㅤㅤ\n\n"
        " ◌   ֢  ׄ   todos tienen la oportunidad de minar, pero... ¿tendrán la suerte de obtener las mejores recompensas? presionen el botón para descubrirlo. ( ;´꒳;`) \n"
    )

RECOMPENSAS_MINERIA = [
    {"p": 0, "m": "nada... ( ꩜ ᯅ ꩜;)\n¡suerte para la próxima!", "weight": 20},
    {"p": 3, "m": "   ⊹     una piedrita común...\n૮ • ﻌ - ა ¡tienes 3 puntos!", "weight": 18},
    {"p": 5, "m": "   ⊹     un pedacito de carbón... \n(´๑•_•๑) no es mucho, pero sirve...\n¡tienes 5 puntos!", "weight": 16},
    {"p": 8, "m": "   ⊹     una piedra que brilla un poquito...\n૮₍´｡• ᵕ •｡₎ა ¡tienes 8 puntos!", "weight": 14},
    {"p": 12, "m": "   ⊹    un cristal de cuarzo pequeño...\n(ᐡ･ ﻌ ･ᐡ) ¡qué bonito!\n¡tienes 12 puntos!", "weight": 12},
    {"p": 18, "m": "   ⊹     una pequeña cueva con honguitos brillantes...\n꒰◍ॢ•ᴗ•◍ॢ꒱ ¡tienes 18 puntos!", "weight": 10},
    {"p": 25, "m": "   ⊹     un fragmento de hierro antiguo...\n૮₍˶• . • ⑅₎ა parece útil...\n¡tienes 8 puntos!", "weight": 8},
    {"p": 32, "m": "   ⊹     un cristal azul escondido...\n૮₍˶ᵔ ᵕ ᵔ˶₎ა ¡qué hallazgo tan lindo!\n¡tienes 32 puntos!", "weight": 7},
    {"p": 40, "m": "   ⊹     una moneda vieja enterrada...\n૮꒰ต´˘ต꒱ა alguien la perdió hace mucho...\n¡tienes 40 puntos!", "weight": 6},
    {"p": 50, "m": "   ⊹     una amatista brillante...\n(∗˃̶ ᵕ ˂̶∗) ¡encontraste algo especial!\n¡tienes 50 puntos!", "weight": 5},
    {"p": 60, "m": "   ⊹    un cristal con energía extraña...\n૮꒰˶˃̵ ^ ˂̵˵꒱ა ¡brilla muchísimo!\n¡tienes 60 puntos!", "weight": 4},
    {"p": 70, "m": "   ⊹     un pequeño cofre bajo las rocas...\n૮꒰⑅ᐢ ᵕ ᵕ ᐢ⑅꒱ ¡¿qué habrá dentro?!\n¡tienes 70 puntos!", "weight": 3},
    {"p": 78, "m": "   ⊹     una perla escondida bajo la tierra...\n(⑅˘͈ ᵕ ˘͈ )  ¡es preciosa!\n¡tienes 78 puntos!", "weight": 2.5},
    {"p": 85, "m": "   ⊹     una pequeña veta de oro...\n໒꒰ྀི ∩ ˃ ᵕ ˂ ∩ ꒱ྀི১ ¡qué suerte!\n¡tienes 85 puntos!", "weight": 2},
    {"p": 90, "m": "   ⊹     un zafiro muy raro...\n૮꒰ྀི ᵔ ๑ ᵔ ꒱ა ¡tuviste mucha suerte!\n¡tienes 90 puntos!", "weight": 1.5},
    {"p": 95, "m": "   ⊹     un diamante rosa brillante...\n♡ ᖭི(ˊᗜˋ*)ᖫྀ ¡ES HERMOSO!\n¡tienes 95 puntos!", "weight": 1},
    {"p": 100, "m": "   ⊹    el tesoro secreto de cherrie...\n(♡´𓈒𓂂˘˘♡) ¡encontraste algo que casi nadie encuentra!\n¡tienes 100 puntos!", "weight": 0.5}
]

@bot.message_handler(commands=['mineria'])
def crear_mineria(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar minería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if mineria_juego["fase"] != "inactivo":
        bot.send_message(chat_id, " (╥﹏╥)  ya hay una partida de minería activa.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    premio = message.text[8:].strip()

    mineria_juego["fase"] = "lobby"
    mineria_juego["chat_id"] = chat_id
    mineria_juego["thread_id"] = thread_id
    mineria_juego["admin_id"] = user_id
    mineria_juego["premio"] = premio
    mineria_juego["participantes"] = []
    mineria_juego["puntos"] = {}
    mineria_juego["turnos_restantes"] = {}

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_mineria_lobby"))

    msg = bot.send_message(chat_id, generar_texto_lobby_mineria(), reply_markup=markup, message_thread_id=thread_id)
    mineria_juego["msg_lobby_id"] = msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "unirse_mineria_lobby")
def unirse_mineria_callback(call):
    if mineria_juego["fase"] != "lobby":
        bot.answer_callback_query(call.id, "El lobby ya no está disponible.", show_alert=True)
        return

    username = call.from_user.username if call.from_user.username else call.from_user.first_name
    usuarios_ids[username] = call.from_user.id

    if username in mineria_juego["participantes"]:
        bot.answer_callback_query(call.id, "Ya estás en la partida.", show_alert=True)
        return

    mineria_juego["participantes"].append(username)
    mineria_juego["puntos"][username] = 0
    mineria_juego["turnos_restantes"][username] = 3
    bot.answer_callback_query(call.id, "¡Te has unido a Minería!")

    bot.send_message(mineria_juego["chat_id"], f"  ୧        @{username} se ha unido. ¿listo para minar?", message_thread_id=mineria_juego["thread_id"])

@bot.message_handler(commands=['mineriastart'])
def iniciar_mineria_start(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar la minería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if mineria_juego["fase"] != "lobby":
        bot.send_message(chat_id, " (╥﹏╥)  no hay ningún lobby activo de minería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if mineria_juego["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if not mineria_juego["participantes"]:
        bot.send_message(chat_id, " (╥﹏╥)  se requieren participantes para iniciar.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    try:
        bot.edit_message_reply_markup(chat_id, mineria_juego["msg_lobby_id"], reply_markup=None)
    except Exception:
        pass

    mineria_juego["fase"] = "jugando"
    mineria_juego["turno_actual_index"] = 0
    siguiente_turno_mineria(chat_id)

def siguiente_turno_mineria(chat_id):
    thread_id = mineria_juego["thread_id"]
    
    con_turnos = [p for p in mineria_juego["participantes"] if mineria_juego["turnos_restantes"].get(p, 0) > 0]
    
    if not con_turnos:
        finalizar_mineria(chat_id)
        return

    # Mantenemos turnos totalmente intercalados usando la lista ordenada de participantes
    idx = mineria_juego["turno_actual_index"]
    for _ in range(len(mineria_juego["participantes"])):
        candidato = mineria_juego["participantes"][idx % len(mineria_juego["participantes"])]
        idx += 1
        if mineria_juego["turnos_restantes"].get(candidato, 0) > 0:
            mineria_juego["turno_actual_index"] = idx
            mineria_juego["turno_actual"] = candidato
            break

    jugador_turno = mineria_juego["turno_actual"]
    texto = (
        f"ㅤ୭ৎ ࣪ ׅ ㅤㅤ¡turno de @{jugador_turno}!\n"
        "ㅤ— ㅤㅤusa /minar para probar tu suerte."
    )
    bot.send_message(chat_id, texto, message_thread_id=thread_id)

@bot.message_handler(commands=['minar'])
def minar_accion(message):
    chat_id = message.chat.id
    username = message.from_user.username if message.from_user.username else message.from_user.first_name
    thread_id = get_thread_id(message)

    if mineria_juego["fase"] != "jugando" or chat_id != mineria_juego["chat_id"]:
        return

    if username != mineria_juego.get("turno_actual"):
        return

    weights = [r["weight"] for r in RECOMPENSAS_MINERIA]
    item = random.choices(RECOMPENSAS_MINERIA, weights=weights, k=1)[0]

    puntos = item["p"]
    mineria_juego["puntos"][username] += puntos
    mineria_juego["turnos_restantes"][username] -= 1
    
    mineria_historico[username] = mineria_historico.get(username, 0) + puntos

    msg_res = (
        f"  ୧       @{username}, encontraste...\n\n"
        f"{item['m']}"
    )
    bot.send_message(chat_id, msg_res, message_thread_id=thread_id)
    time.sleep(2)
    siguiente_turno_mineria(chat_id)

def finalizar_mineria(chat_id):
    thread_id = mineria_juego["thread_id"]
    
    ordenados = sorted(mineria_juego["puntos"].items(), key=lambda x: x[1], reverse=True)
    
    lineas = [f" ֢  ׄ   @{u} — {pts} points." for u, pts in ordenados]
    
    if ordenados and ordenados[0][1] > 0:
        registrar_victoria(ordenados[0][0])

    texto = "ㅤㅤ⠀ৎ⠀ㅤㅤ ℛesultados  :   \n\n" + "\n".join(lineas)
    bot.send_message(chat_id, texto, message_thread_id=thread_id)
    mineria_juego["fase"] = "inactivo"

@bot.message_handler(commands=['checkmineria', 'bestminers'])
def ver_best_miners(message):
    thread_id = get_thread_id(message)
    if not mineria_historico:
        bot.send_message(message.chat.id, " (╥﹏╥)  aún no hay registros globales de minería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    ordenados = sorted(mineria_historico.items(), key=lambda x: x[1], reverse=True)
    lineas = [f"✦ @{u} — {pts} puntos." for u, pts in ordenados]
    texto = "      ‿︵       𝘝𝘪𝘤𝘵𝘰𝘳𝘪𝘢𝘴 / 𝘉𝘦𝘴𝘵 𝘔𝘪𝘯𝘦𝘳𝘴 !\n\n" + "\n".join(lineas)
    bot.send_message(message.chat.id, texto, message_thread_id=thread_id)

@bot.message_handler(commands=['endmineria'])
def forzar_end_mineria(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes finalizar la minería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if mineria_juego["fase"] == "inactivo":
        bot.send_message(chat_id, " (╥﹏╥)  no hay ninguna minería activa.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    finalizar_mineria(chat_id)

# --- LOTERÍA ---

@bot.message_handler(commands=['loteria'])
def crear_loteria(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar la lotería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    premio = message.text[8:].strip()

    loteria_juego["fase"] = "compra"
    loteria_juego["chat_id"] = chat_id
    loteria_juego["thread_id"] = thread_id
    loteria_juego["admin_id"] = user_id
    loteria_juego["premio"] = premio
    loteria_juego["tickets_vendidos"].clear()
    loteria_juego["usuarios_registrados"].clear()

    texto = (
        "ㅤ୭ৎ ࣪ ׅ ㅤㅤ¡ha empezado la lotería!\n"
        "prueba tu suerte comprando tus tickets, usa /tickets para recibir 5 oportunidades para ganar el premio mayor, 5 robux."
    )
    bot.send_message(chat_id, texto, message_thread_id=thread_id)

@bot.message_handler(commands=['tickets'])
def pedir_tickets(message):
    chat_id = message.chat.id
    username = message.from_user.username if message.from_user.username else message.from_user.first_name
    thread_id = get_thread_id(message)

    if loteria_juego["fase"] != "compra" or chat_id != loteria_juego["chat_id"]:
        return

    if username in loteria_juego["usuarios_registrados"]:
        bot.send_message(chat_id, f" (╥﹏╥)  @{username}, ya reclamaste tus 5 tickets para esta lotería.", message_thread_id=thread_id)
        return

    usados = set(loteria_juego["tickets_vendidos"].keys())
    disponibles = [f"CHERRY{random.randint(1000, 9999)}" for _ in range(500)]
    disponibles = [t for t in disponibles if t not in usados]

    mis_tickets = random.sample(disponibles, 5)
    for t in mis_tickets:
        loteria_juego["tickets_vendidos"][t] = username
    loteria_juego["usuarios_registrados"].add(username)

    lista_tickets = "\n".join([f" 𝅄   {t}" for t in mis_tickets])
    texto_res = (
        f"⠀ꕮ⠀ 𝑳ottery tickets for {username}.\n\n"
        f"{lista_tickets}"
    )
    bot.send_message(chat_id, texto_res, message_thread_id=thread_id)

@bot.message_handler(commands=['jugarloteria'])
def realizar_sorteo_loteria(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes realizar el sorteo.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if loteria_juego["fase"] != "compra":
        bot.send_message(chat_id, " (╥﹏╥)  no hay una lotería en fase de compra.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if loteria_juego["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la lotería puede sortearla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if not loteria_juego["tickets_vendidos"]:
        bot.send_message(chat_id, " (╥﹏╥)  nadie compró tickets en esta lotería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    ganador_ticket = random.choice(list(loteria_juego["tickets_vendidos"].keys()))
    ganador_user = loteria_juego["tickets_vendidos"][ganador_ticket]

    loteria_juego["fase"] = "espera_reclamo"
    loteria_juego["ticket_ganador"] = ganador_ticket
    loteria_juego["ganador_esperado"] = ganador_user
    loteria_juego["tiempo_limite"] = time.time() + 45
    loteria_juego["reclamado"] = False

    texto = (
        "ㅤㅤᡣ𐭩ㅤㅤㅤresultados de la lotería cherrie . . .\n"
        f"         —         nuestro ticket ganador es el {ganador_ticket}.\n"
        "el ganador tiene 45 segundos para escribir ¡lotería! en el chat y asegurar su victoria."
    )
    bot.send_message(chat_id, texto, message_thread_id=thread_id)

    t = threading.Thread(target=timer_reclamo_loteria, args=(chat_id,))
    t.daemon = True
    t.start()

def timer_reclamo_loteria(chat_id):
    time.sleep(45)
    if loteria_juego["fase"] == "espera_reclamo" and not loteria_juego["reclamado"]:
        thread_id = loteria_juego["thread_id"]
        bot.send_message(
            chat_id,
            f"(╥﹏╥)  @{loteria_juego['ganador_esperado']} demoró mucho y no cantó su lotería...",
            message_thread_id=thread_id
        )
        del loteria_juego["tickets_vendidos"][loteria_juego["ticket_ganador"]]
        
        if loteria_juego["tickets_vendidos"]:
            loteria_juego["fase"] = "compra"
            realizar_sorteo_loteria_directo(chat_id)
        else:
            bot.send_message(chat_id, " (╥﹏╥)  ya no quedan más tickets para sortear.", message_thread_id=thread_id)
            loteria_juego["fase"] = "inactivo"

def realizar_sorteo_loteria_directo(chat_id):
    ganador_ticket = random.choice(list(loteria_juego["tickets_vendidos"].keys()))
    ganador_user = loteria_juego["tickets_vendidos"][ganador_ticket]

    loteria_juego["fase"] = "espera_reclamo"
    loteria_juego["ticket_ganador"] = ganador_ticket
    loteria_juego["ganador_esperado"] = ganador_user
    loteria_juego["tiempo_limite"] = time.time() + 45
    loteria_juego["reclamado"] = False

    thread_id = loteria_juego["thread_id"]
    texto = (
        "ㅤㅤᡣ𐭩ㅤㅤㅤresultados de la lotería cherrie . . .\n"
        f"         —         nuestro ticket ganador es el {ganador_ticket}.\n"
        "el ganador tiene 45 segundos para escribir ¡lotería! en el chat y asegurar su victoria."
    )
    bot.send_message(chat_id, texto, message_thread_id=thread_id)

    t = threading.Thread(target=timer_reclamo_loteria, args=(chat_id,))
    t.daemon = True
    t.start()

@bot.message_handler(func=lambda m: loteria_juego["fase"] == "espera_reclamo")
def validar_reclamo_loteria(message):
    if message.chat.id == loteria_juego["chat_id"]:
        text_clean = message.text.strip().lower()
        if text_clean == "¡lotería!" or text_clean == "¡loteria!" or text_clean == "loteria!" or text_clean == "lotería!":
            username = message.from_user.username if message.from_user.username else message.from_user.first_name
            if username == loteria_juego["ganador_esperado"]:
                loteria_juego["reclamado"] = True
                loteria_juego["fase"] = "inactivo"
                registrar_victoria(username)
                premio_str = loteria_juego["premio"] if loteria_juego["premio"] else "5 robux"
                texto = f"✦  ¡@{username}  es el ganador de la lotería! ha ganado {premio_str} ♡"
                bot.send_message(message.chat.id, texto, message_thread_id=get_thread_id(message))

# --- RED OR PINK ---

def generar_texto_lobby_redpink():
    parts = "\n".join([f"        ⊹    @{p}" for p in redpink_juego["participantes"]]) if redpink_juego["participantes"] else "        ⊹    @"
    return (
        "ㅤ ⪩⪨     ㅤnueva partida de red or pink  .ᐟ\n\n"
        "   ⎯    𝗽︩︩︪articipantes     :\n"
        f"{parts}\n\n"
        "₍˄..˄₎꠹     presiona el botón para poder hacer tu apuesta...\n"
        "admin, puedes colocar /redpinkstart para dar inicio a la partida."
    )

@bot.message_handler(commands=['redpink'])
def crear_redpink(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar Red or Pink.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if redpink_juego["fase"] != "inactivo":
        bot.send_message(chat_id, " (╥﹏╥)  ya hay una partida de Red or Pink activa.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    premio = message.text[8:].strip()

    redpink_juego["fase"] = "lobby"
    redpink_juego["chat_id"] = chat_id
    redpink_juego["thread_id"] = thread_id
    redpink_juego["admin_id"] = user_id
    redpink_juego["premio"] = premio
    redpink_juego["participantes"].clear()
    redpink_juego["elecciones"].clear()

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_redpink_lobby"))

    msg = bot.send_message(chat_id, generar_texto_lobby_redpink(), reply_markup=markup, message_thread_id=thread_id)
    redpink_juego["msg_lobby_id"] = msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "unirse_redpink_lobby")
def unirse_redpink_callback(call):
    if redpink_juego["fase"] != "lobby":
        bot.answer_callback_query(call.id, "El lobby ya no está disponible.", show_alert=True)
        return

    username = call.from_user.username if call.from_user.username else call.from_user.first_name
    usuarios_ids[username] = call.from_user.id

    if username in redpink_juego["participantes"]:
        bot.answer_callback_query(call.id, "Ya estás en la partida.", show_alert=True)
        return

    redpink_juego["participantes"].add(username)
    bot.answer_callback_query(call.id, "¡Te has unido a Red or Pink!")

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_redpink_lobby"))
    try:
        bot.edit_message_text(generar_texto_lobby_redpink(), redpink_juego["chat_id"], redpink_juego["msg_lobby_id"], reply_markup=markup)
    except Exception:
        pass

@bot.message_handler(commands=['redpinkstart'])
def iniciar_apuestas_redpink(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar Red or Pink.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if redpink_juego["fase"] != "lobby":
        bot.send_message(chat_id, " (╥﹏╥)  no hay ningún lobby de Red or Pink listo para iniciar.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if redpink_juego["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if not redpink_juego["participantes"]:
        bot.send_message(chat_id, " (╥﹏╥)  se requieren participantes para iniciar.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    try:
        bot.edit_message_reply_markup(chat_id, redpink_juego["msg_lobby_id"], reply_markup=None)
    except Exception:
        pass

    redpink_juego["fase"] = "apuestas"

    texto_apuestas = (
        "⎯        ¡es hora de apostar!\n\n"
        "(ᐢ>‌⩊<) sigue tu instinto y escribe /red o /pink según cuál crees que será la monedita ganadora. \n"
        "admin, puedes cerrar las apuestas con /redpinknow cuando estés listo."
    )
    bot.send_message(chat_id, texto_apuestas, message_thread_id=thread_id)

@bot.message_handler(commands=['red', 'pink'])
def registrar_apuesta_redpink(message):
    chat_id = message.chat.id
    username = message.from_user.username if message.from_user.username else message.from_user.first_name
    thread_id = get_thread_id(message)

    if redpink_juego["fase"] != "apuestas" or chat_id != redpink_juego["chat_id"]:
        return

    if username not in redpink_juego["participantes"]:
        return

    eleccion = message.text.split()[0].replace('/', '').lower() # 'red' o 'pink'
    redpink_juego["elecciones"][username] = eleccion
    bot.send_message(chat_id, f"✦ @{username} ha apostado por **{eleccion.upper()}** ♡", parse_mode="Markdown", message_thread_id=thread_id)

@bot.message_handler(commands=['redpinknow'])
def cerrar_y_revelar_redpink(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes cerrar las apuestas.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if redpink_juego["fase"] != "apuestas":
        bot.send_message(chat_id, " (╥﹏╥)  no hay una partida de Red or Pink en fase de apuestas.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if redpink_juego["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    # Sorteo aleatorio para participantes que no apostaron a tiempo
    for p in redpink_juego["participantes"]:
        if p not in redpink_juego["elecciones"]:
            redpink_juego["elecciones"][p] = random.choice(["red", "pink"])

    resultado = random.choice(["red", "pink"])
    ganadores = [p for p, c in redpink_juego["elecciones"].items() if c == resultado]

    for g in ganadores:
        registrar_victoria(g)

    # Sticker aleatorio del pack
    if STICKERS_CHERRIE:
        sticker_elegido = random.choice(STICKERS_CHERRIE)
        try:
            bot.send_sticker(chat_id, sticker_elegido, message_thread_id=thread_id)
        except Exception:
            pass

    resultado_str = "RED 🔴" if resultado == "red" else "PINK 🩷"
    parts_ganadores = "\n".join([f"        ⊹    @{g}" for g in ganadores]) if ganadores else "        ⊹    ninguno..."

    texto_res = (
        f"⎯        ¡el resultado es... {resultado_str}!  ♡\n\n"
        "   (๑´`๑)     ganadores :\n"
        f"{parts_ganadores}"
    )
    bot.send_message(chat_id, texto_res, message_thread_id=thread_id)
    redpink_juego["fase"] = "inactivo"

# --- CARRERA ANÓNIMA ---

@bot.message_handler(commands=['carrera'])
def crear_carrera(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar una carrera.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if carrera_juego["fase"] != "inactivo":
        bot.send_message(chat_id, " (╥﹏╥)  ya hay una carrera activa.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    premio = message.text[8:].strip()

    carrera_juego["fase"] = "lobby"
    carrera_juego["chat_id"] = chat_id
    carrera_juego["thread_id"] = thread_id
    carrera_juego["admin_id"] = user_id
    carrera_juego["premio"] = premio
    carrera_juego["participantes"].clear()
    carrera_juego["emojis_asignados"].clear()
    carrera_juego["posiciones"].clear()

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_carrera_lobby"))

    texto_lobby = (
        "ㅤㅤ```python
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

# --- ESTADOS GLOBALES Y REGISTROS ---

sorteos = {}
puntos_sistema = {}          # {username: puntos_int}
quiz_aciertos = {}           # {username: total_aciertos_int}
mineria_historico = {}       # {username: puntos_acumulados_int}
victorias_historico = {}     # {username: total_victorias_int}
usuarios_ids = {}            # {username: user_id}

def registrar_victoria(username):
    victorias_historico[username] = victorias_historico.get(username, 0) + 1

quiz_juego = {
    "fase": "inactivo",
    "chat_id": None,
    "thread_id": None,
    "admin_id": None,
    "premio": "",
    "participantes": [],
    "participantes_activos": [],
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
    "tickets_vendidos": {}, # {ticket_str: username}
    "usuarios_registrados": set(),
    "ticket_ganador": None,
    "ganador_esperado": None,
    "tiempo_limite": 0,
    "reclamado": False,
    "timer_task": None
}

redpink_juego = {
    "fase": "inactivo",
    "chat_id": None,
    "thread_id": None,
    "admin_id": None,
    "premio": "",
    "participantes": [],
    "elecciones": {},
    "msg_lobby_id": None
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
    "tablero_explosivas": [],
    "podridas_info": {},
    "cerezas_comidas": set(),
    "turno_index": 0,
    "elecciones_privadas": {},
    "msg_tablero_id": None,
    "msg_lobby_id": None,
    "timer_eat": None
}

EMOJIS_CARRERA = ["🍒", "🍓", "🍉", "🍊", "🍍", "🍋‍🟩", "🍏", "🫐", "🍇", "🍐", "🥭", "🍌", "🥝", "🍑"]

def get_thread_id(message):
    return message.message_thread_id if message.is_topic_message else None

# --- GESTIÓN DE ADMINS ---

@bot.message_handler(commands=['admin'])
def agregar_admin_por_id(message):
    username = message.from_user.username
    if not username or username.lower() != SUPER_ADMIN.lower():
        return

    args = message.text.split()[1:]
    if not args:
        bot.send_message(message.chat.id, "✦ Estructura incorrecta. Uso: /admin ID1 ID2 ID3")
        return

    agregados = []
    for arg in args:
        arg_clean = arg.replace('+', '').strip()
        if arg_clean.isdigit():
            user_id_add = int(arg_clean)
            ADMINS_PERMITIDOS.add(user_id_add)
            agregados.append(str(user_id_add))

    if agregados:
        guardar_admins()
        bot.send_message(message.chat.id, f"ㅤ♡ㅤ¡Usuario(s) {', '.join(agregados)} agregado(s) a la lista de admins autorizados!")
    else:
        bot.send_message(message
