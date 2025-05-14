import os
import tempfile
import requests
from datetime import datetime, timedelta
import json # Pour parser les arguments de fonction de manière plus sûre

from openai import AsyncOpenAI
from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow # Non utilisé directement ici
from googleapiclient.discovery import build

# Initialisation du client OpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🔐 Clés d’API (assure-toi qu'elles sont bien chargées dans ton environnement Render)
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
GOOGLE_DIRECTIONS_API_KEY = os.getenv("GOOGLE_DIRECTIONS_API_KEY")

# 🔍 Brave Search
def search_web(query: str) -> str:
    if not BRAVE_API_KEY:
        return "Erreur: Clé API Brave Search non configurée."
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY}
    params = {"q": query, "count": 3}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status() # Lève une exception pour les codes d'erreur HTTP
        results = response.json().get("web", {}).get("results", [])
        if not results:
            return "Aucun résultat trouvé."
        return "\n\n".join([f"{r.get('title', 'Sans titre')} - {r.get('url', '')}\n{r.get('description', '')}" for r in results])
    except requests.exceptions.RequestException as e:
        print(f"ERREUR[search_web]: {e}")
        return "Erreur lors de la communication avec Brave Search."
    except Exception as e:
        print(f"ERREUR[search_web] inattendue: {e}")
        return "Erreur inattendue lors de la recherche web."

# 🌦️ Météo
def get_weather(city: str) -> str:
    if not OPENWEATHER_API_KEY:
        return "Erreur: Clé API OpenWeather non configurée."
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": OPENWEATHER_API_KEY, "lang": "fr", "units": "metric"}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        temp = round(data["main"]["temp"])
        feels_like = round(data["main"]["feels_like"])
        desc = data["weather"][0]["description"]
        return f"Aujourd'hui, à {city}, il fait {desc}, {temp}°C ressentis {feels_like}°C."
    except requests.exceptions.RequestException as e:
        print(f"ERREUR[get_weather]: {e}")
        return "Je n'ai pas pu obtenir la météo actuellement (erreur de communication)."
    except (KeyError, IndexError) as e:
        print(f"ERREUR[get_weather] parsing data: {e}")
        return "Je n'ai pas pu interpréter les données météo."
    except Exception as e:
        print(f"ERREUR[get_weather] inattendue: {e}")
        return "Erreur inattendue en obtenant la météo."


# 📅 Google Calendar
def _get_calendar_credentials():
    if not all([GOOGLE_REFRESH_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET]):
        print("ERREUR[Calendar]: Credentials Google manquants.")
        return None
    return Credentials(
        token=None, # Le token sera rafraîchi automatiquement si besoin
        refresh_token=GOOGLE_REFRESH_TOKEN,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )

def add_event_to_calendar(summary: str, start_time: str, duration_minutes: int = 60) -> str:
    creds = _get_calendar_credentials()
    if not creds: return "Erreur de configuration pour l'accès au calendrier."
    try:
        service = build("calendar", "v3", credentials=creds, static_discovery=False)
        start_dt = datetime.fromisoformat(start_time) # Attend un format ISO correct
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        event_body = {
            "summary": summary,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Brussels"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Brussels"},
        }
        created_event = service.events().insert(calendarId="primary", body=event_body).execute()
        return f"Événement '{summary}' ajouté le {start_dt.strftime('%d/%m/%Y à %H:%M')}."
    except Exception as e:
        print(f"ERREUR[add_event_to_calendar]: {e}")
        return "Erreur lors de l'ajout de l'événement au calendrier."

def get_upcoming_events(max_results: int = 5) -> str:
    creds = _get_calendar_credentials()
    if not creds: return "Erreur de configuration pour l'accès au calendrier."
    try:
        service = build("calendar", "v3", credentials=creds, static_discovery=False)
        now_utc_iso = datetime.utcnow().isoformat() + "Z"
        events_result = service.events().list(
            calendarId="primary", timeMin=now_utc_iso, maxResults=max_results,
            singleEvents=True, orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])
        if not events: return "Aucun événement à venir."
        message = "Voici vos prochains événements :\n"
        for event in events:
            start_str = event["start"].get("dateTime", event["start"].get("date"))
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            message += f"• {event.get('summary', '(Sans titre)')} le {start_dt.strftime('%d/%m')} à {start_dt.strftime('%H:%M')}\n"
        return message.strip()
    except Exception as e:
        print(f"ERREUR[get_upcoming_events]: {e}")
        return "Erreur lors de la récupération des événements à venir."

def get_today_events() -> str:
    creds = _get_calendar_credentials()
    if not creds: return "Erreur de configuration pour l'accès au calendrier."
    try:
        service = build('calendar', 'v3', credentials=creds, static_discovery=False)
        now_utc = datetime.utcnow()
        start_of_day_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day_utc = start_of_day_utc + timedelta(days=1)
        time_min_iso = start_of_day_utc.isoformat() + 'Z'
        time_max_iso = end_of_day_utc.isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary', timeMin=time_min_iso, timeMax=time_max_iso,
            singleEvents=True, orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        if not events: return "Tu n'as aucun événement prévu aujourd'hui."
        result = "Voici tes événements pour aujourd'hui :\n"
        for event in events:
            start_str = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'Sans titre')
            if 'T' in start_str:
                dt_obj = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                heure = dt_obj.strftime("%H:%M")
            else:
                heure = "toute la journée"
            result += f"- {summary} à {heure}\n"
        return result.strip()
    except Exception as e:
        print(f"ERREUR[get_today_events]: {e}")
        return "Je n'ai pas pu récupérer tes événements pour aujourd'hui."

# Google Maps Directions
def get_directions_from_coords(lat: float, lng: float, destination: str, mode: str = "walking") -> tuple[str, str | None]:
    if not GOOGLE_DIRECTIONS_API_KEY:
        return ("Erreur: Clé API Google Directions non configurée.", None)
    origin = f"{lat},{lng}"
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {"origin": origin, "destination": destination, "mode": mode, "language": "fr", "key": GOOGLE_DIRECTIONS_API_KEY}
    print(f"📤 Requête Google Maps: origin={origin}, destination={destination}, mode={mode}")
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"📥 Réponse Google Maps - status: {data.get('status')}")
        if data.get("status") != "OK" or not data.get("routes"):
            error_msg = data.get("error_message", "Itinéraire non trouvé ou erreur API.")
            print(f"🛑 Erreur Google Maps: {error_msg}")
            return (f"Je n’ai pas pu obtenir l’itinéraire: {error_msg}", None)
        
        # leg = data["routes"][0]["legs"][0] # Pas utilisé pour le résumé actuel
        maps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={requests.utils.quote(destination)}&travelmode={mode}"
        return ("Ok, c’est parti pour votre itinéraire !", maps_url)
    except requests.exceptions.RequestException as e:
        print(f"ERREUR[get_directions_from_coords] communication: {e}")
        return ("Erreur de communication avec Google Maps.", None)
    except (KeyError, IndexError) as e:
        print(f"ERREUR[get_directions_from_coords] parsing data: {e}")
        return ("Je n’ai pas pu interpréter les données de l'itinéraire.", None)
    except Exception as e:
        print(f"ERREUR[get_directions_from_coords] inattendue: {e}")
        return ("Erreur inattendue pour l'itinéraire.", None)

# 🎤 Transcription (Version robuste corrigée)
async def transcribe_audio(audio_path: str, original_filename_for_api: str):
    """
    Transcrire un fichier audio en utilisant l'API Whisper d'OpenAI.
    audio_path: Chemin vers le fichier audio temporaire sur le serveur.
    original_filename_for_api: Le nom de fichier original (ex: "audio.wav") pour aider l'API.
    """
    with open(audio_path, "rb") as f_obj:
        print(f"DEBUG[utils.transcribe_audio]: Tentative de transcription pour '{original_filename_for_api}' depuis '{audio_path}'")
        try:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=(original_filename_for_api, f_obj) # Passer le nom et l'objet fichier
            )
            return transcript.text
        except Exception as e:
            print(f"ERREUR[utils.transcribe_audio] API call: {e}")
            # Relancer l'exception pour qu'elle soit gérée dans main.py et qu'un 500 soit retourné
            raise # Important pour que le code appelant sache qu'il y a eu une erreur

# 🔊 TTS
async def synthesize_speech(text: str) -> str | None:
    input_text = text
    if not input_text or input_text.isspace():
        print("⚠️ Texte vide fourni à synthesize_speech, utilisation d'un espace.")
        input_text = " " # TTS-1 peut gérer un espace, ou retourner une erreur si l'entrée est vide.
    
    try:
        speech = await client.audio.speech.create(
            model="tts-1", voice="shimmer", input=input_text, response_format="mp3"
        )
        # Utiliser NamedTemporaryFile pour obtenir un chemin de fichier
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_speech_file:
            tmp_speech_file.write(speech.content)
            # tmp_speech_file.flush() # s'assurer que tout est écrit
            # tmp_speech_file.close() # fermer le handle avant de retourner le nom n'est pas nécessaire ici car on retourne le nom
            return tmp_speech_file.name
    except Exception as e:
        print(f"ERREUR[utils.synthesize_speech] API call: {e}")
        return None # Indiquer une erreur


# 📚 Fonctions accessibles par GPT (Tools)
search_web_function = {"name": "search_web", "description": "Effectue une recherche web avec Brave Search. Utile pour des informations actuelles ou spécifiques.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Question ou sujet à rechercher"}}, "required": ["query"]}}
weather_function = {"name": "get_weather", "description": "Donne la météo actuelle pour une ville.", "parameters": {"type": "object", "properties": {"city": {"type": "string", "description": "Nom de la ville"}}, "required": ["city"]}}
calendar_add_function = {"name": "add_event_to_calendar", "description": "Ajoute un événement dans le Google Calendar de l'utilisateur. Demande toujours confirmation avant d'appeler cette fonction.", "parameters": {"type": "object", "properties": {"summary": {"type": "string", "description": "Titre de l'événement"}, "start_time": {"type": "string", "description": "Date et heure ISO ex: 2024-07-15T14:00:00. Utilise l'heure et la date actuelles si l'utilisateur dit 'maintenant' ou 'tout de suite'."},"duration_minutes": {"type": "integer", "description": "Durée en minutes (par défaut 60)", "default": 60}}, "required": ["summary", "start_time"]}}
calendar_read_function = {"name": "get_upcoming_events", "description": "Récupère les événements à venir (jusqu'à 5 par défaut) dans le calendrier Google de l'utilisateur.", "parameters": {"type": "object", "properties": {"max_results": {"type": "integer", "description": "Nombre maximum d'événements à récupérer", "default": 5}}}}
calendar_get_function = {"name": "get_today_events", "description": "Récupère les événements du jour dans l’agenda Google Calendar connecté.", "parameters": {"type": "object", "properties": {}}}
get_directions_function = {"name": "get_directions", "description": "Fournit un itinéraire en utilisant la position actuelle de l'utilisateur comme point de départ. Le frontend fournit les coordonnées GPS.", "parameters": {"type": "object", "properties": {"destination": {"type": "string", "description": "Adresse ou lieu d’arrivée (ex: Tour Eiffel, Paris)"},"mode": {"type": "string", "enum": ["walking", "driving", "transit"], "description": "Mode de transport (défaut: walking)", "default": "walking"}}, "required": ["destination"]}}
prepare_send_message_function = {"name": "prepare_send_message", "description": "Prépare l'envoi d'un message à un contact. Collecte le nom du destinataire et le contenu du message. Si l'un des deux manque, demande à l'utilisateur de le fournir AVANT d'appeler cette fonction. L'application cliente se chargera de trouver le contact et d'ouvrir l'application de messagerie.", "parameters": {"type": "object", "properties": {"recipient_name": {"type": "string", "description": "Nom du contact à qui envoyer le message."}, "message_content": {"type": "string", "description": "Contenu du message à envoyer."}}, "required": ["recipient_name", "message_content"]}}

# 🧠 Mémoire de conversation globale (simplification)
# Pour un vrai multi-utilisateur, cela devrait être stocké par session/utilisateur (ex: Redis, DB)
conversation_history_store: dict[str, list] = {}
MAX_HISTORY_LEN = 20 # Message système + 9 échanges (user/assistant) * 2 + dernier user

def get_user_conversation(user_id: str) -> list:
    if user_id not in conversation_history_store:
        conversation_history_store[user_id] = [{"role": "system", "content": (
            "Tu es Alto, un assistant vocal intelligent, connecté et utile. "
            "Tu es concis et vas droit au but. "
            "Si l'utilisateur veut envoyer un message mais ne précise pas le destinataire ou le contenu, demande-lui ces informations avant d'utiliser la fonction 'prepare_send_message'. "
            "Si l'utilisateur demande un itinéraire, la position actuelle est fournie par le système (ne demande pas l'origine si ce n'est pas spécifié). "
            "Pour les événements de calendrier, si l'utilisateur dit 'maintenant' ou 'tout de suite', utilise l'heure et la date actuelles pour 'start_time' au format ISO (YYYY-MM-DDTHH:MM:SS). "
            "Fuseau horaire par défaut pour les nouveaux événements : Europe/Brussels. "
            "Demande toujours confirmation avant d'ajouter un événement au calendrier. "
            "Lorsque tu appelles une fonction, ne réponds rien d'autre que l'appel de fonction lui-même."
        )}]
    return conversation_history_store[user_id]

def update_user_conversation(user_id: str, new_messages: list):
    conv = get_user_conversation(user_id)
    conv.extend(new_messages)
    # Limiter la taille de l'historique
    if len(conv) > MAX_HISTORY_LEN:
        system_message = conv[0] # Garder le message système
        conversation_history_store[user_id] = [system_message] + conv[-(MAX_HISTORY_LEN-1):]


# 💬 Dialogue principal
async def ask_gpt(prompt: str, lat: float = None, lng: float = None, user_id: str = "default_user"):
    current_conversation_for_user = get_user_conversation(user_id).copy() # Copie pour cet appel
    current_conversation_for_user.append({"role": "user", "content": prompt})
    
    response_data = {"text_response": None, "action_data": None}
    new_history_additions = [{"role": "user", "content": prompt}] # Messages à ajouter à l'historique global

    # Détection manuelle d'intention de déplacement (simplifiée, peut être entièrement gérée par GPT tool)
    keywords_destination = ["itinéraire vers", "emmène-moi", "direction pour", "aller à"] # Plus spécifiques
    prompt_lower = prompt.lower()
    if any(k in prompt_lower for k in keywords_destination) and lat is not None and lng is not None:
        try:
            # ... (logique d'extraction de destination avec GPT comme avant) ...
            # Pour simplifier, on pourrait directement appeler get_directions_from_coords si la destination est claire.
            # Ici, on garde la logique GPT pour l'extraction.
            dest_extract_completion = await client.chat.completions.create(
                model="gpt-4o", messages=[{"role": "system", "content": "Extrais la destination de cette phrase. Réponds juste avec le nom du lieu ou l'adresse."}, {"role": "user", "content": prompt}], temperature=0.0, max_tokens=50
            )
            destination = dest_extract_completion.choices[0].message.content.strip()

            if destination:
                print(f"📍 Destination (manuelle): {destination}")
                summary_text, maps_url = get_directions_from_coords(lat, lng, destination)
                if maps_url:
                    response_data["text_response"] = summary_text
                    response_data["action_data"] = {"type": "OPEN_MAPS", "payload": {"url": maps_url}}
                    new_history_additions.append({"role": "assistant", "content": f"Action: ouverture de Maps pour {destination}."}) # Pour le contexte
                    update_user_conversation(user_id, new_history_additions)
                    return response_data
                else: # Erreur de get_directions_from_coords
                    response_data["text_response"] = summary_text 
                    new_history_additions.append({"role": "assistant", "content": summary_text})
                    update_user_conversation(user_id, new_history_additions)
                    return response_data
        except Exception as e:
            print(f"💥 Erreur extraction destination (manuelle): {e}")
            # Laisser GPT gérer si l'extraction manuelle échoue

    # Requête GPT standard avec tools
    try:
        gpt_response = await client.chat.completions.create(
            model="gpt-4o", messages=current_conversation_for_user,
            tools=[
                {"type": "function", "function": f} for f in [
                    search_web_function, weather_function, calendar_add_function,
                    calendar_read_function, calendar_get_function, get_directions_function,
                    prepare_send_message_function
                ]
            ],
            tool_choice="auto"
        )
        message = gpt_response.choices[0].message
        new_history_additions.append(message) # Ajoute la réponse de l'assistant (avec ou sans tool_calls)

        tool_calls = message.tool_calls
        if tool_calls:
            available_tool_functions = {
                "search_web": search_web, "get_weather": get_weather,
                "add_event_to_calendar": add_event_to_calendar,
                "get_upcoming_events": get_upcoming_events, "get_today_events": get_today_events,
            }
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                tool_response_content = f"Erreur: fonction {function_name} non implémentée correctement."
                try:
                    function_args = json.loads(tool_call.function.arguments)
                    print(f"🛠️ GPT appelle: {function_name}({function_args})")

                    if function_name == "prepare_send_message":
                        response_data["text_response"] = f"Ok, je prépare un message pour {function_args.get('recipient_name', 'le contact demandé')}."
                        response_data["action_data"] = {"type": "PREPARE_SEND_MESSAGE", "payload": function_args}
                        tool_response_content = "Action de préparation de message déléguée au client."
                    elif function_name == "get_directions":
                        if lat is not None and lng is not None:
                            dest = function_args.get("destination")
                            mode = function_args.get("mode", "walking")
                            summary_text, maps_url = get_directions_from_coords(lat, lng, dest, mode)
                            if maps_url:
                                response_data["text_response"] = summary_text
                                response_data["action_data"] = {"type": "OPEN_MAPS", "payload": {"url": maps_url}}
                                tool_response_content = f"Itinéraire vers {dest} fourni."
                            else: tool_response_content = summary_text
                        else: tool_response_content = "Position de l'utilisateur non disponible pour calculer l'itinéraire."
                    elif function_name in available_tool_functions:
                        tool_response_content = available_tool_functions[function_name](**function_args)
                    else:
                        tool_response_content = f"Fonction {function_name} inconnue."
                except json.JSONDecodeError as e_json:
                    print(f"ERREUR[ask_gpt] parsing JSON args pour {function_name}: {e_json}")
                    tool_response_content = f"Erreur de format des arguments pour {function_name}."
                except TypeError as e_type: # Mauvais arguments pour la fonction Python
                    print(f"ERREUR[ask_gpt] appel de {function_name} avec {function_args}: {e_type}")
                    tool_response_content = f"Erreur d'arguments pour la fonction {function_name}."
                except Exception as e_tool:
                    print(f"ERREUR[ask_gpt] exécution de {function_name}: {e_tool}")
                    tool_response_content = f"Erreur inattendue lors de l'exécution de {function_name}."
                
                new_history_additions.append({"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": str(tool_response_content)})
            
            if response_data["action_data"]: # Si une action client est déjà définie par un tool
                if not response_data["text_response"]: response_data["text_response"] = "Ok."
                update_user_conversation(user_id, new_history_additions)
                return response_data

            # Si un tool a été appelé mais n'a pas défini d'action_data (ex: search_web), faire un suivi
            current_conversation_for_user.extend(new_history_additions[1:]) # Ajouter la réponse de l'assistant et les tool_results
            followup_response = await client.chat.completions.create(model="gpt-4o", messages=current_conversation_for_user)
            answer = followup_response.choices[0].message.content.strip()
            new_history_additions.append(followup_response.choices[0].message) # Ajouter la réponse finale de l'assistant
            response_data["text_response"] = answer
        else: # Pas d'appel de tool, réponse directe de GPT
            answer = message.content.strip()
            response_data["text_response"] = answer
            # new_history_additions contient déjà le message de l'assistant

        update_user_conversation(user_id, new_history_additions)
        return response_data

    except Exception as e:
        import traceback
        print(f"💥 Erreur majeure dans ask_gpt: {e}\n{traceback.format_exc()}")
        response_data["text_response"] = "Désolé, une erreur majeure est survenue lors du traitement de votre demande."
        # Ne pas ajouter l'erreur à l'historique de conversation car elle est technique
        return response_data