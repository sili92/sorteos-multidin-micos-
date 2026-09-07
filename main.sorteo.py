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
    "podridas_info": {},       # {numero_cereza: cantidad_robux}
    "turno_index": 0,
    "elecciones_privadas": {},
    "msg_tablero_id": None,
    "msg_lobby_id": None,
    "timer_eat": None,
    "duracion_pila": 25
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

# --- COMANDO /beg ---
@bot.message_handler(commands=['beg'])
def suplicar_robux(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)
    nickname1 = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name

    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        nickname2 = f"@{target_user.username}" if target_user.username else target_user.first_name
        texto = f"ㅤ૮  .ܸ  .ܸ ྀི ა  ㅤ{nickname1} está suplicando a {nickname2} por robux...ㅤ"
    else:
        texto = f"ㅤ૮  .ܸ  .ܸ ྀི ა  ㅤ{nickname1} está suplicando por robux...ㅤ"

    bot.send_message(
        chat_id, 
        texto, 
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
        bot.send_message(chat_id, "✦ Estructura incorrecta. Ejemplo: /quiz VIP Mensual", message_thread_id=thread_id, reply_to_message_id=message.message_id)
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

    time.sleep(3)
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
    time.sleep(3)
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
        f"ㅤㅤㅤㅤㅤ୭ৎ ࣪ ׅ ㅤRonda {quiz_juego['dificultad']}ㅤ (Sobrevivientes: {len(quiz_juego['participantes_activos'])})\n\n"
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
    eliminados_incorrecta = set()
    eliminados_afk = set()

    for p in list(quiz_juego["participantes_activos"]):
        if p in quiz_juego["respuestas"]:
            resp = quiz_juego["respuestas"][p]
            if resp["opcion"] == correcta_idx:
                acertaron.append((p, resp["tiempo"]))
                quiz_aciertos[p] = quiz_aciertos.get(p, 0) + 1
            else:
                eliminados_incorrecta.add(p)
        else:
            eliminados_afk.add(p)

    es_ultima_ronda_2p = (len(quiz_juego["participantes_activos"]) == 2)
    mensaje_eliminacion_especial = ""

    if es_ultima_ronda_2p and len(acertaron) == 2:
        acertaron.sort(key=lambda x: x[1])
        mas_lento = acertaron[1][0]
        eliminados_incorrecta.add(mas_lento)
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
        
        str_eliminados = " ".join([f"@{e}" for e in eliminados_incorrecta]) if eliminados_incorrecta else "@"
        str_afk = " ".join([f"@{e}" for e in eliminados_afk]) if eliminados_afk else "@"

        if mensaje_eliminacion_especial:
            texto_resumen = (
                " (๑>ᴗ<๑)  ¡tiempo agotado!\n\n"
                f"𓂃   La respuesta correcta era  :  **{texto_correcta}**\n\n"
                f"✦   {mensaje_eliminacion_especial}"
            )
        else:
            texto_resumen = (
                " (๑>ᴗ<๑)  ¡tiempo agotado!\n\n"
                f"𓂃   La respuesta correcta era  :  **{texto_correcta}**\n\n"
                f"𓂃   Eliminados  :  {str_eliminados}\n"
                f"𓂃   AFK  :  {str_afk}"
            )

    time.sleep(3)
    bot.send_message(chat_id, texto_resumen, parse_mode="Markdown", message_thread_id=thread_id)

    if len(quiz_juego["participantes_activos"]) <= 1:
        time.sleep(3)
        finalizar_juego_quiz(chat_id)
    else:
        quiz_juego["dificultad"] += 1
        time.sleep(3)
        bot.send_message(chat_id, "✦⠀¡Siguiente ronda en unos segundos! Prepárense... ૮ ˶• ˔ •˶ ა", message_thread_id=thread_id)
        time.sleep(3)
        lanzar_siguiente_pregunta(chat_id)

def finalizar_juego_quiz(chat_id):
    thread_id = quiz_juego["thread_id"]
    if len(quiz_juego["participantes_activos"]) == 1:
        ganador = list(quiz_juego["participantes_activos"])[0]
        registrar_victoria(ganador)
        texto_final = (
            "ㅤㅤㅤㅤㅤ୭ৎ ࣪ ׅ ㅤ¡Resultados!ㅤ\n\n"
            f"𓂃   premio  :  {quiz_juego['premio']}\n"
            f"𓂃   ganador/es  :  @{ganador}\n\n"
            f"ㅤㅤㅤᡣ𐭩ㅤ¡felicidades! reclama con @{bot.get_chat(quiz_juego['admin_id']).username or 'admin'}"
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
    texto = "      ‿︵       𝘘𝘶𝘪𝘻 𝘓𝘦𝘨𝘦𝘯𝘥𝘴 !\n\n" + "\n".join(lineas)
    bot.send_message(message.chat.id, texto, message_thread_id=thread_id)

# --- CHERRY BOMB ---
def generar_tablero_grid():
    grid = (
        "⠀⠀  ⎯  ⠀⠀⠀𝕿‌ ablero de cherries. \n\n"
        " 1   2   3   4   5  \n"
        " 6   7   8   9   10  \n"
        " 11   12   13   14   15  \n"
        " 16   17   18   19   20  \n"
        " 21   22   23   24   25  "
    )
    return grid

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
        try:
            bot.send_message(user_id, "🍒 Instrucciones de Admin:\nPara pudrir cerezas, responde con el formato:\n[número] podrida [monto]\nEjemplo: 15 podrida 5")
        except Exception:
            pass
        iniciar_ronda_privada_admin(chat_id)

def iniciar_ronda_privada_players(chat_id):
    cherrybomb_juego["elecciones_privadas"].clear()
    cherrybomb_juego["tablero_explosivas"] = random.sample(range(1, 26), 3)

    for p in cherrybomb_juego["participantes_activos"]:
        uid = usuarios_ids.get(p)
        if uid:
            try:
                bot.send_message(uid, "🍒 Elige tu cereza enviándome: /eat [1-25]")
            except Exception:
                pass

    t = threading.Thread(target=timer_mode_players, args=(chat_id,))
    t.daemon = True
    t.start()

def iniciar_ronda_privada_admin(chat_id):
    cherrybomb_juego["elecciones_privadas"].clear()
    cherrybomb_juego["tablero_explosivas"] = random.sample(range(1, 26), 3)

    t = threading.Thread(target=timer_mode_admin, args=(chat_id,))
    t.daemon = True
    t.start()

@bot.message_handler(func=lambda m: cherrybomb_juego["fase"] == "jugando" and cherrybomb_juego["modo"] == "admin" and m.from_user.id == cherrybomb_juego["admin_id"] and "podrida" in m.text.lower())
def set_cereza_podrida_admin(message):
    partes = message.text.lower().split()
    try:
        num = int(partes[0])
        monto = int(partes[2])
        cherrybomb_juego["podridas_info"][num] = monto
        bot.send_message(message.chat.id, f"✦ Cereza {num} configurada como PODRIDA con -{monto} robux.")
    except Exception:
        pass

def timer_mode_players(chat_id):
    time.sleep(45)
    if cherrybomb_juego["fase"] == "jugando":
        comenzar_turnos_tablero(chat_id)

def timer_mode_admin(chat_id):
    time.sleep(15)
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
        f"✦    ¡es el turno de @{actual}! por favor, usa /eat [número].\n"
        "✦   ¡el tiempo corre! si no eliges en 30 segundos, serás automáticamente eliminado."
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
        actual = cherrybomb_juego["participantes_activos"][cherrybomb_juego["turno_index"]]
        if actual == jugador:
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

    if cherrybomb_juego["fase"] != "jugando":
        return

    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return

    num = int(args[1])
    if num < 1 or num > 25:
        return

    if message.chat.type == 'private':
        if username in cherrybomb_juego["participantes_activos"]:
            cherrybomb_juego["elecciones_privadas"][username] = num
            bot.send_message(chat_id, f"✦ Cereza {num} seleccionada. ¡Mucha suerte!")
        return

    if chat_id != cherrybomb_juego["chat_id"]:
        return

    actual = cherrybomb_juego["participantes_activos"][cherrybomb_juego["turno_index"]]
    if username != actual:
        return

    if cherrybomb_juego["timer_eat"]:
        cherrybomb_juego["timer_eat"].cancel()

    if num in cherrybomb_juego["tablero_explosivas"]:
        bot.send_message(chat_id, f"(ᴗ‌ . ᴗ‌)     es una pena... @{username} comió la cereza equivocada, explotó en su estómago.", message_thread_id=thread_id)
        cherrybomb_juego["participantes_activos"].remove(username)

        if len(cherrybomb_juego["participantes_activos"]) <= 1:
            finalizar_cherrybomb(chat_id)
        else:
            bot.send_message(chat_id, "✦ ¡Se ha reiniciado el tablero! Todas las cerezas están disponibles de nuevo.", message_thread_id=thread_id)
            if cherrybomb_juego["modo"] == "players":
                iniciar_ronda_privada_players(chat_id)
            else:
                iniciar_ronda_privada_admin(chat_id)
        return

    if cherrybomb_juego["modo"] == "admin" and num in cherrybomb_juego["podridas_info"]:
        cant = cherrybomb_juego["podridas_info"][num]
        puntos_sistema[username] = max(0, puntos_sistema.get(username, 0) - cant)
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
        "ㅤㅤᡣ𐭩ㅤㅤㅤ¡hora de minar!\n"
        "prueba tu suerte y únete para ganar o perder minery points."
    )

@bot.message_handler(commands=['mineria'])
def crear_mineria(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar minería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if mineria_juego["fase"] != "inactivo":
        bot.send_message(chat_id, " (╥﹏╥)  ya hay un juego de minería en curso.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    premio = message.text[8:].strip()
    if not premio:
        bot.send_message(chat_id, "✦ Estructura incorrecta. Ejemplo: /mineria 500 robux", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    mineria_juego["fase"] = "lobby"
    mineria_juego["chat_id"] = chat_id
    mineria_juego["thread_id"] = thread_id
    mineria_juego["admin_id"] = user_id
    mineria_juego["premio"] = premio
    mineria_juego["participantes"].clear()
    mineria_juego["puntos"].clear()
    mineria_juego["turnos_restantes"].clear()

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_mineria_lobby"))

    time.sleep(3)
    msg = bot.send_message(chat_id, generar_texto_lobby_mineria(), reply_markup=markup, message_thread_id=thread_id)
    mineria_juego["msg_lobby_id"] = msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "unirse_mineria_lobby")
def unirse_mineria_callback(call):
    if mineria_juego["fase"] != "lobby":
        bot.answer_callback_query(call.id, "El lobby ya no está activo.", show_alert=True)
        return

    username = call.from_user.username if call.from_user.username else call.from_user.first_name
    usuarios_ids[username] = call.from_user.id

    if username in mineria_juego["participantes"]:
        bot.answer_callback_query(call.id, "Ya estás en la lista de mineros.", show_alert=True)
        return

    mineria_juego["participantes"].append(username)
    mineria_juego["puntos"][username] = 0
    mineria_juego["turnos_restantes"][username] = 5
    bot.answer_callback_query(call.id, "¡Te has unido a la Minería!")

    bot.send_message(mineria_juego["chat_id"], f"✦ @{username} se ha unido. ¿listo para minar?", message_thread_id=mineria_juego["thread_id"])

@bot.message_handler(commands=['mineriastart'])
def iniciar_mineria_start(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if mineria_juego["fase"] != "lobby":
        bot.send_message(chat_id, " (╥﹏╥)  no hay ningún lobby de minería esperando.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if mineria_juego["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if not mineria_juego["participantes"]:
        bot.send_message(chat_id, " (╥﹏╥)  no hay mineros registrados.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    try:
        bot.edit_message_reply_markup(chat_id, mineria_juego["msg_lobby_id"], reply_markup=None)
    except Exception:
        pass

    mineria_juego["fase"] = "jugando"
    mineria_juego["turno_actual_index"] = 0

    notificar_turno_mineria(chat_id)

def notificar_turno_mineria(chat_id):
    thread_id = mineria_juego["thread_id"]
    if all(t == 0 for t in mineria_juego["turnos_restantes"].values()):
        finalizar_mineria(chat_id)
        return

    total = len(mineria_juego["participantes"])
    for _ in range(total):
        idx = mineria_juego["turno_actual_index"]
        jugador = mineria_juego["participantes"][idx]
        if mineria_juego["turnos_restantes"][jugador] > 0:
            bot.send_message(
                chat_id, 
                f"ㅤ୭ৎ ࣪ ׅ ㅤㅤ¡turno de @{jugador}!\nㅤ— ㅤㅤusa /minar para probar tu suerte.",
                message_thread_id=thread_id
            )
            return
        else:
            mineria_juego["turno_actual_index"] = (idx + 1) % total

    finalizar_mineria(chat_id)

@bot.message_handler(commands=['minar'])
def picar_mineria(message):
    chat_id, username = message.chat.id, (message.from_user.username if message.from_user.username else message.from_user.first_name)
    thread_id = get_thread_id(message)

    if mineria_juego["fase"] != "jugando" or chat_id != mineria_juego["chat_id"]:
        return

    idx = mineria_juego["turno_actual_index"]
    jugador_actual = mineria_juego["participantes"][idx]

    if username != jugador_actual:
        bot.send_message(chat_id, " (╥﹏╥)  no es tu turno de picar.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    mineria_juego["turnos_restantes"][username] -= 1

    eventos = [
        ("🪨 ¡Conseguiste una Piedrita brillante! (+100 minery points)", 100),
        ("🦪 ¡Encontraste una Perla marina! (+200 minery points)", 200),
        ("✨ ¡Picaste un Cristal reluciente! (+350 minery points)", 350),
        ("👑 ¡TESORO LEGENDARIO ENCONTRADO! (+500 minery points)", 500),
        ("🦇 Solo encontraste murciélagos asustados. (0 minery points)", 0)
    ]
    txt_evo, pts_ganados = random.choices(eventos, weights=[30, 25, 20, 10, 15])[0]

    mineria_juego["puntos"][username] = max(0, mineria_juego["puntos"][username] + pts_ganados)
    mineria_historico[username] = mineria_historico.get(username, 0) + max(0, pts_ganados)

    tot = mineria_juego["puntos"][username]

    bot.send_message(
        chat_id, 
        f"✦  @{username} picó en la mina...\n{txt_evo}\nTotal actual: **{tot} minery points**",
        parse_mode="Markdown",
        message_thread_id=thread_id
    )

    mineria_juego["turno_actual_index"] = (idx + 1) % len(mineria_juego["participantes"])
    time.sleep(3)
    notificar_turno_mineria(chat_id)

@bot.message_handler(commands=['endmineria'])
def forzar_fin_mineria(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes finalizar la minería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if mineria_juego["fase"] != "jugando":
        bot.send_message(chat_id, " (╥﹏╥)  no hay ninguna minería activa.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if mineria_juego["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    finalizar_mineria(chat_id)

def finalizar_mineria(chat_id):
    thread_id = mineria_juego["thread_id"]
    if not mineria_juego["puntos"]:
        bot.send_message(chat_id, " (╥﹏╥)  la minería terminó sin participación.", message_thread_id=thread_id)
        mineria_juego["fase"] = "inactivo"
        return

    max_pts = max(mineria_juego["puntos"].values())
    ganadores = [u for u, pts in mineria_juego["puntos"].items() if pts == max_pts]

    for g in ganadores:
        registrar_victoria(g)

    str_ganadores = ", ".join([f"@{g}" for g in ganadores])
    texto = (
        "ㅤㅤㅤㅤㅤ... ࣪ ׅ ㅤ¡Resultados!ㅤ\n\n"
        f"𓂃   premio  :  {mineria_juego['premio']}\n"
        f"𓂃   ganador/es  :  {str_ganadores} ({max_pts} pts)\n\n"
        f"ㅤㅤㅤᡣ𐭩ㅤ¡felicidades! reclama con @{bot.get_chat(mineria_juego['admin_id']).username or 'admin'}"
    )

    bot.send_message(chat_id, texto, message_thread_id=thread_id)
    mineria_juego["fase"] = "inactivo"

@bot.message_handler(commands=['bestminers', 'topminers'])
def mostrar_best_miners(message):
    thread_id = get_thread_id(message)
    if not mineria_historico:
        bot.send_message(message.chat.id, " (╥﹏╥)  aún no hay registros de minería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    ordenados = sorted(mineria_historico.items(), key=lambda x: x[1], reverse=True)[:10]
    lineas = [f"{idx:02d}  ;  @{u} ({pts} pts acumulados)" for idx, (u, pts) in enumerate(ordenados, start=1)]
    texto = "      ‿︵       𝘛𝘰𝘱 𝘔𝘪𝘯𝘦𝘳𝘴 !\n\n" + "\n".join(lineas)
    bot.send_message(message.chat.id, texto, message_thread_id=thread_id)

# --- CARRERA ANÓNIMA ---
@bot.message_handler(commands=['carrera'])
def crear_carrera(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar la carrera.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if carrera_juego["fase"] != "inactivo":
        bot.send_message(chat_id, " (╥﹏╥)  ya hay una carrera activa.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    premio = message.text[8:].strip()
    if not premio:
        bot.send_message(chat_id, "✦ Estructura incorrecta. Ejemplo: /carrera 100 robux", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

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

    texto = (
        "ㅤㅤ୭ৎ ࣪ ׅ ㅤㅤ 𝗰︩︪arrera anónima iniciada!\n\n"
        "(⌯ˇ- ˇ⌯)◜ nadie sabe quién es quién hasta que la partida finalice.\n"
        "ㅤ¡presiona el botón para unirte! admin, inicia la carrera con /carrerastart."
    )
    msg = bot.send_message(chat_id, texto, reply_markup=markup, message_thread_id=thread_id)
    carrera_juego["msg_lobby_id"] = msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "unirse_carrera_lobby")
def unirse_carrera_callback(call):
    if carrera_juego["fase"] != "lobby":
        bot.answer_callback_query(call.id, "La carrera ya no está disponible.", show_alert=True)
        return

    username = call.from_user.username if call.from_user.username else call.from_user.first_name
    usuarios_ids[username] = call.from_user.id

    if username in carrera_juego["participantes"]:
        bot.answer_callback_query(call.id, "Ya estás en la carrera.", show_alert=True)
        return

    carrera_juego["participantes"].append(username)
    bot.answer_callback_query(call.id, "¡Te has unido a la carrera!")

    bot.send_message(
        carrera_juego["chat_id"], 
        f"︵‌  @{username} se ha unido... ¿será el afortunado?   ₍˶ᵔ ˕ ᵔ˶₎", 
        message_thread_id=carrera_juego["thread_id"]
    )

@bot.message_handler(commands=['carrerastart'])
def iniciar_carrera_start(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar la carrera.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if carrera_juego["fase"] != "lobby":
        bot.send_message(chat_id, " (╥﹏╥)  no hay ningún lobby de carrera listo.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if carrera_juego["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if len(carrera_juego["participantes"]) < 2:
        bot.send_message(chat_id, " (╥﹏╥)  se necesitan al menos 2 participantes para la carrera.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    try:
        bot.edit_message_reply_markup(chat_id, carrera_juego["msg_lobby_id"], reply_markup=None)
    except Exception:
        pass

    carrera_juego["fase"] = "jugando"

    emojis_disponibles = random.sample(EMOJIS_CARRERA, len(carrera_juego["participantes"]))
    participantes_shuffled = list(carrera_juego["participantes"])
    random.shuffle(participantes_shuffled)

    for p, emoji in zip(participantes_shuffled, emojis_disponibles):
        carrera_juego["emojis_asignados"][p] = emoji
        carrera_juego["posiciones"][emoji] = 0

    texto_inicio = (
        "ㅤ ⪩⪨     ㅤ  ㅤ¡ Ɩa carrera ha iniciado !\n"
        "ㅤㅤ¿quién ganará? ¿quién soy? ¿quién es?\n"
        "ㅤㅤㅤㅤㅤ¡ es un misterio !    (⌯ˇ- ˇ⌯)"
    )
    bot.send_message(chat_id, texto_inicio, message_thread_id=thread_id)

    time.sleep(3)

    t = threading.Thread(target=ejecutar_animacion_carrera, args=(chat_id,))
    t.daemon = True
    t.start()

def renderizar_pista_carrera():
    meta = 20
    lineas = []
    for emoji in carrera_juego["posiciones"].keys():
        pos = carrera_juego["posiciones"][emoji]
        antes = " · " * pos
        despues = " · " * (meta - pos)
        lineas.append(f"{antes}{emoji}{despues}🏁")
    return "\n".join(lineas)

def ejecutar_animacion_carrera(chat_id):
    thread_id = carrera_juego["thread_id"]
    meta = 20

    texto_corran = (
        "ㅤㅤㅤㅤ ㅤ¡  𝗰︩︪ׄorran  !\n"
        + renderizar_pista_carrera()
    )
    msg = bot.send_message(chat_id, texto_corran, message_thread_id=thread_id)
    carrera_juego["msg_carrera_id"] = msg.message_id

    ganador_emoji = None
    llegadas_orden = []

    while not ganador_emoji:
        time.sleep(2.5)
        emojis_list = list(carrera_juego["posiciones"].keys())

        for emoji in emojis_list:
            if carrera_juego["posiciones"][emoji] < meta:
                avance = random.choice([0, 1, 2])
                carrera_juego["posiciones"][emoji] = min(meta, carrera_juego["posiciones"][emoji] + avance)
                if carrera_juego["posiciones"][emoji] == meta and emoji not in llegadas_orden:
                    llegadas_orden.append(emoji)

        if llegadas_orden:
            ganador_emoji = llegadas_orden[0]

        texto_pista = (
            "ㅤㅤㅤㅤ ㅤ¡  𝗰︩︪ׄorran  !\n"
            + renderizar_pista_carrera()
        )
        if ganador_emoji:
            texto_pista += "\nㅤ¡¡ㅤ(ˊᗜˋ*)ㅤㅤ¡tenemos a un ganador!"

        try:
            bot.edit_message_text(texto_pista, chat_id, carrera_juego["msg_carrera_id"])
        except Exception:
            pass

    time.sleep(2)
    bot.send_message(
        chat_id, 
        f"ㅤㅤ  ¡un anónimo ha cruzado la meta!\nㅤㅤ   ㅤ¿quién eres, {ganador_emoji}?", 
        message_thread_id=thread_id
    )

    time.sleep(3)

    for emoji in carrera_juego["posiciones"].keys():
        if emoji not in llegadas_orden:
            llegadas_orden.append(emoji)

    emoji_to_user = {v: k for k, v in carrera_juego["emojis_asignados"].items()}

    lineas_revelacion = []
    for idx, emoji in enumerate(llegadas_orden):
        u = emoji_to_user[emoji]
        if idx == 0:
            lineas_revelacion.append(f" ᜊ   ¡𝐆‌anador! {emoji} — @{u}")
            registrar_victoria(u)
        else:
            lineas_revelacion.append(f" ᜊ   {emoji}  — @{u}")

    texto_revelacion = (
        "ㅤㅤꔫ      ℛevelando identidades...\n\n"
        + "\n".join(lineas_revelacion)
    )
    bot.send_message(chat_id, texto_revelacion, message_thread_id=thread_id)
    carrera_juego["fase"] = "inactivo"

# --- LOTERÍA ---
@bot.message_handler(commands=['loteria'])
def crear_loteria(message):
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
        bot.send_message(chat_id, "✦ Estructura incorrecta. Ejemplo: /loteria 100 robux", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    loteria_juego["fase"] = "compras"
    loteria_juego["chat_id"] = chat_id
    loteria_juego["thread_id"] = thread_id
    loteria_juego["admin_id"] = user_id
    loteria_juego["premio"] = premio
    loteria_juego["tickets_vendidos"].clear()
    loteria_juego["usuarios_registrados"].clear()
    loteria_juego["reclamado"] = False

    texto = (
        "ㅤ୭ৎ ࣪ ׅ ㅤㅤ¡ha empezado la lotería!\n"
        f"prueba tu suerte comprando tus tickets, usa /tickets para recibir 5 oportunidades para ganar el premio mayor, {premio}."
    )
    time.sleep(3)
    bot.send_message(chat_id, texto, message_thread_id=thread_id)

@bot.message_handler(commands=['tickets'])
def comprar_tickets(message):
    chat_id, username = message.chat.id, (message.from_user.username if message.from_user.username else message.from_user.first_name)
    thread_id = get_thread_id(message)

    if loteria_juego["fase"] != "compras" or chat_id != loteria_juego["chat_id"]:
        return

    if username in loteria_juego["usuarios_registrados"]:
        bot.send_message(chat_id, f" (╥﹏╥)  @{username}, ya recibiste tus tickets de lotería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    loteria_juego["usuarios_registrados"].add(username)
    mis_tickets = []

    usados = set(loteria_juego["tickets_vendidos"].keys())
    while len(mis_tickets) < 5:
        num = f"CHERRY{random.randint(1000, 9999)}"
        if num not in usados and num not in mis_tickets:
            mis_tickets.append(num)
            loteria_juego["tickets_vendidos"][num] = username

    nickname_str = message.from_user.first_name

    listado_tickets = "\n".join([f" 𝅄   {t}" for t in mis_tickets])
    texto = (
        f"⠀ꕮ⠀ 𝑳ottery tickets for {nickname_str}.\n\n"
        f"{listado_tickets}"
    )
    bot.send_message(chat_id, texto, message_thread_id=thread_id)

@bot.message_handler(commands=['jugarloteria'])
def realizar_sorteo_loteria(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes sortear la lotería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if loteria_juego["fase"] != "compras":
        bot.send_message(chat_id, " (╥﹏╥)  no hay ninguna lotería en fase de tickets.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if loteria_juego["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if not loteria_juego["tickets_vendidos"]:
        bot.send_message(chat_id, " (╥﹏╥)  nadie compró tickets para esta lotería.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    ticket_ganador = random.choice(list(loteria_juego["tickets_vendidos"].keys()))
    ganador_user = loteria_juego["tickets_vendidos"][ticket_ganador]

    loteria_juego["ticket_ganador"] = ticket_ganador
    loteria_juego["ganador_esperado"] = ganador_user
    loteria_juego["tiempo_limite"] = time.time() + 45
    loteria_juego["fase"] = "esperando_reclamo"

    registrar_victoria(ganador_user)

    texto_anuncio = (
        "ㅤㅤᡣ𐭩ㅤㅤㅤresultados de la lotería cherrie . . .\n"
        f"         —         nuestro ticket ganador es el {ticket_ganador}.\n"
        "el ganador tiene 45 segundos para escribir ¡lotería! en el chat y asegurar su victoria."
    )

    bot.send_message(
        chat_id, 
        texto_anuncio,
        message_thread_id=thread_id
    )

    t = threading.Thread(target=temporizador_reclamo_loteria, args=(chat_id,))
    t.daemon = True
    t.start()

def temporizador_reclamo_loteria(chat_id):
    time.sleep(45)
    if loteria_juego["fase"] == "esperando_reclamo" and not loteria_juego["reclamado"]:
        thread_id = loteria_juego["thread_id"]
        ganador_fallido = loteria_juego['ganador_esperado']
        
        texto_no_reclamo = f"✦   @{ganador_fallido} no reclamó su lotería... (´๑•_•๑)"
        bot.send_message(
            chat_id, 
            texto_no_reclamo,
            message_thread_id=thread_id
        )
        loteria_juego["fase"] = "compras"
        
        usados = set(loteria_juego["tickets_vendidos"].keys())
        elegibles = [t for t in usados if loteria_juego["tickets_vendidos"][t] != ganador_fallido]
        if elegibles:
            nuevo_t = random.choice(elegibles)
            ganador_user = loteria_juego["tickets_vendidos"][nuevo_t]
            
            loteria_juego["ticket_ganador"] = nuevo_t
            loteria_juego["ganador_esperado"] = ganador_user
            loteria_juego["tiempo_limite"] = time.time() + 45
            loteria_juego["fase"] = "esperando_reclamo"

            registrar_victoria(ganador_user)

            texto_reintento = (
                "ㅤㅤᡣ𐭩ㅤㅤㅤresultados de la lotería cherrie . . .\n"
                f"         —         nuestro ticket ganador es el {nuevo_t}.\n"
                "el ganador tiene 45 segundos para escribir ¡lotería! en el chat y asegurar su victoria."
            )

            bot.send_message(
                chat_id, 
                texto_reintento,
                message_thread_id=thread_id
            )
            t2 = threading.Thread(target=temporizador_reclamo_loteria, args=(chat_id,))
            t2.daemon = True
            t2.start()
        else:
            bot.send_message(chat_id, " (╥﹏╥)  No quedan más participantes en la lotería.", message_thread_id=thread_id)
            loteria_juego["fase"] = "inactivo"

@bot.message_handler(func=lambda m: loteria_juego["fase"] == "esperando_reclamo")
def verificar_reclamo_loteria(message):
    username = message.from_user.username if message.from_user.username else message.from_user.first_name
    chat_id = message.chat.id
    thread_id = get_thread_id(message)

    if chat_id == loteria_juego["chat_id"] and username == loteria_juego["ganador_esperado"]:
        if message.text and message.text.strip().lower() == "¡lotería!":
            loteria_juego["reclamado"] = True
            loteria_juego["fase"] = "inactivo"

            texto = f"✦  ¡@{username}  es el ganador de la lotería! ha ganado {loteria_juego['premio']} ♡"
            bot.send_message(chat_id, texto, message_thread_id=thread_id)

# --- RED OR PINK ---
def generar_texto_lobby_redpink():
    participantes_str = "\n".join([f"        ⊹    @{p}" for p in redpink_juego["participantes"]]) if redpink_juego["participantes"] else "        ⊹    @"
    return (
        "ㅤ ⪩⪨     ㅤnueva partida de red or pink  .ᐟ\n\n"
        "   ⎯    𝗽︩︩︪articipantes     :\n"
        f"{participantes_str}\n\n"
        "₍˄..˄₎꠹     presiona el botón para poder hacer tu apuesta...\n"
        "admin, puedes colocar /redpinkstart para dar inicio a la partida."
    )

@bot.message_handler(commands=['redpink'])
def crear_redpink(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar red or pink.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if redpink_juego["fase"] != "inactivo":
        bot.send_message(chat_id, " (╥﹏╥)  ya hay una partida de Red or Pink en curso.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    premio = message.text[8:].strip()
    if not premio:
        bot.send_message(chat_id, "✦ Estructura incorrecta. Ejemplo: /redpink 100 robux", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    redpink_juego["fase"] = "lobby"
    redpink_juego["chat_id"] = chat_id
    redpink_juego["thread_id"] = thread_id
    redpink_juego["admin_id"] = user_id
    redpink_juego["premio"] = premio
    redpink_juego["participantes"].clear()
    redpink_juego["elecciones"].clear()

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("୭ৎㅤ𝗝𝗢𝗜𝗡!", callback_data="unirse_redpink_lobby"))

    time.sleep(3)
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
        bot.answer_callback_query(call.id, "Ya estás en la lista.", show_alert=True)
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
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes iniciar.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if redpink_juego["fase"] != "lobby":
        bot.send_message(chat_id, " (╥﹏╥)  no hay ningún lobby de Red or Pink listo.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if redpink_juego["admin_id"] != user_id:
        bot.send_message(chat_id, " (╥﹏╥)  solo el admin que inició la partida puede administrarla.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if not redpink_juego["participantes"]:
        bot.send_message(chat_id, " (╥﹏╥)  no hay participantes registrados.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
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
def procesar_comando_redpink(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)
    username = message.from_user.username if message.from_user.username else message.from_user.first_name

    if redpink_juego["fase"] != "apuestas" or chat_id != redpink_juego["chat_id"]:
        return

    if username not in redpink_juego["participantes"]:
        return

    if username in redpink_juego["elecciones"]:
        return

    comando = message.text.split()[0].lower()
    color = "RED" if "/red" in comando else "PINK"
    redpink_juego["elecciones"][username] = color

    bot.send_message(
        chat_id, 
        f"⸜(ˊᗜˋ*)⸝  ¡ℬuena elección! eres team {color.lower()}.", 
        message_thread_id=thread_id, 
        reply_to_message_id=message.message_id
    )

@bot.message_handler(commands=['redpinknow'])
def revelar_redpink(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin, no puedes revelar el resultado.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    if redpink_juego["fase"] != "apuestas":
        bot.send_message(chat_id, " (╥﹏╥)  no hay apuestas activas de Red or Pink.", message_thread_id=thread_id, reply_to_message_id=message.message_id)
        return

    for p in redpink_juego["participantes"]:
        if p not in redpink_juego["elecciones"]:
            redpink_juego["elecciones"][p] = random.choice(["RED", "PINK"])

    color_ganador = random.choice(["RED", "PINK"])
    ganadores = [u for u, c in redpink_juego["elecciones"].items() if c == color_ganador]

    for g in ganadores:
        registrar_victoria(g)

    sticker_mostrar = STICKER_RED if color_ganador == "RED" else STICKER_PINK
    try:
        bot.send_sticker(chat_id, sticker_mostrar, message_thread_id=thread_id)
    except Exception:
        pass

    time.sleep(2)

    str_ganadores = ", ".join([f"@{g}" for g in ganadores]) if ganadores else "nadie"
    texto_resumen = (
        "ㅤㅤㅤㅤㅤ... ࣪ ׅ ㅤ¡Resultados!ㅤ\n\n"
        f"𓂃   color ganador  :  {color_ganador}\n"
        f"𓂃   premio  :  {redpink_juego['premio']}\n"
        f"𓂃   ganador/es  :  {str_ganadores}\n\n"
        f"ㅤㅤㅤᡣ𐭩ㅤ¡felicidades! reclama con @{bot.get_chat(redpink_juego['admin_id']).username or 'admin'}"
    )

    bot.send_message(chat_id, texto_resumen, message_thread_id=thread_id)
    redpink_juego["fase"] = "inactivo"

# --- BUCLE DE BOT ---
if __name__ == "__main__":
    print("Bot Cherrie en ejecución...")
    bot.infinity_polling()
