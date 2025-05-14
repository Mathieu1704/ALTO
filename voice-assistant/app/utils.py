import os
import time
import tempfile
import requests
from datetime import datetime, timedelta
import json # NOUVEAU: Pour parser les arguments de fonction de manière plus sûre

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
ASSISTANT_ID = None # Non utilisé dans ce code, peut-être pour une implémentation Assistants API ?

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
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Brussels"}, # Pensez à gérer les fuseaux horaires dynamiquement si besoin
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
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00")) # Assurer la compatibilité avec fromisoformat
            # TODO: Afficher dans le fuseau horaire local de l'utilisateur si possible
            message += f"• {event.get('summary', '(Sans titre)')} le {start_dt.strftime('%d/%m')} à {start_dt.strftime('%H:%M')}\n"

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
        # Obtenir le début et la fin de la journée dans le fuseau horaire local de l'utilisateur (ici supposé Europe/Brussels pour la cohérence avec l'ajout)
        # Pour une solution plus robuste, le fuseau horaire de l'utilisateur devrait être connu.
        # Pour simplifier, on utilise UTC pour timeMin et timeMax, ce qui peut décaler les "événements d'aujourd'hui" selon le fuseau de l'utilisateur.
        # Une meilleure approche serait de demander le fuseau horaire au client ou de le déduire.
        now_utc = datetime.utcnow()
        start_of_day_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day_utc = start_of_day_utc + timedelta(days=1)

        time_min_iso = start_of_day_utc.isoformat() + 'Z'
        time_max_iso = end_of_day_utc.isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min_iso,
            timeMax=time_max_iso,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events:
            return "Tu n'as aucun événement prévu aujourd'hui."

        result = "Voici tes événements pour aujourd'hui :\n"
        for event in events:
            start_str = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'Sans titre')
            
            # Convertir en objet datetime pour formater l'heure correctement
            if 'T' in start_str: # C'est un dateTime
                dt_obj = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                # Afficher l'heure dans un format local (nécessiterait pytz ou similaire pour une conversion de fuseau correcte)
                # Pour l'instant, on affiche l'heure telle quelle (probablement UTC ou le fuseau de l'événement)
                heure = dt_obj.strftime("%H:%M")
            else: # C'est une date (événement sur toute la journée)
                heure = "toute la journée"
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
    print(f"📤 Requête Google Maps: origin={origin}, destination={destination}, mode={mode}")
    response = requests.get(url, params=params)
    data = response.json()

    print(f"📥 Réponse Google Maps - status: {data.get('status')}")
    if "error_message" in data:
        print(f"🛑 Erreur Google Maps: {data['error_message']}")

    if data.get("status") != "OK" or not data.get("routes"):
        return ("Je n’ai pas pu obtenir l’itinéraire.", None)
    try:
        leg = data["routes"][0]["legs"][0]
        # summary = ( # Ce résumé n'est plus directement utilisé si on ouvre Maps
        #     f"Depuis votre position actuelle jusqu’à {leg['end_address']}, "
        #     f"il faut environ {leg['duration']['text']} pour parcourir {leg['distance']['text']}."
        # )
        maps_url = (
            f"https://www.google.com/maps/dir/?api=1&origin={origin}"
            f"&destination={destination.replace(' ', '+')}&travelmode={mode}" # MODIFIÉ: encodage simple de la destination
        )
        # Le texte de confirmation sera géré par GPT ou un message standard.
        return ("Ok, c’est parti pour votre itinéraire !", maps_url)
    except Exception as e:
        print(f"⚠️ Erreur lors de l'analyse des données Google Maps: {e}")
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
    "description": "Ajoute un événement dans le Google Calendar de l'utilisateur. Demande toujours confirmation avant d'appeler cette fonction.",
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Titre de l'événement"},
            "start_time": {
                "type": "string",
                "description": "Date et heure ISO ex: 2024-06-10T14:00:00 (utiliser l'heure actuelle si non spécifié pour 'maintenant' ou 'tout de suite')"
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
    "parameters": {"type": "object", "properties": {}}
}
get_directions_function = { # Cette fonction peut être appelée par GPT si la détection manuelle échoue ou pour plus de flexibilité
    "name": "get_directions",
    "description": "Fournit un itinéraire. Si l'origine est la position actuelle de l'utilisateur, le frontend fournira les coordonnées GPS.",
    "parameters": {
        "type": "object",
        "properties": {
            # "origin" is implicitly user's current location if lat/lng are provided to ask_gpt
            "destination": {
                "type": "string",
                "description": "Adresse ou lieu d’arrivée (ex: Gare de Mons)"
            },
            "mode": {
                "type": "string",
                "enum": ["walking", "driving", "transit"],
                "description": "Mode de transport (défaut: walking)",
                "default": "walking"
            }
        },
        "required": ["destination"]
    }
}

# NOUVEAU: Fonction pour préparer l'envoi de message
prepare_send_message_function = {
    "name": "prepare_send_message",
    "description": "Prépare l'envoi d'un message à un contact. Collecte le nom du destinataire et le contenu du message. Si l'un des deux manque, demande à l'utilisateur de le fournir avant d'appeler cette fonction. L'application se chargera de trouver le contact et d'ouvrir l'application de messagerie.",
    "parameters": {
        "type": "object",
        "properties": {
            "recipient_name": {"type": "string", "description": "Nom du contact à qui envoyer le message."},
            "message_content": {"type": "string", "description": "Contenu du message à envoyer."}
        },
        "required": ["recipient_name", "message_content"]
    }
}

# 🧠 Mémoire de conversation
conversation_history = [ # MODIFIÉ: Renommé pour plus de clarté
    {"role": "system", "content": (
        "Tu es Alto, un assistant vocal intelligent, connecté et utile. "
        "Tu es concis et vas droit au but. "
        "Si l'utilisateur veut envoyer un message mais ne précise pas le destinataire ou le contenu, demande-lui ces informations avant d'utiliser la fonction 'prepare_send_message'. "
        "Si l'utilisateur demande un itinéraire, la position actuelle est fournie par le système. "
        "Pour les événements de calendrier, si l'utilisateur dit 'maintenant' ou 'tout de suite', utilise l'heure actuelle pour 'start_time'. "
        "Fuseau horaire par défaut pour les événements : Europe/Brussels."
        "Demande toujours confirmation avant d'ajouter un événement au calendrier."
    )}
]

# 💬 Dialogue principal
async def ask_gpt(prompt: str, lat: float = None, lng: float = None, user_id: str = "default_user"): # user_id pour future gestion multi-utilisateurs de la conversation
    # NOTE: La gestion de 'conversation_history' devrait être propre à chaque utilisateur.
    # Pour l'instant, elle est globale, ce qui n'est pas idéal pour plusieurs utilisateurs simultanés.
    # Une solution simple serait de passer `conversation_history` en argument ou de la stocker dans un dict avec user_id comme clé.

    # Utilisation d'un chemin relatif pour les imports si ce fichier est dans un sous-module
    # from app.utils import ( ... ) # Supposé que les fonctions sont dans ce même fichier maintenant

    # MODIFIÉ: La conversation est passée directement
    current_conversation = list(conversation_history) # Copie pour cette session
    current_conversation.append({"role": "user", "content": prompt})
    
    # MODIFIÉ: Réponse structurée
    response_data = {
        "text_response": None, # Réponse textuelle à vocaliser
        "action_data": None    # Action spécifique pour le client (maps, message, etc.)
    }

    # 🔍 Détection manuelle d'intention de déplacement (prioritaire)
    # On pourrait aussi laisser GPT gérer ça avec get_directions_function, mais cette détection manuelle est plus directe.
    keywords_destination = ["je veux aller", "je dois aller", "emmène-moi", "rends-toi", "direction", "aller à", "je vais à", "me rendre à", "itinéraire vers"]
    if any(k in prompt.lower() for k in keywords_destination) and lat is not None and lng is not None:
        # 🧠 GPT utilisé uniquement pour extraire la destination proprement
        try:
            destination_query_completion = await client.chat.completions.create(
                model="gpt-4o", # ou gpt-3.5-turbo pour plus de rapidité/coût moindre
                messages=[
                    {"role": "system", "content": "Tu es un extracteur de destination. Extrais uniquement le nom du lieu ou l'adresse de destination à partir de la requête de l'utilisateur. Ne rajoute aucune politesse ou phrase supplémentaire. Exemple: si l'utilisateur dit 'Emmène-moi à la Gare du Nord à Paris', tu réponds 'Gare du Nord, Paris'."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            destination = destination_query_completion.choices[0].message.content.strip()
            if destination:
                print("📍 Destination extraite (détection manuelle) :", destination)
                summary_text, maps_url = get_directions_from_coords(lat, lng, destination) # mode par défaut "walking"
                if maps_url:
                    response_data["text_response"] = summary_text # ou un message plus générique comme "Ok, voici l'itinéraire."
                    response_data["action_data"] = {"type": "OPEN_MAPS", "payload": {"url": maps_url}}
                    # On n'ajoute pas cette interaction spécifique à l'historique GPT principal, car c'est géré "en dehors".
                    # Ou alors, on pourrait l'ajouter pour le contexte futur. Pour l'instant, on la garde simple.
                    return response_data 
                else:
                    response_data["text_response"] = summary_text # Contient le message d'erreur de get_directions_from_coords
                    return response_data
            else:
                print("⚠️ La destination extraite par GPT était vide.")
        except Exception as e:
            print(f"💥 Erreur lors de l'extraction de la destination : {e}")
            response_data["text_response"] = "Je n'ai pas bien compris la destination. Pouvez-vous répéter ?"
            return response_data


    # 🤖 Sinon, requête GPT standard avec function calling
    try:
        gpt_response = await client.chat.completions.create(
            model="gpt-4o",
            messages=current_conversation,
            tools=[ # MODIFIÉ: "functions" est déprécié, utiliser "tools"
                {"type": "function", "function": search_web_function},
                {"type": "function", "function": weather_function},
                {"type": "function", "function": calendar_add_function},
                {"type": "function", "function": calendar_read_function},
                {"type": "function", "function": calendar_get_function},
                {"type": "function", "function": get_directions_function},
                {"type": "function", "function": prepare_send_message_function} # NOUVEAU
            ],
            tool_choice="auto" # MODIFIÉ: "function_call" est déprécié
        )
        message = gpt_response.choices[0].message

        tool_calls = message.tool_calls # MODIFIÉ

        if tool_calls:
            current_conversation.append(message) # Ajoute la réponse de l'assistant (avec les tool_calls)
            
            available_functions = {
                "search_web": search_web,
                "get_weather": get_weather,
                "add_event_to_calendar": add_event_to_calendar,
                "get_upcoming_events": get_upcoming_events,
                "get_today_events": get_today_events,
                # get_directions est un cas spécial car il a besoin de lat/lng
                # prepare_send_message est aussi un cas spécial
            }

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments) # MODIFIÉ: json.loads est plus sûr que eval()

                print(f"🛠️ Appel de fonction détecté: {function_name} avec args: {function_args}")

                function_response_content = None

                if function_name == "prepare_send_message":
                    # Cette fonction ne s'exécute pas côté serveur pour faire une action.
                    # Elle instruit le client.
                    response_data["text_response"] = f"Ok, je prépare un message pour {function_args.get('recipient_name')}." # Message de confirmation
                    response_data["action_data"] = {
                        "type": "PREPARE_SEND_MESSAGE",
                        "payload": {
                            "recipient_query": function_args.get("recipient_name"),
                            "message_content": function_args.get("message_content")
                        }
                    }
                    # On n'a pas besoin de `function_response_content` car on ne fait pas de second appel à GPT ici.
                    # La réponse est directement pour le client.
                    # On ajoute quand même un message "fonction" pour l'historique, indiquant que l'action a été déléguée.
                    function_response_content = "Action de préparation de message déléguée au client."
                
                elif function_name == "get_directions":
                    if lat is not None and lng is not None:
                        destination = function_args.get("destination")
                        mode = function_args.get("mode", "walking")
                        summary_text, maps_url = get_directions_from_coords(lat, lng, destination, mode)
                        if maps_url:
                            response_data["text_response"] = summary_text
                            response_data["action_data"] = {"type": "OPEN_MAPS", "payload": {"url": maps_url}}
                            function_response_content = f"Itinéraire vers {destination} fourni et URL Google Maps générée."
                        else:
                            function_response_content = summary_text # Message d'erreur
                    else:
                        function_response_content = "Je n'ai pas pu obtenir votre position pour calculer l'itinéraire."
                
                elif function_name in available_functions:
                    # Appel des fonctions "classiques"
                    try:
                        function_to_call = available_functions[function_name]
                        # Gestion des arguments avec **function_args
                        function_response_content = function_to_call(**function_args)
                    except TypeError as te:
                        print(f"Erreur d'arguments pour {function_name}: {te}")
                        function_response_content = f"Erreur d'arguments en appelant {function_name}."
                    except Exception as e:
                        print(f"Erreur pendant l'exécution de {function_name}: {e}")
                        function_response_content = f"Erreur lors de l'exécution de {function_name}."
                else:
                    function_response_content = f"Fonction {function_name} non reconnue ou non implémentée pour un appel direct."

                current_conversation.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response_content,
                })

            # Si une action client a déjà été définie (prepare_send_message, get_directions), on ne fait pas de second appel
            if response_data["action_data"]:
                if not response_data["text_response"]: # Si GPT n'a pas donné de texte initial
                     response_data["text_response"] = "Ok." # Fournir un texte par défaut
                conversation_history.extend(current_conversation[len(conversation_history):]) # Mettre à jour l'historique global
                return response_data

            # Faire un second appel pour obtenir une réponse en langage naturel basée sur le résultat de la fonction
            followup_response = await client.chat.completions.create(
                model="gpt-4o",
                messages=current_conversation
            )
            answer = followup_response.choices[0].message.content.strip()
            response_data["text_response"] = answer
            current_conversation.append({"role": "assistant", "content": answer})
        
        else: # Pas d'appel de fonction, réponse directe de GPT
            answer = message.content.strip()
            response_data["text_response"] = answer
            current_conversation.append({"role": "assistant", "content": answer})

        # Mettre à jour l'historique global
        # Ceci est une simplification. Idéalement, l'historique serait géré par session/utilisateur.
        conversation_history.extend(current_conversation[len(conversation_history):])
        # Limiter la taille de l'historique pour éviter des coûts/latences excessifs
        if len(conversation_history) > 20: # Garder le message système + 19 derniers échanges
            conversation_history = [conversation_history[0]] + conversation_history[-19:]

        return response_data

    except Exception as e:
        print(f"💥 Erreur majeure dans ask_gpt: {e}")
        response_data["text_response"] = "Désolé, une erreur est survenue. Pouvez-vous réessayer ?"
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
    # Ajout d'une petite pause pour un effet plus naturel, si désiré
    # input_text = "Hum... " + text if not text.lower().startswith(("ok", "d'accord", "voici", "très bien")) else text
    input_text = text
    
    # Vérifier si le texte n'est pas vide ou juste des espaces
    if not input_text or input_text.isspace():
        print("⚠️ Texte vide fourni à synthesize_speech, retour d'un fichier audio vide.")
        # Créer un fichier MP3 silencieux ou retourner une erreur gérée par le client
        # Pour l'instant, on pourrait retourner un fichier avec un son très court de silence.
        # Ou simplement ne pas générer de fichier et le client doit gérer ça.
        # Alternative la plus simple:
        input_text = " " # TTS-1 peut générer un son pour un espace, ou une erreur gérable

    try:
        speech = await client.audio.speech.create(
            model="tts-1", # ou tts-1-hd pour meilleure qualité
            voice="shimmer", # ou une autre voix: alloy, echo, fable, onyx, nova
            input=input_text,
            response_format="mp3" # s'assurer du format
        )
        # Utiliser BytesIO pour éviter d'écrire sur le disque si ce n'est pas nécessaire
        # Mais pour le retour au client FastAPI, un fichier temporaire est souvent plus simple
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        # speech.write_to_file(temp_file.name) # Méthode directe de l'objet response
        temp_file.write(speech.content) # Accès direct au contenu binaire
        temp_file.close() # Important de fermer avant de retourner le nom
        return temp_file.name
    except Exception as e:
        print(f"Erreur lors de la synthèse vocale (TTS OpenAI): {e}")
        # Gérer le cas où `input_text` est vide ou problématique pour l'API TTS
        # Par exemple, l'API peut rejeter une chaîne vide.
        if "input is too long" in str(e).lower() or "invalid text" in str(e).lower():
             # Essayer de synthétiser un message d'erreur générique
            try:
                error_speech = await client.audio.speech.create(model="tts-1", voice="shimmer", input="Je ne peux pas dire cela.")
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                temp_file.write(error_speech.content)
                temp_file.close()
                return temp_file.name
            except:
                pass # Si même ça échoue, on ne peut plus rien faire ici.
        return None # Indiquer une erreur au code appelant