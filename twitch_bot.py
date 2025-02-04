import os
from dotenv import load_dotenv
import twitchio
from twitchio.ext import commands
import subprocess
import google.generativeai as genai
from PIL import Image
import requests

load_dotenv()

# Configurar Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")


# Nombre del canal de Twitch
CHANNEL_NAME = os.getenv("TWITCH_CHANNEL")

def is_stream_live():
    """Verifica si el canal de Twitch está transmitiendo en vivo."""
    url = f"https://api.twitch.tv/helix/streams?user_login={CHANNEL_NAME}"
    headers = {
        "Client-ID": os.getenv("TWITCH_CLIENT_ID"),
        "Authorization": f"Bearer {os.getenv('TWITCH_OAUTH_TOKEN')}",
    }
    
    response = requests.get(url, headers=headers)
    data = response.json()
    
    return bool(data.get("data"))

def analyze_frame():
    """Captura un frame del stream y lo analiza con Gemini."""
    frame_path = "latest_frame.jpg"

    if not is_stream_live():
        # Gemini responde con sarcasmo si el canal no está en vivo
        response = model.generate_content(
            "Responde como si fueras una planta sarcástica y graciosa que se queja porque el canal no está en directo. "
            "Máximo 200 caracteres."
        )
        return response.text if response and response.text else "Oh, genial. Aquí estoy, fotosintetizando en la oscuridad. 🌿"

    # Capturar stream con streamlink y ffmpeg
    stream_process = subprocess.Popen(
        ["streamlink", f"https://www.twitch.tv/{CHANNEL_NAME}", "best", "-O"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", "pipe:0", "-vframes", "1", frame_path],
        stdin=stream_process.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    stream_process.stdout.close()
    stream_process.wait()

    if not os.path.exists(frame_path):
        return "Parece que algo salió mal al capturar la imagen... 🌿"

    img = Image.open(frame_path)
    response = model.generate_content([
        "Describe lo que ocurre en esta imagen de un stream de Twitch. "
        "Responde como si fueras una planta sarcástica y graciosa. Máximo 200 caracteres.", 
        img
    ])

    return response.text if response and response.text else "No tengo ni idea de qué acabo de ver, pero seguro que es arte. 🌱"

# Configurar el bot de Twitch
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=os.getenv("TWITCH_OAUTH_TOKEN"),
            client_id=os.getenv("TWITCH_CLIENT_ID"),
            prefix="!",
            initial_channels=[CHANNEL_NAME]  # Corregido: initial_channels debe ser una lista
        )

    async def event_message(self, message):
        if message.author is None:
            return

        response = analyze_frame()
        await message.channel.send(response)

# Iniciar el bot
bot = Bot()
bot.run()
