import os
import time
import tempfile
import requests
from datetime import datetime, timedelta

from openai import AsyncOpenAI
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🔐 Clés d’API
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
GOOGLE_DIRECTIONS_API_KEY = os.getenv("GOOGLE_DIRECTIONS_API_KEY")

# 🧠 Assistant ID global
ASSISTANT_ID = None

# 🔍 Brave Search
def search_web(query: str) -> str:
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    params = {"q": query, "count": 3}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        results = response.json().get("web", {}).get("results", [])
        if not results:
            return "Aucun résultat trouvé."
        return "\n\n".join([f"{r['title']} - {r['url']}\n{r['description']}" for r in results])
    return "Erreur lors de la recherche web."

# 🌦️ Météo
def get_weather(city: str) -> str:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "lang": "fr",
        "units": "metric"
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return "Je n'ai pas pu obtenir la météo actuellement."
    data = response.json()
    temp = round(data["main"]["temp"])
    feels_like = round(data["main"]["feels_like"])
    desc = data["weather"][0]["description"]
    return f"Aujourd'hui, à {city}, il fait {desc}, {temp}°C ressentis {feels_like}°C."

# 📅 Google Calendar
def add_event_to_calendar(summary: str, start_time: str, duration_minutes: int = 60) -> str:
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    try:
        service = build("calendar", "v3", credentials=creds)
        start_dt = datetime.fromisoformat(start_time)
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event = {
            "summary": summary,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Brussels"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Brussels"},
        }

        created = service.events().insert(calendarId="primary", body=event).execute()
        return f"Événement '{summary}' ajouté le {start_dt.strftime('%d/%m/%Y à %H:%M')}."
    except Exception as e:
        print("Erreur ajout événement:", e)
        return "Erreur lors de l'ajout de l'événement."

def get_upcoming_events(max_results=5) -> str:
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    try:
        service = build("calendar", "v3", credentials=creds)
        now = datetime.utcnow().isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return "Aucun événement à venir."

        message = "Voici vos prochains événements :\n"
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            message += f"• {event.get('summary', '(Sans titre)')} à {start}\n"

        return message.strip()
    except Exception as e:
        print("Erreur lecture événements:", e)
        return "Erreur lors de la récupération des événements."

def get_today_events() -> str:
    creds = Credentials(
        None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
    )

    try:
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.utcnow().isoformat() + 'Z'
        end_of_day = (datetime.utcnow() + timedelta(hours=24)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return "Tu n'as aucun événement prévu aujourd'hui."

        result = "Voici tes événements pour aujourd'hui :\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'Sans titre')
            heure = start[11:16] if 'T' in start else "toute la journée"
            result += f"- {summary} à {heure}\n"

        return result

    except Exception as e:
        print("Erreur Google Calendar :", e)
        return "Je n'ai pas pu récupérer tes événements pour aujourd'hui."
    
# Google Maps Directions avec coordonnées
def get_directions_from_coords(lat: float, lng: float, destination: str, mode: str = "walking") -> tuple:
    origin = f"{lat},{lng}"
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "language": "fr",
        "key": GOOGLE_DIRECTIONS_API_KEY,
    }

    print("📤 Requête Google Maps avec :")
    print("  ➤ origin:", origin)
    print("  ➤ destination:", destination)
    print("  ➤ mode:", mode)

    response = requests.get(url, params=params)
    data = response.json()

    # Log status
    print("📥 Réponse Google Maps - status:", data.get("status"))
    if "error_message" in data:
        print("🛑 Erreur Google Maps:", data["error_message"])

    if data.get("status") != "OK" or not data.get("routes"):
        return ("Je n’ai pas pu obtenir l’itinéraire.", None)

    try:
        leg = data["routes"][0]["legs"][0]
        summary = (
            f"Depuis votre position actuelle jusqu’à {leg['end_address']}, "
            f"il faut environ {leg['duration']['text']} pour parcourir {leg['distance']['text']}."
        )
        maps_url = (
            f"https://www.google.com/maps/dir/?api=1&origin={origin}"
            f"&destination={destination}&travelmode={mode}"
        )
        return (summary, maps_url)
    except Exception as e:
        print("⚠️ Erreur lors de l'analyse des données Google Maps:", e)
        return ("Je n’ai pas pu interpréter l’itinéraire.", None)




# 📚 Fonctions accessibles par GPT
search_web_function = {
    "name": "search_web",
    "description": "Effectue une recherche web avec Brave Search.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Question ou sujet à rechercher"}
        },
        "required": ["query"]
    }
}

weather_function = {
    "name": "get_weather",
    "description": "Donne la météo actuelle pour une ville.",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "Nom de la ville"}
        },
        "required": ["city"]
    }
}

calendar_add_function = {
    "name": "add_event_to_calendar",
    "description": "Ajoute un événement dans le Google Calendar de l'utilisateur.",
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Titre de l'événement"},
            "start_time": {
                "type": "string",
                "description": "Date et heure ISO ex: 2024-06-10T14:00"
            },
            "duration_minutes": {
                "type": "integer",
                "description": "Durée en minutes (par défaut 60)",
                "default": 60
            }
        },
        "required": ["summary", "start_time"]
    }
}

calendar_read_function = {
    "name": "get_upcoming_events",
    "description": "Récupère les événements à venir dans le calendrier Google.",
    "parameters": {
        "type": "object",
        "properties": {
            "max_results": {
                "type": "integer",
                "description": "Nombre d'événements à récupérer (par défaut 5)",
                "default": 5
            }
        }
    }
}

calendar_get_function = {
    "name": "get_today_events",
    "description": "Récupère les événements du jour dans l’agenda Google Calendar connecté.",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

get_directions_function = {
    "name": "get_directions",
    "description": "Fournit un itinéraire à pied, en voiture ou en transport.",
    "parameters": {
        "type": "object",
        "properties": {
            "origin": {
                "type": "string",
                "description": "Adresse de départ (ex: Rue Albert 12, Mons)"
            },
            "destination": {
                "type": "string",
                "description": "Adresse ou lieu d’arrivée (ex: Gare de Mons)"
            },
            "mode": {
                "type": "string",
                "enum": ["walking", "driving", "transit"],
                "description": "Mode de transport (défaut: à pied)",
                "default": "walking"
            }
        },
        "required": ["origin", "destination"]
    }
}




# 🧠 Mémoire de conversation
conversation = [
    {"role": "system", "content": "Tu es Alto, un assistant vocal intelligent, connecté et utile."}
]

# 💬 Dialogue principal
async def ask_gpt(prompt, lat=None, lng=None):
    from app.utils import (
        search_web_function, weather_function, calendar_add_function,
        calendar_read_function, calendar_get_function, get_directions_function,
        search_web, get_weather, add_event_to_calendar, get_upcoming_events,
        get_today_events, get_directions_from_coords
    )

    conversation.append({"role": "user", "content": prompt})
    maps_url = None

    # 🔍 Détection manuelle d'intention de déplacement
    keywords = ["je veux aller", "je dois aller", "emmène-moi", "rends-toi", "direction", "aller à", "je vais à", "me rendre à"]
    if any(k in prompt.lower() for k in keywords) and lat is not None and lng is not None:
        # 🧠 GPT utilisé uniquement pour extraire la destination proprement
        destination_query = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Tu es un extracteur de destination. Rends simplement le lieu vers lequel l'utilisateur veut aller."},
                {"role": "user", "content": prompt}
            ]
        )
        destination = destination_query.choices[0].message.content.strip()
        print("📍 Destination extraite :", destination)
        summary, maps_url = get_directions_from_coords(lat, lng, destination)
        return {
            "text": "Ok, c’est parti !",
            "maps_url": maps_url
        }

    # 🤖 Sinon, requête GPT standard
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=conversation,
        functions=[
            search_web_function,
            weather_function,
            calendar_add_function,
            calendar_read_function,
            calendar_get_function,
            get_directions_function
        ],
        function_call="auto"
    )

    message = response.choices[0].message

    if message.function_call:
        name = message.function_call.name
        args = eval(message.function_call.arguments)

        if name == "search_web":
            result = search_web(args["query"])
        elif name == "get_weather":
            result = get_weather(args["city"])
        elif name == "add_event_to_calendar":
            result = add_event_to_calendar(
                args["summary"],
                args["start_time"],
                args.get("duration_minutes", 60)
            )
        elif name == "get_upcoming_events":
            result = get_upcoming_events(args.get("max_results", 5))
        elif name == "get_today_events":
            result = get_today_events()
        elif name == "get_directions":
            if lat is not None and lng is not None:
                result, maps_url = get_directions_from_coords(lat, lng, args["destination"], args.get("mode", "walking"))
                result = "Ok, c’est parti !"
            else:
                result = "Je n’ai pas pu obtenir votre position."
        else:
            result = "Fonction non reconnue."

        conversation.append({
            "role": "function",
            "name": name,
            "content": result
        })

        followup = await client.chat.completions.create(
            model="gpt-4o",
            messages=conversation
        )
        answer = followup.choices[0].message.content.strip()
        conversation.append({"role": "assistant", "content": answer})
        return {
            "text": result if maps_url else answer,
            "maps_url": maps_url
        }

    answer = message.content.strip()
    conversation.append({"role": "assistant", "content": answer})
    return {"text": answer}




# 🎤 Transcription
async def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        transcript = await client.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )
    return transcript.text

# 🔊 TTS
async def synthesize_speech(text):
    speech = await client.audio.speech.create(
        model="tts-1",
        voice="shimmer",
        input="Hum... " + text
    )
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file.write(speech.content)
    return temp_file.name
