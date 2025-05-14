import os
import tempfile
import requests
from datetime import datetime, timedelta
import json # Pour parser les arguments de fonction de manière plus sûre
import traceback # Pour un logging d'erreur plus détaillé

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
        print("WARN[search_web]: Clé API Brave Search non configurée.")
        return "Désolé, la recherche web n'est pas disponible pour le moment."
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY}
    params = {"q": query, "count": 3}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status() 
        results = response.json().get("web", {}).get("results", [])
        if not results:
            return "Aucun résultat trouvé pour votre recherche."
        return "\n\n".join([f"{r.get('title', 'Sans titre')} - {r.get('url', '')}\n{r.get('description', '')}" for r in results])
    except requests.exceptions.Timeout:
        print(f"ERREUR[search_web]: Timeout lors de la connexion à Brave Search.")
        return "La recherche web a mis trop de temps à répondre."
    except requests.exceptions.RequestException as e:
        print(f"ERREUR[search_web]: {e}")
        return "Erreur de communication avec le service de recherche web."
    except Exception as e:
        print(f"ERREUR[search_web] inattendue: {e}")
        return "Une erreur inattendue est survenue pendant la recherche web."

# 🌦️ Météo
def get_weather(city: str) -> str:
    if not OPENWEATHER_API_KEY:
        print("WARN[get_weather]: Clé API OpenWeather non configurée.")
        return "Désolé, le service météo n'est pas disponible pour le moment."
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": OPENWEATHER_API_KEY, "lang": "fr", "units": "metric"}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        temp = round(data["main"]["temp"])
        feels_like = round(data["main"]["feels_like"])
        desc = data["weather"][0]["description"]
        return f"Actuellement à {city}, il fait {desc}, la température est de {temp}°C et la température ressentie est de {feels_like}°C."
    except requests.exceptions.Timeout:
        print(f"ERREUR[get_weather]: Timeout lors de la connexion à OpenWeather.")
        return "Le service météo a mis trop de temps à répondre."
    except requests.exceptions.RequestException as e:
        print(f"ERREUR[get_weather]: {e}")
        if response and response.status_code == 404:
             return f"Je n'ai pas trouvé la ville de {city} pour la météo."
        return "Je n'ai pas pu obtenir la météo (erreur de communication)."
    except (KeyError, IndexError) as e:
        print(f"ERREUR[get_weather] parsing data: {e}")
        return "Je n'ai pas pu interpréter les données météo reçues."
    except Exception as e:
        print(f"ERREUR[get_weather] inattendue: {e}")
        return "Une erreur inattendue est survenue en consultant la météo."


# 📅 Google Calendar
def _get_calendar_credentials():
    if not all([GOOGLE_REFRESH_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET]):
        print("ERREUR[Calendar]: Credentials Google manquants. L'accès au calendrier est désactivé.")
        return None
    return Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )

def add_event_to_calendar(summary: str, start_time: str, duration_minutes: int = 60) -> str:
    creds = _get_calendar_credentials()
    if not creds: return "L'accès au calendrier n'est pas configuré."
    try:
        service = build("calendar", "v3", credentials=creds, static_discovery=False)
        start_dt = datetime.fromisoformat(start_time)
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        event_body = {
            "summary": summary,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Brussels"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Brussels"},
        }
        created_event = service.events().insert(calendarId="primary", body=event_body).execute()
        return f"Événement '{summary}' ajouté le {start_dt.strftime('%d/%m/%Y à %Hh%M')}."
    except Exception as e:
        print(f"ERREUR[add_event_to_calendar]: {e}")
        return "Une erreur est survenue lors de l'ajout de l'événement au calendrier."

def get_upcoming_events(max_results: int = 5) -> str:
    creds = _get_calendar_credentials()
    if not creds: return "L'accès au calendrier n'est pas configuré."
    try:
        service = build("calendar", "v3", credentials=creds, static_discovery=False)
        now_utc_iso = datetime.utcnow().isoformat() + "Z"
        events_result = service.events().list(
            calendarId="primary", timeMin=now_utc_iso, maxResults=max_results,
            singleEvents=True, orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])
        if not events: return "Vous n'avez aucun événement à venir."
        message = "Voici vos prochains événements :\n"
        for event in events:
            start_str = event["start"].get("dateTime", event["start"].get("date"))
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            message += f"• {event.get('summary', '(Sans titre)')} le {start_dt.strftime('%d/%m')} à {start_dt.strftime('%Hh%M')}\n"
        return message.strip()
    except Exception as e:
        print(f"ERREUR[get_upcoming_events]: {e}")
        return "Une erreur est survenue lors de la récupération des événements à venir."

def get_today_events() -> str:
    creds = _get_calendar_credentials()
    if not creds: return "L'accès au calendrier n'est pas configuré."
    try:
        service = build('calendar', 'v3', credentials=creds, static_discovery=False)
        now_utc = datetime.utcnow()
        # Utiliser le fuseau horaire de l'utilisateur serait mieux, mais pour l'instant UTC.
        start_of_day_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day_utc = start_of_day_utc + timedelta(days=1)
        time_min_iso = start_of_day_utc.isoformat() + 'Z'
        time_max_iso = end_of_day_utc.isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary', timeMin=time_min_iso, timeMax=time_max_iso,
            singleEvents=True, orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        if not events: return "Vous n'avez aucun événement prévu aujourd'hui."
        result = "Vos événements pour aujourd'hui sont :\n"
        for event in events:
            start_str = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'Sans titre')
            if 'T' in start_str: # C'est un événement avec une heure précise
                dt_obj = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                heure = dt_obj.strftime("%Hh%M")
            else: # C'est un événement sur toute la journée
                heure = "toute la journée"
            result += f"- {summary} ({heure})\n"
        return result.strip()
    except Exception as e:
        print(f"ERREUR[get_today_events]: {e}")
        return "Je n'ai pas pu récupérer vos événements pour aujourd'hui."

# Google Maps Directions
def get_directions_from_coords(lat: float, lng: float, destination: str, mode: str = "walking") -> tuple[str, str | None]:
    if not GOOGLE_DIRECTIONS_API_KEY:
        print("WARN[get_directions_from_coords]: Clé API Google Directions non configurée.")
        return ("Le service d'itinéraire n'est pas disponible pour le moment.", None)
    origin = f"{lat},{lng}"
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {"origin": origin, "destination": destination, "mode": mode, "language": "fr", "key": GOOGLE_DIRECTIONS_API_KEY}
    print(f"INFO[get_directions_from_coords]: Requête Google Maps: origin={origin}, destination='{destination}', mode={mode}")
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"INFO[get_directions_from_coords]: Réponse Google Maps status: {data.get('status')}")
        if data.get("status") != "OK" or not data.get("routes"):
            error_msg = data.get("error_message", "Itinéraire non trouvé ou erreur API.")
            print(f"WARN[get_directions_from_coords]: Erreur Google Maps: {error_msg}")
            return (f"Je n’ai pas pu obtenir d’itinéraire pour '{destination}': {error_msg}", None)
        
        leg = data["routes"][0]["legs"][0]
        summary = f"Pour aller à {leg.get('end_address', destination)}, cela prendra environ {leg['duration']['text']} ({leg['distance']['text']})."
        maps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={requests.utils.quote(destination)}&travelmode={mode}"
        return (summary, maps_url)
    except requests.exceptions.Timeout:
        print(f"ERREUR[get_directions_from_coords]: Timeout lors de la connexion à Google Maps.")
        return ("Le service d'itinéraire a mis trop de temps à répondre.", None)
    except requests.exceptions.RequestException as e:
        print(f"ERREUR[get_directions_from_coords] communication: {e}")
        return ("Erreur de communication avec le service d'itinéraire.", None)
    except (KeyError, IndexError) as e:
        print(f"ERREUR[get_directions_from_coords] parsing data: {e}")
        return ("Je n’ai pas pu interpréter les données de l'itinéraire.", None)
    except Exception as e:
        print(f"ERREUR[get_directions_from_coords] inattendue: {e}")
        return ("Une erreur inattendue est survenue pour l'itinéraire.", None)

# 🎤 Transcription (Version robuste corrigée)
async def transcribe_audio(audio_path: str, original_filename_for_api: str) -> str:
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
            raise # Important pour que le code appelant (main.py) sache qu'il y a eu une erreur

# 🔊 TTS
async def synthesize_speech(text: str) -> str | None:
    input_text = text
    if not input_text or input_text.isspace():
        print("WARN[utils.synthesize_speech]: Texte vide fourni, utilisation d'un espace.")
        input_text = " "
    
    try:
        speech = await client.audio.speech.create(
            model="tts-1", voice="shimmer", input=input_text, response_format="mp3"
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_speech_file:
            tmp_speech_file.write(speech.content)
            return tmp_speech_file.name
    except Exception as e:
        print(f"ERREUR[utils.synthesize_speech] API call: {e}")
        return None


# 📚 Fonctions accessibles par GPT (Tools)
search_web_function = {"name": "search_web", "description": "Effectue une recherche web avec Brave Search. Utile pour des informations actuelles ou spécifiques.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Question ou sujet à rechercher"}}, "required": ["query"]}}
weather_function = {"name": "get_weather", "description": "Donne la météo actuelle pour une ville.", "parameters": {"type": "object", "properties": {"city": {"type": "string", "description": "Nom de la ville"}}, "required": ["city"]}}
calendar_add_function = {"name": "add_event_to_calendar", "description": "Ajoute un événement dans le Google Calendar de l'utilisateur. Demande toujours confirmation avant d'appeler cette fonction.", "parameters": {"type": "object", "properties": {"summary": {"type": "string", "description": "Titre de l'événement"}, "start_time": {"type": "string", "description": "Date et heure ISO ex: 2024-07-15T14:00:00. Utilise l'heure et la date actuelles si l'utilisateur dit 'maintenant' ou 'tout de suite'."},"duration_minutes": {"type": "integer", "description": "Durée en minutes (par défaut 60)", "default": 60}}, "required": ["summary", "start_time"]}}
calendar_read_function = {"name": "get_upcoming_events", "description": "Récupère les événements à venir (jusqu'à 5 par défaut) dans le calendrier Google de l'utilisateur.", "parameters": {"type": "object", "properties": {"max_results": {"type": "integer", "description": "Nombre maximum d'événements à récupérer", "default": 5}}}}
calendar_get_function = {"name": "get_today_events", "description": "Récupère les événements du jour dans l’agenda Google Calendar connecté.", "parameters": {"type": "object", "properties": {}}}
get_directions_function = {"name": "get_directions", "description": "Fournit un itinéraire en utilisant la position actuelle de l'utilisateur comme point de départ. Le frontend fournit les coordonnées GPS.", "parameters": {"type": "object", "properties": {"destination": {"type": "string", "description": "Adresse ou lieu d’arrivée (ex: Tour Eiffel, Paris)"},"mode": {"type": "string", "enum": ["walking", "driving", "transit"], "description": "Mode de transport (défaut: walking)", "default": "walking"}}, "required": ["destination"]}}
prepare_send_message_function = {"name": "prepare_send_message", "description": "Prépare l'envoi d'un message à un contact. Collecte le nom du destinataire et le contenu du message. Si l'un des deux manque, demande à l'utilisateur de le fournir AVANT d'appeler cette fonction. L'application cliente se chargera de trouver le contact et d'ouvrir l'application de messagerie.", "parameters": {"type": "object", "properties": {"recipient_name": {"type": "string", "description": "Nom du contact à qui envoyer le message."}, "message_content": {"type": "string", "description": "Contenu du message à envoyer."}}, "required": ["recipient_name", "message_content"]}}

# 🧠 Mémoire de conversation
conversation_history_store: dict[str, list[dict[str, str]]] = {} # Type hint ajouté
MAX_HISTORY_LEN = 20 

def get_user_conversation(user_id: str) -> list[dict[str, str]]:
    if user_id not in conversation_history_store:
        # Initialisation du prompt système pour chaque nouvel utilisateur
        conversation_history_store[user_id] = [{"role": "system", "content": (
            "Tu es Alto, un assistant vocal intelligent, connecté et utile. "
            "Tu es concis et vas droit au but. "
            "Si l'utilisateur veut envoyer un message mais ne précise pas le destinataire ou le contenu, demande-lui ces informations avant d'utiliser la fonction 'prepare_send_message'. "
            "Si l'utilisateur demande un itinéraire, la position actuelle est fournie par le système (ne demande pas l'origine si ce n'est pas spécifié). "
            "Pour les événements de calendrier, si l'utilisateur dit 'maintenant' ou 'tout de suite', tu dois calculer et utiliser l'heure et la date actuelles pour 'start_time' au format ISO (YYYY-MM-DDTHH:MM:SS). "
            "Le fuseau horaire par défaut pour les nouveaux événements est Europe/Brussels. "
            "Demande toujours confirmation avant d'ajouter un événement au calendrier via la fonction 'add_event_to_calendar'. "
            "Lorsque tu appelles une fonction (tool), ne réponds rien d'autre que l'appel de fonction lui-même. Ne rajoute pas de phrases comme 'Ok, je vais faire ça.' avant l'appel de fonction."
        )}]
    return conversation_history_store[user_id]

def update_user_conversation(user_id: str, new_messages: list[dict[str, str]]):
    # S'assure que l'utilisateur a une conversation initialisée
    conv = get_user_conversation(user_id) 
    
    # Ajoute les nouveaux messages. Si conv était vide (ne devrait pas arriver avec get_user_conversation),
    # il faut s'assurer que le message système est là.
    # Cependant, get_user_conversation garantit que conv[0] est le message système.
    
    for msg in new_messages:
        # Éviter d'ajouter des messages système en double si prompt est vide la première fois
        if msg["role"] == "system" and len(conv) > 0 and conv[0]["role"] == "system":
            continue
        conv.append(msg)
            
    # Limiter la taille de l'historique
    if len(conv) > MAX_HISTORY_LEN:
        system_message = conv[0] 
        # Garder le message système et les MAX_HISTORY_LEN-1 derniers messages
        conversation_history_store[user_id] = [system_message] + conv[-(MAX_HISTORY_LEN-1):]
    # else: # Pas besoin de réassigner si la taille n'est pas dépassée, car conv est une référence
    #    conversation_history_store[user_id] = conv


# 💬 Dialogue principal
async def ask_gpt(prompt: str, lat: float = None, lng: float = None, user_id: str = "default_user"):
    
    # Récupérer la conversation de l'utilisateur (inclut le message système)
    # current_conversation_for_user est une copie modifiable pour cet appel uniquement.
    current_conversation_for_user = get_user_conversation(user_id).copy() 
    
    # Ajouter le message de l'utilisateur actuel à cette copie locale
    current_conversation_for_user.append({"role": "user", "content": prompt})
    
    # Ce qui sera réellement ajouté à l'historique stocké
    messages_to_add_to_stored_history: list[dict[str, str]] = [{"role": "user", "content": prompt}]
    
    response_data = {"text_response": "Désolé, je n'ai pas pu traiter votre demande.", "action_data": None} # Fallback

    # --- Détection manuelle d'intention de déplacement (Optionnel, peut être délégué à un tool GPT) ---
    # Si on garde cette section, il faut s'assurer qu'elle ne court-circuite pas trop agressivement GPT.
    # keywords_destination = ["itinéraire vers", "emmène-moi à", "direction pour", "aller à"]
    # prompt_lower = prompt.lower()
    # if any(k in prompt_lower for k in keywords_destination) and "message" not in prompt_lower and lat is not None and lng is not None:
    #     try:
    #         dest_extract_completion = await client.chat.completions.create(
    #             model="gpt-4o", messages=[{"role": "system", "content": "Extrais la destination de cette phrase. Réponds juste avec le nom du lieu ou l'adresse."}, {"role": "user", "content": prompt}], temperature=0.0, max_tokens=50
    #         )
    #         destination = dest_extract_completion.choices[0].message.content.strip()
    #         if destination:
    #             print(f"INFO[ask_gpt]: Destination (détection manuelle): '{destination}'")
    #             summary_text, maps_url = get_directions_from_coords(lat, lng, destination)
    #             if maps_url:
    #                 response_data["text_response"] = summary_text
    #                 response_data["action_data"] = {"type": "OPEN_MAPS", "payload": {"url": maps_url}}
    #                 messages_to_add_to_stored_history.append({"role": "assistant", "content": f"Action: ouverture de Maps pour {destination}."})
    #                 update_user_conversation(user_id, messages_to_add_to_stored_history)
    #                 return response_data
    #             else:
    #                 response_data["text_response"] = summary_text
    #                 messages_to_add_to_stored_history.append({"role": "assistant", "content": summary_text})
    #                 update_user_conversation(user_id, messages_to_add_to_stored_history)
    #                 return response_data
    #     except Exception as e_dest_extract:
    #         print(f"WARN[ask_gpt]: Erreur extraction destination (manuelle), fallback sur GPT tools: {e_dest_extract}")
    # --- Fin Détection Manuelle ---

    try:
        print(f"DEBUG[ask_gpt]: Conversation envoyée à GPT pour user '{user_id}': {json.dumps(current_conversation_for_user, indent=2)}")
        gpt_response = await client.chat.completions.create(
            model="gpt-4o", messages=current_conversation_for_user,
            tools=[{"type": "function", "function": f} for f in [
                search_web_function, weather_function, calendar_add_function,
                calendar_read_function, calendar_get_function, get_directions_function,
                prepare_send_message_function
            ]],
            tool_choice="auto"
        )
        message = gpt_response.choices[0].message
        messages_to_add_to_stored_history.append(message.model_dump(exclude_none=True)) # model_dump pour Pydantic v2

        tool_calls = message.tool_calls
        if tool_calls:
            available_tool_functions = {
                "search_web": search_web, "get_weather": get_weather,
                "add_event_to_calendar": add_event_to_calendar,
                "get_upcoming_events": get_upcoming_events, "get_today_events": get_today_events,
            }
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                tool_response_content_str = f"Erreur: fonction {function_name} non implémentée correctement."
                try:
                    function_args = json.loads(tool_call.function.arguments)
                    print(f"INFO[ask_gpt]: GPT tool call: {function_name}({json.dumps(function_args)})")

                    if function_name == "prepare_send_message":
                        response_data["text_response"] = f"D'accord, je prépare un message pour {function_args.get('recipient_name', 'le contact')}."
                        response_data["action_data"] = {"type": "PREPARE_SEND_MESSAGE", "payload": function_args}
                        tool_response_content_str = "Action de préparation de message déléguée au client."
                    elif function_name == "get_directions":
                        if lat is not None and lng is not None:
                            dest = function_args.get("destination")
                            mode = function_args.get("mode", "walking")
                            summary_text, maps_url = get_directions_from_coords(lat, lng, dest, mode)
                            if maps_url:
                                response_data["text_response"] = summary_text
                                response_data["action_data"] = {"type": "OPEN_MAPS", "payload": {"url": maps_url}}
                                tool_response_content_str = f"Itinéraire vers {dest} fourni."
                            else: tool_response_content_str = summary_text # Message d'erreur de get_directions
                        else: tool_response_content_str = "La position de l'utilisateur n'est pas disponible pour calculer l'itinéraire."
                    elif function_name in available_tool_functions:
                        # Pour les fonctions synchrones, il faudrait les appeler dans un thread executor avec asyncio
                        # ou les rendre asynchrones si elles font des I/O bloquantes.
                        # Pour l'instant, on les appelle directement (attention si elles sont longues).
                        tool_response_content_str = available_tool_functions[function_name](**function_args)
                    else:
                        tool_response_content_str = f"La fonction {function_name} n'est pas reconnue ou implémentée."
                
                except json.JSONDecodeError as e_json:
                    print(f"ERREUR[ask_gpt] parsing JSON args pour {function_name}: {e_json}")
                    tool_response_content_str = f"Erreur de format des arguments pour {function_name}."
                except TypeError as e_type: 
                    print(f"ERREUR[ask_gpt] appel de {function_name} avec args {function_args if 'function_args' in locals() else 'non parsés'}: {e_type}")
                    tool_response_content_str = f"Erreur d'arguments pour la fonction {function_name}."
                except Exception as e_tool:
                    print(f"ERREUR[ask_gpt] exécution de {function_name}: {e_tool}\n{traceback.format_exc()}")
                    tool_response_content_str = f"Erreur inattendue lors de l'exécution de {function_name}."
                
                messages_to_add_to_stored_history.append({"tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": tool_response_content_str})
            
            if response_data["action_data"]: # Si une action client a été définie par un tool
                if not response_data["text_response"]: response_data["text_response"] = "Ok."
                update_user_conversation(user_id, messages_to_add_to_stored_history)
                return response_data

            # Si un tool a été appelé mais n'a PAS défini d'action_data (ex: search_web), faire un suivi à GPT
            # On ajoute les messages de l'assistant et du tool à la conversation pour le suivi
            current_conversation_for_user.extend(messages_to_add_to_stored_history[1:]) 
            
            print(f"DEBUG[ask_gpt]: Conversation envoyée à GPT pour suivi après tool call pour user '{user_id}': {json.dumps(current_conversation_for_user, indent=2)}")
            followup_response = await client.chat.completions.create(model="gpt-4o", messages=current_conversation_for_user)
            answer = followup_response.choices[0].message.content.strip()
            messages_to_add_to_stored_history.append(followup_response.choices[0].message.model_dump(exclude_none=True))
            response_data["text_response"] = answer
        
        else: # Pas d'appel de tool, réponse directe de GPT
            answer = message.content.strip()
            response_data["text_response"] = answer
            # messages_to_add_to_stored_history contient déjà le message user et la réponse assistant

        update_user_conversation(user_id, messages_to_add_to_stored_history)
        return response_data

    except Exception as e:
        print(f"ERREUR MAJEURE[ask_gpt] pour user_id '{user_id}': {e}\n{traceback.format_exc()}")
        response_data["text_response"] = "Désolé, une erreur majeure est survenue lors du traitement de votre demande."
        # Ne pas ajouter l'erreur technique à l'historique de conversation de l'utilisateur
        return response_data