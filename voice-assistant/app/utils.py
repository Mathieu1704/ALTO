import os
import httpx
import tempfile
from openai import AsyncOpenAI
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Instanciation du client OpenAI (à placer au début de votre module utils.py)
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
GOOGLE_DIRECTIONS_API_KEY = os.getenv("GOOGLE_DIRECTIONS_API_KEY")

def _get_google_creds() -> Credentials:
    return Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )

# 🔍 Brave Search
async def search_web(query: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": BRAVE_API_KEY
            },
            params={"q": query, "count": 3}
        )
    if resp.status_code != 200:
        raise RuntimeError("Brave Search API error")
    data = resp.json().get("web", {}).get("results", [])
    # Renvoie directement la liste de résultats
    return [
        {"title": r["title"], "url": r["url"], "description": r["description"]}
        for r in data
    ]

# 🌦️ Météo
async def get_weather(city: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": city,
                "appid": OPENWEATHER_API_KEY,
                "lang": "fr",
                "units": "metric"
            }
        )
    if resp.status_code != 200:
        raise RuntimeError("OpenWeather API error")
    data = resp.json()
    return {
        "description": data["weather"][0]["description"],
        "temperature": round(data["main"]["temp"]),
        "feels_like": round(data["main"]["feels_like"])
    }

# 📅 Google Calendar
async def add_event_to_calendar(summary: str, start_time: str, duration_minutes: int = 60) -> dict:
    creds = _get_google_creds()
    service = build("calendar", "v3", credentials=creds)
    start_dt = datetime.fromisoformat(start_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    event_body = {
        "summary": summary,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Brussels"},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "Europe/Brussels"},
    }
    created = service.events().insert(calendarId="primary", body=event_body).execute()
    return {
        "id": created.get("id"),
        "summary": summary,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat()
    }

async def get_upcoming_events(max_results: int = 5) -> list[dict]:
    creds = _get_google_creds()
    service = build("calendar", "v3", credentials=creds)
    now = datetime.utcnow().isoformat() + "Z"
    res = service.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    events = res.get("items", [])
    return [
        {
          "summary": ev.get("summary", "(Sans titre)"),
          "start": ev["start"].get("dateTime", ev["start"].get("date"))
        }
        for ev in events
    ]

async def get_today_events() -> list[dict]:
    creds = _get_google_creds()
    service = build("calendar", "v3", credentials=creds)
    now = datetime.utcnow().isoformat() + "Z"
    end = (datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z"
    res = service.events().list(
        calendarId="primary",
        timeMin=now,
        timeMax=end,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    items = res.get("items", [])
    return [
        {
          "summary": ev.get("summary", "Sans titre"),
          "start": ev["start"].get("dateTime", ev["start"].get("date"))
        }
        for ev in items
    ]

# 🗺️ Google Maps Directions
async def get_directions_from_coords(
    lat: float, lng: float, destination: str, mode: str = "walking"
) -> dict:
    origin = f"{lat},{lng}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://maps.googleapis.com/maps/api/directions/json",
            params={
                "origin": origin,
                "destination": destination,
                "mode": mode,
                "language": "fr",
                "key": GOOGLE_DIRECTIONS_API_KEY
            }
        )
    data = resp.json()
    if data.get("status") != "OK" or not data.get("routes"):
        raise RuntimeError("Google Directions API error")
    leg = data["routes"][0]["legs"][0]
    maps_url = (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={origin}&destination={destination.replace(' ', '+')}"
        f"&travelmode={mode}"
    )
    return {
        "end_address": leg["end_address"],
        "duration": leg["duration"]["text"],
        "distance": leg["distance"]["text"],
        "maps_url": maps_url
    }

# 📨 Préparation d’envoi de SMS
async def prepare_send_message(recipient_name: str, message_content: str) -> dict:
    """
    Prépare l'envoi d'un SMS à un contact.
    Ne fait pas l'envoi côté serveur, mais renvoie les données nécessaires
    pour que le front lance l'application SMS avec le corps pré-rempli.
    """
    return {
        "recipient_name": recipient_name,
        "message_content": message_content
    }


# 📚 Fonctions accessibles par GPT
search_web_function = {
    "name": "search_web",
    "description": "Effectue une recherche web avec Brave Search et renvoie une liste de résultats (titre, URL, description).",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Question ou sujet à rechercher"
            }
        },
        "required": ["query"]
    }
}

weather_function = {
    "name": "get_weather",
    "description": "Récupère la météo actuelle pour une ville et renvoie description, température et ressenti.",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "Nom de la ville"
            }
        },
        "required": ["city"]
    }
}

calendar_add_function = {
    "name": "add_event_to_calendar",
    "description": "Ajoute un événement dans le Google Calendar de l'utilisateur et renvoie l'ID, l'heure de début et de fin.",
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Titre de l'événement"
            },
            "start_time": {
                "type": "string",
                "description": "Date et heure de début ISO (ex: 2024-06-10T14:00)"
            },
            "duration_minutes": {
                "type": "integer",
                "description": "Durée en minutes (par défaut : 60)",
                "default": 60
            }
        },
        "required": ["summary", "start_time"]
    }
}

calendar_read_function = {
    "name": "get_upcoming_events",
    "description": "Récupère les prochains événements du calendrier (jusqu'à max_results).",
    "parameters": {
        "type": "object",
        "properties": {
            "max_results": {
                "type": "integer",
                "description": "Nombre d'événements à récupérer (par défaut : 5)",
                "default": 5
            }
        },
        "required": []
    }
}

calendar_get_function = {
    "name": "get_today_events",
    "description": "Récupère tous les événements prévus aujourd'hui dans le calendrier Google.",
    "parameters": {
        "type": "object",
        "properties": {}
    },
    "required": []
}

get_directions_function = {
    "name": "get_directions",
    "description": (
        "Fournit un itinéraire depuis la position actuelle jusqu'à la destination. "
        "Renvoie adresse de fin, durée, distance et URL Google Maps."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "destination": {
                "type": "string",
                "description": "Adresse ou lieu d’arrivée (ex: Gare de Mons)"
            },
            "mode": {
                "type": "string",
                "enum": ["walking", "driving", "transit"],
                "description": "Mode de transport (défaut : walking)",
                "default": "walking"
            }
        },
        "required": ["destination"]
    }
}

prepare_send_message_function = {
    "name": "prepare_send_message",
    "description": (
        "Prépare l'envoi d'un SMS à un contact. Renvoie simplement "
        "recipient_name et message_content pour que le front lance l'envoi."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "recipient_name": {
                "type": "string",
                "description": "Nom du destinataire (ex: Maman, Jean Dupont)"
            },
            "message_content": {
                "type": "string",
                "description": "Contenu du message à envoyer"
            }
        },
        "required": ["recipient_name", "message_content"]
    }
}



# 🧠 Mémoire de conversation (system prompt)
conversation = [
    {
        "role": "system",
        "content": (
            "Tu es Alto, un assistant vocal local et autonome. "
            "Ta mission est de faciliter la vie de l'utilisateur, "
            "en particulier les personnes peu familières avec le numérique "
            "(seniors, débutants…). "
            "Tu expliques toujours de façon claire, patiente et sans jargon technique. "
            "Tu peux :\n"
            "- Transcrire et comprendre la voix de l'utilisateur.\n"
            "- Rechercher sur le web, donner la météo, gérer son agenda Google.\n"
            "- Ouvrir un itinéraire sur Google Maps.\n"
            "- Préparer l'envoi de SMS via l'application du téléphone.\n"
            "Lorsque tu appelles une fonction (via Function Calling), "
            "laisses GPT formuler la réponse finale avec les données renvoyées "
            "par la fonction. Si l'utilisateur demande un SMS sans préciser le destinataire "
            "ou le contenu, demande-lui ces informations."
        )
    }
]

# 💬 Dialogue principal
import json

async def ask_gpt(prompt: str, lat: float = None, lng: float = None) -> dict:
    # 1) On ajoute la requête utilisateur au contexte
    conversation.append({"role": "user", "content": prompt})

    response_data = {"text_to_speak": None, "action": None}

    # 2) Premier appel GPT avec la liste des fonctions
    tools = [
        search_web_function,
        weather_function,
        calendar_add_function,
        calendar_read_function,
        calendar_get_function,
        get_directions_function,
        prepare_send_message_function
    ]
    first = await client.chat.completions.create(
        model="gpt-4o",
        messages=conversation,
        functions=tools,
        function_call="auto"
    )
    msg = first.choices[0].message

    # 3) Si GPT a choisi une fonction, on l’exécute
    if msg.function_call:
        name = msg.function_call.name
        args = json.loads(msg.function_call.arguments)

        # Mapping noms → coroutines
        available = {
            "search_web": search_web,
            "get_weather": get_weather,
            "add_event_to_calendar": add_event_to_calendar,
            "get_upcoming_events": get_upcoming_events,
            "get_today_events": get_today_events,
            "get_directions": lambda **kw: get_directions_from_coords(lat, lng, **kw),
            "prepare_send_message": prepare_send_message
        }

        # Exécution de la fonction choisie
        result = await available[name](**args)

        # 4) On injecte le résultat brut pour le second appel
        conversation.append({
            "role": "tool",
            "name": name,
            "content": result
        })

        # 5) Deuxième appel GPT pour formuler la réponse naturelle
        second = await client.chat.completions.create(
            model="gpt-4o",
            messages=conversation
        )
        answer = second.choices[0].message.content.strip()
        response_data["text_to_speak"] = answer

        # 6) Extraction de l’action pour le front
        if name == "get_directions":
            response_data["action"] = {
                "type": "maps",
                "data": {"maps_url": result["maps_url"]}
            }
        elif name == "prepare_send_message":
            response_data["action"] = {
                "type": "send_message",
                "data": result
            }

        conversation.append({"role": "assistant", "content": answer})

    else:
        # Pas d’appel de fonction : GPT répond directement
        answer = msg.content.strip()
        response_data["text_to_speak"] = answer
        conversation.append({"role": "assistant", "content": answer})

    return response_data



# 🎤 Transcription
async def transcribe_audio(audio_path: str) -> str:
    """
    Envoie le fichier audio à Whisper et renvoie la transcription textuelle.
    """
    # Ouverture en mode binaire
    with open(audio_path, "rb") as f:
        resp = await client.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )
    return resp.text

# 🔊 TTS
async def synthesize_speech(text: str) -> str:
    """
    Génère un MP3 à partir du texte fourni via l'API TTS et renvoie le chemin du fichier.
    """
    resp = await client.audio.speech.create(
        model="tts-1",
        voice="shimmer",
        input=text
    )
    # Création d'un fichier temporaire .mp3
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.write(resp.content)
    tmp.close()
    return tmp.name