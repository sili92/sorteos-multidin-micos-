import telebot
from telebot import types
import random
import threading
import time
import os

TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

sorteos = {}

def get_thread_id(message):
    return message.message_thread_id if message.is_topic_message else None

# --- FUNCIONES AUXILIARES OBLIGATORIAS ---
def generar_texto_sorteo(premio, minutos_restantes, ganadores):
    return f"🎉 **¡SORTEO ACTIVO!**\n\n🏆 Premio: {premio}\n⏳ Quedan: {minutos_restantes} min\n👤 Ganadores: {ganadores}"

def generar_texto_resultados(premio, ganadores_str):
    return f"🎊 **¡RESULTADOS DEL SORTEO!**\n\n🏆 Premio: {premio}\n👑 Ganador/es: {ganadores_str}"

def ejecutar_fin_sorteo(chat_id):
    if chat_id not in sorteos or not sorteos[chat_id]["activo"]:
        return
    datos = sorteos[chat_id]
    datos["activo"] = False
    
    if not datos["participantes"]:
        bot.send_message(chat_id, " (╥﹏╥) El sorteo terminó sin participantes.")
        return

    elegibles = list(datos["participantes"])
    ganador = random.choice(elegibles)
    datos["ganadores_anteriores"].append(ganador)
    
    bot.send_message(chat_id, generar_texto_resultados(datos["premio"], f"@{ganador}"))

# --- COMANDO RESORTEO ---
@bot.message_handler(commands=['resorteo'])
def resortear(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)

    if chat_id not in sorteos or not sorteos[chat_id]["participantes"]:
        bot.send_message(chat_id, " (╥﹏╥)  no hay un sorteo reciente para volver a sortear.", message_thread_id=thread_id)
        return

    datos = sorteos[chat_id]
    elegibles = [p for p in datos["participantes"] if p not in datos["ganadores_anteriores"]]
    
    if not elegibles:
        bot.send_message(chat_id, " (╥﹏╥)  no quedan más participantes disponibles.", message_thread_id=thread_id)
        return

    bot.send_message(chat_id, "(๑´`๑)  ¡eligiendo nuevo ganador!", message_thread_id=thread_id)
    time.sleep(2)

    nuevo_ganador = random.choice(elegibles)
    datos["ganadores_anteriores"].append(nuevo_ganador)
    bot.send_message(chat_id, generar_texto_resultados(datos["premio"], f"@{nuevo_ganador}"), message_thread_id=thread_id)

# --- MONITOR EN SEGUNDO PLANO ---
def monitor_sorteos():
    while True:
        try:
            ahora = time.time()
            for chat_id, datos in list(sorteos.items()):
                if datos.get("activo") and datos.get("tiempo_fin"):
                    if ahora >= datos["tiempo_fin"]:
                        ejecutar_fin_sorteo(chat_id)
        except Exception as e:
            print(f"Error en monitor: {e}")
        time.sleep(10)

hilo_monitor = threading.Thread(target=monitor_sorteos, daemon=True)
hilo_monitor.start()

# --- ARRANQUE 24/7 ---
if __name__ == '__main__':
    bot.infinity_polling()
