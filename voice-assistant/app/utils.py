import os
import httpx
import tempfile
from openai import AsyncOpenAI
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json

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

# 🔮 Prévisions météo (3 h / 5 jours)
async def get_weather_forecast(city: str, days_ahead: int = 1) -> dict:
    """
    Utilise l'API 5-day/3-hour forecast d'OpenWeather.
    days_ahead = 1 → prévision la plus proche de maintenant + 24 h.
    Renvoie un dict avec date, heure, température, ressenti et description.
    """
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "lang": "fr",
        "units": "metric"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
    if resp.status_code != 200:
        raise RuntimeError("OpenWeather forecast API error")
    data = resp.json()

    # Calculer l'heure cible : maintenant + (days_ahead * 24 h)
    target_dt = datetime.utcnow() + timedelta(days=days_ahead)
    # Trouver l'entrée de forecast la plus proche de target_dt
    best = min(
        data["list"],
        key=lambda e: abs(
            datetime.fromisoformat(e["dt_txt"]) - target_dt
        )
    )
    return {
        "date": best["dt_txt"].split(" ")[0],
        "time": best["dt_txt"].split(" ")[1],
        "temp": round(best["main"]["temp"]),
        "feels_like": round(best["main"]["feels_like"]),
        "description": best["weather"][0]["description"]
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

# 📱 Appel
async def prepare_call_contact(recipient_name: str) -> dict:
    """
    Prépare un appel téléphonique à un contact.
    Ne fait pas l'envoi côté serveur, mais renvoie les données nécessaires
    pour que le front lance l'application SMS avec le corps pré-rempli.
    """
    return { "recipient_name": recipient_name }

#  📷 Ouvrir l’appareil photo
async def prepare_open_camera() -> dict:
    """Prépare l’ouverture de l’appareil photo."""
    return {}          # rien à renvoyer, le front sait quoi faire

# 📱 Ouvrir une application
async def prepare_open_app(app_name: str) -> dict:
    """
    Prépare l’ouverture d’une application installée sur le téléphone.
    L’argument app_name est un nom “humain” (YouTube, WhatsApp…).
    """
    return {"app_name": app_name}

# 📅 Lire le calendrier natif
async def read_local_calendar(period: str) -> dict:
    """
    Stub côté serveur : renvoie simplement la période demandée.
    Le vrai accès au calendrier se fait dans l’app (Expo Calendar).
    """
    return {"period": period}



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

forecast_function = {
    "name": "get_weather_forecast",
    "description": (
        "Donne la prévision météo pour une ville X jours à l'avance "
        "en utilisant l'API OpenWeather 5 jours/3 heures."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "Nom de la ville (ex: Paris)"
            },
            "days_ahead": {
                "type": "integer",
                "description": "Nombre de jours à l'avance (1 = demain)",
                "default": 1
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
        "Avant de préréparer l'envoi d'un SMS, "
        "vérifie que l'utilisateur a un contact correspondant. "
        "si il y a plusieurs contacts avec le même nom, "
        "demande-lui de choisir lequel. "
        "Prépare l'envoi d'un SMS à un contact. "
        "Appelle-la dès que tu connais le destinataire, "
        "même si le texte du message est encore inconnu."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "recipient_name": {
                "type": "string",
                "description": "Nom ou surnom du destinataire (ex: Maman, Didier)"
            },
            "message_content": {
                "type": "string",
                "description": (
                    "Contenu du message. Doit être NON vide quand tu connais le texte. "
                    "Si l'utilisateur ne l'a pas encore donné, passe simplement une chaîne vide."
                ),
                "default": ""    
            }
        },
        "required": ["recipient_name"] 
    }
}

prepare_call_contact_function = {
    "name": "prepare_call_contact",
    "description": (
        "Prépare un appel téléphonique à un contact. "
        "Appelle-la dès que tu connais le NOM du destinataire."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "recipient_name": {
                "type": "string",
                "description": "Nom ou surnom du destinataire (ex : Papa)"
            }
        },
        "required": ["recipient_name"]
    }
}

prepare_open_camera_function = {
    "name": "prepare_open_camera",
    "description": "Ouvre l'appareil photo du téléphone pour prendre une photo.",
    "parameters": { "type": "object", "properties": {} , "required": [] }
}

open_app_function = {
    "name": "prepare_open_app",
    "description": "Ouvre une application installée sur l'appareil de l'utilisateur (YouTube, Facebook, Spotify…).",
    "parameters": {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": "Nom de l'application à ouvrir (ex: YouTube)"
            }
        },
        "required": ["app_name"]
    }
}

read_local_calendar_function = {
    "name": "read_local_calendar",
    "description": (
        "Demande au téléphone de lire les événements du calendrier natif "
        "(iOS/Android) pour une période donnée."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "period": {
                "type": "string",
                "description": (
                    "Période en langage naturel : "
                    "aujourd'hui, demain, cette semaine, ce week-end, semaine prochaine."
                )
            }
        },
        "required": ["period"]
    }
}





# 🧠 Mémoire de conversation (system prompt)
conversation = [
    {
        "role": "system",
        "content": (
            "Tu es Alto, un assistant vocal local et autonome. "
            "Ta mission est d'aider l'utilisateur, surtout les personnes peu à l'aise avec le numérique. "
            "Tu expliques de façon claire, patiente et sans jargon.\n\n"
            "CAPACITÉS  ▸  Transcription vocale, recherche web, météo, agenda Google, itinéraires Google Maps, "
            "préparation d'envoi de SMS, preparation d'appel téléphonique, ouvrir l'appareil photo.\n\n"
            "RÈGLES  ▸\n"
            "1. Utilise toujours le *function calling* pour déclencher les fonctions prévues.\n"
            "2. Quand l'utilisateur veut envoyer un SMS :\n"
            "   • Appelle immédiatement la fonction **prepare_send_message** dès que tu connais le NOM du destinataire. "
            "     Mets `message_content = \"\"` si l'utilisateur n'a encore rien dicté.\n"
            "   • NE DEMANDE PAS le contenu du message avant de savoir qu'il existe exactement UN contact correspondant. "
            "     S'il y a plusieurs homonymes, demande d'abord lequel choisir. "
            "     S'il n'y en a aucun, informe-en l'utilisateur.\n"
            "     Dès que l’utilisateur fournit le contenu du SMS :\n"
            "   • Appelle de nouveau **prepare_send_message** avec **les deux** champs "
            "     (nom + message_content). Ne demande pas de confirmation supplémentaire.\n"
            "    Il faut qu'as ce moment tu aies le contenu du message avant de l'envoyer.\n"
            "      Ne réponds jamais “Je ne peux pas envoyer le message moi-même” ; laisse le front faire l’envoi.\n"
            "3. Après chaque appel de fonction, rédige la réponse finale en te basant sur les données renvoyées. \n"
            "Si tu as besoin de plusieurs appels de fonction, fais-les dans l'ordre et rédige la réponse finale après le dernier appel.\n"
            "4. Quand l'utilisateur veut passer un appel :\n"
            "   • Appelle immédiatement la fonction **prepare_call_contact** dès que tu connais le NOM du destinataire.\n"
            "   • NE DEMANDE PAS de confirmation avant de passer l'appel.\n"
            "5. Quand l'utilisateur veut prendre une photo :\n"
            "   • Appelle immédiatement la fonction **prepare_open_camera**.\n"
            "   • NE DEMANDE PAS de confirmation avant d'ouvrir l'appareil photo.\n"
            "6. Quand l'utilisateur veut ouvrir une application :\n"
            "   • Appelle immédiatement la fonction **prepare_open_app** dès que tu connais le NOM de l'application.\n"
            "7. Quand l'utilisateur veut connaitre son emploi du temps  :\n"
            "   • Appelle immédiatement la fonction **read_local_calendar** dès que tu connais la période .\n"
        )
    }
]


# 💬 Dialogue principal

import json

async def ask_gpt(prompt: str, lat: float = None, lng: float = None) -> dict:
    # 1) On ajoute l'input utilisateur
    conversation.append({"role": "user", "content": prompt})

    response_data = {"text_to_speak": None, "action": None}

    # 2) Premier appel GPT avec Function Calling
    tools = [
        search_web_function,
        weather_function,
        calendar_add_function,
        calendar_read_function,
        calendar_get_function,
        get_directions_function,
        prepare_send_message_function,
        forecast_function,
        prepare_call_contact_function,
        prepare_open_camera_function,
        open_app_function,
        read_local_calendar_function
    ]

    first = await client.chat.completions.create(
        model="gpt-4o",
        messages=conversation,
        functions=tools,
        function_call="auto"
    )
    msg = first.choices[0].message

    # 3) Si GPT a déclenché un appel de fonction
    if msg.function_call:
        name = msg.function_call.name
        args = json.loads(msg.function_call.arguments)

        # Mapping des fonctions disponibles
        available = {
            "search_web": search_web,
            "get_weather": get_weather,
            "get_weather_forecast": get_weather_forecast,
            "add_event_to_calendar": add_event_to_calendar,
            "get_upcoming_events": get_upcoming_events,
            "get_today_events": get_today_events,
            "get_directions": lambda **kw: get_directions_from_coords(lat, lng, **kw),
            "prepare_send_message": prepare_send_message,
            "prepare_call_contact": prepare_call_contact,
            "prepare_open_camera": prepare_open_camera,
            "prepare_open_app": prepare_open_app,
            "read_local_calendar": read_local_calendar
        }

        # Exécution de la fonction
        result = await available[name](**args)

        # 4) Réinjecter d'abord le message assistant (avec function_call)
        conversation.append({
            "role": "assistant",
            "content": msg.content,
            "function_call": {
                "name": name,
                "arguments": msg.function_call.arguments
            }
        })

        # 5) Puis injecter la réponse de la fonction avec role "function"
        conversation.append({
            "role": "function",
            "name": name,
            "content": json.dumps(result)
        })

        # 6) Deuxième appel GPT pour formuler la réponse finale
        second = await client.chat.completions.create(
            model="gpt-4o",
            messages=conversation
        )
        answer_msg = second.choices[0].message
        answer = answer_msg.content.strip()
        response_data["text_to_speak"] = answer

        # 7) Extraction de l’action
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
        elif name == "prepare_call_contact":
            response_data["action"] = {
                "type": "make_call",  
                "data": result
            }
        elif name == "prepare_open_camera":
            response_data["action"] = {
                "type": "open_camera",
                "data": result
            }
        elif name == "prepare_open_app":
            response_data["action"] = {
                "type": "open_app",
                "data": result          
            }
        elif name == "read_local_calendar":
            response_data["action"] = {
                "type": "read_calendar",
                "data": result         
            }


        

        conversation.append({"role": "assistant", "content": answer})

    else:
        # Pas d'appel de fonction : GPT répond directement
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
        voice="ballad",
        input=text
    )
    # Création d'un fichier temporaire .mp3
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.write(resp.content)
    tmp.close()
    return tmp.name