from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import JSONResponse
import tempfile
import os
import base64
import traceback # Pour un logging d'erreur plus détaillé

# Assure-toi que le chemin vers ton module utils est correct
# Si utils.py est dans un dossier "app" au même niveau que main.py :
from app.utils import transcribe_audio, ask_gpt, synthesize_speech
# Si utils.py est au même niveau que main.py (peu courant pour "app."), ce serait:
# from utils import transcribe_audio, ask_gpt, synthesize_speech

app = FastAPI()

@app.post("/process-voice")
async def process_voice(
    file: UploadFile = File(...),
    lat: float = Form(None),
    lng: float = Form(None),
    user_id: str = Form("default_user") # Ajout d'un user_id pour l'historique de conversation
):
    temp_audio_path = None
    user_transcript = "[Transcription non effectuée ou échouée]" # Valeur par défaut

    try:
        original_filename = file.filename
        if not original_filename: # Au cas où le client n'enverrait pas de nom de fichier
            original_filename = "audio.unknown" # Fallback
        
        print(f"INFO[main.process_voice]: Requête reçue pour user_id: {user_id}")
        print(f"DEBUG[main.process_voice]: Nom de fichier original reçu: '{original_filename}', Type: {file.content_type}")

        # Déterminer l'extension pour le fichier temporaire, et pour l'API OpenAI
        # On se fie d'abord à l'extension du nom de fichier envoyé par le client
        # puis au content_type si l'extension manque ou est suspecte.
        
        # Nom de fichier à utiliser pour l'API OpenAI (doit avoir une extension valide)
        filename_for_api = original_filename
        
        # Suffixe pour le fichier temporaire sur le disque
        # (peut être différent de l'extension pour l'API si on veut forcer)
        _root, current_ext_for_api = os.path.splitext(filename_for_api)
        
        # Liste des extensions valides pour Whisper
        valid_extensions = ['.flac', '.m4a', '.mp3', '.mp4', '.mpeg', '.mpga', '.oga', '.ogg', '.wav', '.webm']

        if current_ext_for_api.lower() not in valid_extensions:
            print(f"WARN[main.process_voice]: Extension '{current_ext_for_api}' de '{filename_for_api}' non valide ou manquante. Tentative de déduction via content_type.")
            if file.content_type == "audio/wav" or file.content_type == "audio/x-wav":
                file_extension_for_temp = ".wav"
                filename_for_api = _root + ".wav" if _root else "audio.wav"
            elif file.content_type in ["audio/m4a", "audio/mp4", "audio/x-m4a"]:
                file_extension_for_temp = ".m4a"
                filename_for_api = _root + ".m4a" if _root else "audio.m4a"
            elif file.content_type == "audio/webm":
                file_extension_for_temp = ".webm"
                filename_for_api = _root + ".webm" if _root else "audio.webm"
            elif file.content_type == "audio/mpeg": # Pour mp3
                file_extension_for_temp = ".mp3"
                filename_for_api = _root + ".mp3" if _root else "audio.mp3"
            elif file.content_type == "audio/ogg":
                file_extension_for_temp = ".ogg"
                filename_for_api = _root + ".ogg" if _root else "audio.ogg"
            else:
                print(f"WARN[main.process_voice]: Type de contenu '{file.content_type}' non explicitement mappé. Fallback à '.wav' pour le fichier temporaire et API.")
                file_extension_for_temp = ".wav"
                filename_for_api = "audio.wav" # Nom de fichier sûr pour l'API
        else:
            file_extension_for_temp = current_ext_for_api.lower()

        print(f"DEBUG[main.process_voice]: Nom de fichier pour API: '{filename_for_api}', Suffixe fichier temp: '{file_extension_for_temp}'")

        # Créer le fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension_for_temp) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_audio_path = tmp.name
        print(f"DEBUG[main.process_voice]: Fichier audio temporaire sauvegardé: '{temp_audio_path}'")

        # Transcrire
        user_transcript = await transcribe_audio(temp_audio_path, original_filename_for_api=filename_for_api)
        print(f"🎙️ Transcrit pour user_id '{user_id}': {user_transcript}")

        # Demander à GPT
        assistant_response_data = await ask_gpt(user_transcript, lat=lat, lng=lng, user_id=user_id)
        assistant_text_response = assistant_response_data.get("text_response")
        action_data = assistant_response_data.get("action_data")

        # Logique de fallback pour assistant_text_response si vide
        if not assistant_text_response and action_data:
            assistant_text_response = "Ok." # Ou un autre message par défaut pour une action
        elif not assistant_text_response and not action_data:
            assistant_text_response = "Je n'ai pas compris ou je n'ai rien à ajouter."

        print(f"🤖 Réponse Assistant pour user_id '{user_id}': {assistant_text_response}")
        if action_data:
            print(f"🎬 Action Assistant pour user_id '{user_id}': {action_data}")

        # Synthétiser la parole
        audio_base64_response = ""
        if assistant_text_response: # Seulement si il y a du texte à dire
            mp3_path_response = await synthesize_speech(assistant_text_response)
            if mp3_path_response:
                try:
                    with open(mp3_path_response, "rb") as f_mp3:
                        audio_base64_response = base64.b64encode(f_mp3.read()).decode("utf-8")
                except Exception as e_mp3_read:
                    print(f"ERREUR[main.process_voice] lecture fichier MP3 généré: {e_mp3_read}")
                finally: # Assurer la suppression du fichier MP3 temporaire
                    if os.path.exists(mp3_path_response):
                        try:
                            os.remove(mp3_path_response)
                        except Exception as e_mp3_remove:
                             print(f"ERREUR[main.process_voice] suppression fichier MP3 {mp3_path_response}: {e_mp3_remove}")
            else:
                print(f"WARN[main.process_voice]: synthesize_speech n'a pas retourné de chemin pour '{assistant_text_response}'")
        
        return JSONResponse(content={
            "transcript": user_transcript,
            "response_text": assistant_text_response,
            "audio_base64": audio_base64_response,
            "action_data": action_data
        })

    except Exception as e:
        print(f"ERREUR MAJEURE[main.process_voice] pour user_id '{user_id}': {e}")
        traceback.print_exc() # Imprime la stack trace complète dans les logs du serveur

        error_message_for_tts = "Désolé, une erreur interne majeure est survenue."
        audio_base64_error = ""
        # Tentative de synthèse du message d'erreur
        try:
            mp3_path_error = await synthesize_speech(error_message_for_tts)
            if mp3_path_error:
                with open(mp3_path_error, "rb") as f_error:
                    audio_base64_error = base64.b64encode(f_error.read()).decode("utf-8")
                if os.path.exists(mp3_path_error): os.remove(mp3_path_error)
        except Exception as e_tts_err:
            print(f"ERREUR[main.process_voice] lors de la synthèse du message d'erreur TTS: {e_tts_err}")

        return JSONResponse(
            status_code=500,
            content={
                "transcript": user_transcript, # Peut être la valeur par défaut ou une transcription partielle
                "response_text": error_message_for_tts,
                "audio_base64": audio_base64_error,
                "action_data": None
            }
        )
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
                print(f"DEBUG[main.process_voice]: Fichier audio temporaire '{temp_audio_path}' supprimé.")
            except Exception as e_remove:
                print(f"ERREUR[main.process_voice] lors de la suppression du fichier temporaire '{temp_audio_path}': {e_remove}")

@app.post("/tts-only")
async def tts_only(request: Request):
    mp3_path = None
    try:
        data = await request.json()
        text_to_synthesize = data.get("text", "")
        if not text_to_synthesize.strip():
            return JSONResponse(status_code=400, content={"error": "Le texte à synthétiser ne peut pas être vide."})

        mp3_path = await synthesize_speech(text_to_synthesize)
        if not mp3_path: # Si synthesize_speech retourne None (erreur)
            return JSONResponse(status_code=500, content={"error": "Erreur lors de la génération de l'audio."})

        with open(mp3_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")
        
        return {"audio_base64": audio_base64}
    except Exception as e:
        print(f"ERREUR[main.tts_only]: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "Erreur interne du serveur lors du TTS."})
    finally:
        if mp3_path and os.path.exists(mp3_path):
            try:
                os.remove(mp3_path)
            except Exception as e_remove_tts:
                 print(f"ERREUR[main.tts_only] suppression fichier MP3 {mp3_path}: {e_remove_tts}")


@app.post("/transcribe-only")
async def transcribe_only(file: UploadFile = File(...)):
    temp_path = None
    try:
        original_filename = file.filename
        if not original_filename: original_filename = "audio.unknown"
        print(f"DEBUG[main.transcribe_only]: Nom de fichier original reçu: '{original_filename}', Type: {file.content_type}")

        filename_for_api = original_filename
        _root, current_ext_for_api = os.path.splitext(filename_for_api)
        valid_extensions = ['.flac', '.m4a', '.mp3', '.mp4', '.mpeg', '.mpga', '.oga', '.ogg', '.wav', '.webm']

        if current_ext_for_api.lower() not in valid_extensions:
            if file.content_type == "audio/wav" or file.content_type == "audio/x-wav": file_extension_for_temp = ".wav"; filename_for_api = _root + ".wav" if _root else "audio.wav"
            elif file.content_type in ["audio/m4a", "audio/mp4", "audio/x-m4a"]: file_extension_for_temp = ".m4a"; filename_for_api = _root + ".m4a" if _root else "audio.m4a"
            elif file.content_type == "audio/webm": file_extension_for_temp = ".webm"; filename_for_api = _root + ".webm" if _root else "audio.webm"
            else: file_extension_for_temp = ".wav"; filename_for_api = "audio.wav"
        else:
            file_extension_for_temp = current_ext_for_api.lower()
        
        print(f"DEBUG[main.transcribe_only]: Nom pour API: '{filename_for_api}', Suffixe temp: '{file_extension_for_temp}'")

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension_for_temp) as tmp:
            tmp.write(await file.read())
            temp_path = tmp.name
        
        transcript_text = await transcribe_audio(temp_path, original_filename_for_api=filename_for_api)
        return {"transcript_text": transcript_text}
    except Exception as e:
        print(f"ERREUR[main.transcribe_only]: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Erreur interne du serveur lors de la transcription: {str(e)}"})
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e_remove_transcribe_only:
                print(f"ERREUR[main.transcribe_only] suppression fichier {temp_path}: {e_remove_transcribe_only}")