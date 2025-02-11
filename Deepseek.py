import os
from dotenv import load_dotenv
import twitchio
from twitchio.ext import commands
import subprocess
import requests
from PIL import Image
import base64

load_dotenv()

# Configuración DeepSeek
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# Servicio de análisis de imágenes (usaremos PlantID API como ejemplo)
PLANT_API_URL = "https://api.plant.id/v2/identify"

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

def capture_frame():
    """Captura un frame del stream"""
    frame_path = "latest_frame.jpg"
    
    stream_process = subprocess.Popen(
        ["streamlink", f"https://www.twitch.tv/{CHANNEL_NAME}", "best", "-O"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    
    subprocess.run(
        ["ffmpeg", "-y", "-i", "pipe:0", "-vframes", "1", frame_path],
        stdin=stream_process.stdout, 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL
    )
    
    stream_process.stdout.close()
    stream_process.wait()
    
    return frame_path if os.path.exists(frame_path) else None

def analyze_plant_health(image_path):
    """Analiza la planta usando PlantID API"""
    with open(image_path, "rb") as img_file:
        img_base64 = base64.b64encode(img_file.read()).decode()
    
    response = requests.post(
        PLANT_API_URL,
        json={
            "images": [img_base64],
            "modifiers": ["similar_images"],
            "plant_details": ["health", "fruit"]
        },
        headers={
            "Content-Type": "application/json",
            "Api-Key": os.getenv("PLANT_API_KEY")
        }
    )
    
    return response.json()

def generate_plant_response(analysis):
    """Genera respuesta con personalidad usando DeepSeek"""
    try:
        # Construir el prompt
        health_status = analysis.get('health', {}).get('status', 'desconocido')
        diseases = ", ".join(analysis.get('diseases', [])) or "ninguna detectada"
        fruits = analysis.get('fruit', {}).get('presence', False)
        
        prompt = f"""
        Eres una planta sarcástica en un stream de Twitch. Analiza esta información y genera una respuesta divertida:
        - Estado de salud: {health_status}
        - Enfermedades detectadas: {diseases}
        - Presencia de frutos: {'Sí' if fruits else 'No'}
        
        Respuesta en máximo 2 líneas, usa emojis vegetales y sé creativo.
        """
        
        # Configurar la solicitud a la API
        headers = {
            "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": DEEPSEEK_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.9,
            "max_tokens": 150
        }
        
        # Hacer la solicitud con timeout
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=data,
            timeout=10  # Añadir timeout para evitar bloqueos
        )
        
        # Verificar el código de estado HTTP
        response.raise_for_status()
        
        # Parsear la respuesta
        response_data = response.json()
        
        # Debug: mostrar respuesta completa
        print(f"[DEBUG] Respuesta de DeepSeek API: {json.dumps(response_data, indent=2)}")
        
        # Verificar estructura de la respuesta
        if 'choices' not in response_data or len(response_data['choices']) == 0:
            raise ValueError("Estructura de respuesta inválida: falta 'choices'")
            
        return response_data['choices'][0]['message']['content']
        
    except requests.exceptions.HTTPError as e:
        print(f"Error HTTP: {e.response.status_code}")
        print(f"Respuesta del error: {e.response.text}")
        return "¡Ups! Mis raíces no alcanzan el servidor... 🌿📡"
        
    except requests.exceptions.Timeout:
        print("Error: Timeout al conectar con DeepSeek")
        return "¡El servidor está más lento que mi fotosíntesis! 🌿⏳"
        
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión: {str(e)}")
        return "¡Problemas de conexión en mi red de raíces! 🌿📶"
        
    except (KeyError, ValueError) as e:
        print(f"Error procesando respuesta: {str(e)}")
        return "¡Algo salió mal procesando mi savia digital! 🌿💻"
        
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        return "¡Ups! Mis hojas están bloqueando la conexión... 🌿💻"
    
def analyze_frame():
    if not is_stream_live():
        return generate_plant_response({'health': {'status': 'offline'}})
    
    frame_path = capture_frame()
    if not frame_path:
        return "Error capturando mi mejor ángulo... 📸🌱"
    
    analysis = analyze_plant_health(frame_path)
    return generate_plant_response(analysis)

# Configurar el bot de Twitch
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=os.getenv("TWITCH_OAUTH_TOKEN"),
            client_id=os.getenv("TWITCH_CLIENT_ID"),
            prefix="!",
            initial_channels=[CHANNEL_NAME]
        )

    async def event_message(self, message):
        if message.author is None:
            return

        response = analyze_frame()
        await message.channel.send(response[:400])  # Asegurar límite de Twitch

# Iniciar el bot
bot = Bot()
bot.run()