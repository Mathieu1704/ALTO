import os
import time
import tempfile
import requests
from datetime import datetime, timedelta
import json # NEW: Ajouté pour parser les arguments de fonction plus proprement

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

    print("📥 Réponse Google Maps - status:", data.get("status"))
    if "error_message" in data:
        print("🛑 Erreur Google Maps:", data["error_message"])

    if data.get("status") != "OK" or not data.get("routes"):
        return ("Je n’ai pas pu obtenir l’itinéraire.", None)

    try:
        leg = data["routes"][0]["legs"][0]
        # summary = ( # NEW: Le summary sera généré par GPT ou sera un simple "Ok c'est parti"
        #     f"Depuis votre position actuelle jusqu’à {leg['end_address']}, "
        #     f"il faut environ {leg['duration']['text']} pour parcourir {leg['distance']['text']}."
        # )
        maps_url = (
            f"https://www.google.com/maps/dir/?api=1&origin={origin}"
            f"&destination={destination.replace(' ', '+')}&travelmode={mode}" # NEW: Added replace for destination
        )
        # NEW: On retourne juste l'URL, le texte viendra de GPT ou d'un message fixe
        return (f"Ok, c'est parti pour {destination} !", maps_url)
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
    "description": "Fournit un itinéraire à pied, en voiture ou en transport en utilisant la position actuelle de l'utilisateur si disponible. Demande la destination.", # NEW: Clarified description
    "parameters": {
        "type": "object",
        "properties": {
            # "origin": { # NEW: Origin is now implicitly the user's current location via lat/lng
            #     "type": "string",
            #     "description": "Adresse de départ (ex: Rue Albert 12, Mons)"
            # },
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
        "required": ["destination"] # NEW: Origin is no longer required here as it uses lat/lng
    }
}

# NEW: Fonction pour préparer l'envoi de message
prepare_send_message_function = {
    "name": "prepare_send_message",
    "description": "Prépare l'envoi d'un message SMS à un contact. Le message sera finalisé et envoyé sur le téléphone de l'utilisateur.",
    "parameters": {
        "type": "object",
        "properties": {
            "recipient_name": {
                "type": "string",
                "description": "Le nom du destinataire du message (ex: Maman, Jean Dupont)."
            },
            "message_content": {
                "type": "string",
                "description": "Le contenu du message à envoyer."
            }
        },
        "required": ["recipient_name", "message_content"]
    }
}


# 🧠 Mémoire de conversation
# NEW: Il est fortement recommandé d'améliorer ce system prompt pour inclure la nouvelle capacité.
# Par exemple: "Tu es Alto, un assistant vocal intelligent, connecté et utile. Tu peux aussi aider à préparer l'envoi de messages SMS. Demande à qui envoyer le message et quel est le contenu si ce n'est pas précisé."
conversation = [
    {"role": "system", "content": "Tu es Alto, un assistant vocal intelligent, connecté et utile. Tu peux aussi aider à préparer l'envoi de messages SMS. Si l'utilisateur veut envoyer un message mais ne précise pas le destinataire ou le contenu, demande-lui ces informations."}
]

# 💬 Dialogue principal
async def ask_gpt(prompt, lat=None, lng=None):
    # NEW: On ne réimporte plus les fonctions ici, elles sont déjà définies globalement.
    # from app.utils import (...)

    conversation.append({"role": "user", "content": prompt})
    
    # NEW: Structure de retour standardisée
    response_data = {
        "text_to_speak": None,
        "action": None # Sera { "type": "maps", "data": {"maps_url": "..."} } ou { "type": "send_message", "data": {"recipient_name": "...", "message_content": "..."} }
    }

    # 🔍 Détection manuelle d'intention de déplacement (gardée pour l'instant, mais pourrait aussi passer par une fonction GPT)
    #    Cette détection manuelle est prioritaire sur l'appel GPT standard.
    #    Si elle est déclenchée, elle ne permettra pas à GPT de gérer d'autres fonctions comme `prepare_send_message` dans le même tour.
    #    À évaluer si c'est le comportement souhaité ou si tout devrait passer par la logique de fonction GPT.
    keywords_direction = ["je veux aller", "je dois aller", "emmène-moi", "rends-toi", "direction", "aller à", "je vais à", "me rendre à"]
    is_direction_intent = any(k in prompt.lower() for k in keywords_direction)

    if is_direction_intent and lat is not None and lng is not None:
        # Utiliser GPT pour extraire la destination proprement (comme avant)
        try:
            destination_query = await client.chat.completions.create(
                model="gpt-4o", # ou gpt-3.5-turbo pour économiser si suffisant pour cette tâche
                messages=[
                    {"role": "system", "content": "Tu es un extracteur de destination. Rends simplement le nom du lieu vers lequel l'utilisateur veut aller, basé sur sa dernière phrase."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50
            )
            destination = destination_query.choices[0].message.content.strip()
            if destination: # Vérifier si la destination n'est pas vide
                print("📍 Destination extraite (manuellement) :", destination)
                summary_text, maps_link = get_directions_from_coords(lat, lng, destination) # Mode par défaut "walking"
                
                response_data["text_to_speak"] = summary_text
                if maps_link:
                    response_data["action"] = {"type": "maps", "data": {"maps_url": maps_link}}
                
                conversation.append({"role": "assistant", "content": summary_text}) # Ajoute la réponse au contexte
                return response_data
            else:
                print("⚠️ Destination non extraite par GPT pour la détection manuelle.")
                # Tomber dans la logique GPT standard si la destination est vide
        except Exception as e:
            print(f"Erreur lors de l'extraction de la destination (manuelle): {e}")
            # Tomber dans la logique GPT standard en cas d'erreur

    # 🤖 Requête GPT standard avec fonctions
    try: # NEW: try/except pour la requête OpenAI
        tools_to_use = [
            search_web_function,
            weather_function,
            calendar_add_function,
            calendar_read_function,
            calendar_get_function,
            get_directions_function,
            prepare_send_message_function # NEW: Ajout de la nouvelle fonction
        ]

        # S'assurer que les fonctions sont bien formatées pour l'API
        formatted_tools = [{"type": "function", "function": f} for f in tools_to_use]

        gpt_response = await client.chat.completions.create(
            model="gpt-4o",
            messages=conversation,
            tools=formatted_tools, # NEW: Utilisation de 'tools' au lieu de 'functions' avec le nouveau format
            tool_choice="auto"    # NEW: 'tool_choice' au lieu de 'function_call'
        )

        response_message = gpt_response.choices[0].message
        tool_calls = response_message.tool_calls # NEW: Accès aux appels d'outils

        if tool_calls:
            conversation.append(response_message) # Ajoute la réponse de l'assistant (avec les tool_calls)
            
            available_functions = {
                "search_web": search_web,
                "get_weather": get_weather,
                "add_event_to_calendar": add_event_to_calendar,
                "get_upcoming_events": get_upcoming_events,
                "get_today_events": get_today_events,
                "get_directions": lambda **kwargs: get_directions_from_coords(lat, lng, **kwargs) if lat is not None and lng is not None else ("Je n'ai pas pu obtenir votre position.", None),
                # NEW: "prepare_send_message" ne fait rien côté backend à part retourner les infos pour le frontend
                "prepare_send_message": lambda recipient_name, message_content: {
                    "recipient_name": recipient_name, 
                    "message_content": message_content
                }
            }

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions.get(function_name)
                
                try:
                    function_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    print(f"Erreur: Arguments de la fonction {function_name} ne sont pas un JSON valide: {tool_call.function.arguments}")
                    conversation.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": f"Erreur: arguments invalides fournis pour {function_name}.",
                    })
                    continue # Passe au prochain tool_call s'il y en a

                if function_to_call:
                    print(f"📞 Appel de la fonction: {function_name} avec args: {function_args}")
                    try:
                        if function_name == "get_directions":
                            if lat is not None and lng is not None:
                                # get_directions_from_coords attend destination et mode (optionnel)
                                # GPT devrait fournir 'destination' et optionnellement 'mode'
                                summary_text, maps_link = function_to_call(**function_args)
                                function_response_content = summary_text # Ce que GPT verra comme résultat de la fonction
                                response_data["text_to_speak"] = summary_text # Ce que l'utilisateur entendra initialement
                                if maps_link:
                                    response_data["action"] = {"type": "maps", "data": {"maps_url": maps_link}}
                            else:
                                function_response_content = "Je n'ai pas votre position pour calculer l'itinéraire."
                                response_data["text_to_speak"] = function_response_content
                        
                        elif function_name == "prepare_send_message":
                            # La "fonction" prepare_send_message retourne un dictionnaire avec les args
                            action_data_sms = function_to_call(**function_args)
                            function_response_content = f"Préparation du message pour {action_data_sms['recipient_name']}." # Ce que GPT verra
                            # Le texte à vocaliser sera généré par le followup GPT.
                            # On stocke l'action à faire par le frontend.
                            response_data["action"] = {"type": "send_message", "data": action_data_sms}
                            # On peut laisser GPT formuler la confirmation, ou en mettre une par défaut
                            # response_data["text_to_speak"] = f"Ok, je prépare votre message pour {action_data_sms['recipient_name']}."

                        else: # Pour les autres fonctions existantes
                            function_response_content = function_to_call(**function_args)
                            # Pour ces fonctions, le résultat de la fonction est souvent ce qu'on veut dire.
                            # Mais il est mieux de laisser GPT formuler la réponse finale.
                            # response_data["text_to_speak"] = function_response_content 

                        conversation.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": str(function_response_content), # S'assurer que c'est une chaîne
                        })
                    except Exception as e:
                        print(f"Erreur lors de l'exécution de la fonction {function_name}: {e}")
                        conversation.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": f"Erreur lors de l'exécution de {function_name}: {str(e)}",
                        })
                else:
                    print(f"Fonction {function_name} non reconnue.")
                    conversation.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": f"Fonction {function_name} non reconnue.",
                    })

            # Obtenir une réponse finale de GPT après l'exécution des fonctions
            second_response = await client.chat.completions.create(
                model="gpt-4o",
                messages=conversation
            )
            final_answer = second_response.choices[0].message.content.strip()
            response_data["text_to_speak"] = final_answer # Le texte à vocaliser est la réponse finale de GPT
            conversation.append({"role": "assistant", "content": final_answer})

        else: # Pas d'appel de fonction, GPT répond directement
            answer = response_message.content.strip()
            response_data["text_to_speak"] = answer
            conversation.append({"role": "assistant", "content": answer})

        return response_data

    except Exception as e: # NEW: Gestion d'erreur pour l'appel GPT
        print(f"Erreur lors de l'appel à GPT: {e}")
        response_data["text_to_speak"] = "Désolé, une erreur s'est produite lors du traitement de votre demande."
        # On pourrait ajouter une entrée "error" dans la conversation si nécessaire
        return response_data


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
        input="Hum... " + text # Gardé tel quel, à voir si le "Hum..." est toujours pertinent
    )
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file.write(speech.content)
    return temp_file.name