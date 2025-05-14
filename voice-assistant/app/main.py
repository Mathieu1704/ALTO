from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import JSONResponse
import tempfile
import os
import base64
from app.utils import transcribe_audio, ask_gpt, synthesize_speech

app = FastAPI()

@app.post("/process-voice")
async def process_voice(
    file: UploadFile = File(...), # file contient file.filename et file.content_type
    lat: float = Form(None),
    lng: float = Form(None)
):
    temp_audio_path = None # Pour s'assurer qu'il est défini pour le bloc finally
    try:
        # Extraire l'extension du nom de fichier original envoyé par le client
        original_filename = file.filename
        _, file_extension = os.path.splitext(original_filename)

        # S'assurer que l'extension est l'une de celles supportées par Whisper
        # et qu'elle correspond bien à ce que le client est censé envoyer.
        # Notre client envoie .wav (iOS) ou .m4a (Android). Les deux sont supportés.
        # Si l'extension est vide ou invalide, on pourrait utiliser un fallback ou rejeter.
        if not file_extension or file_extension.lower() not in ['.flac', '.m4a', '.mp3', '.mp4', '.mpeg', '.mpga', '.oga', '.ogg', '.wav', '.webm']:
            print(f"Extension de fichier non valide ou manquante reçue: '{original_filename}'. Tentative avec '.m4a' par défaut.")
            # On pourrait essayer de déduire du content_type, mais l'extension est plus directe ici
            # car notre client la spécifie.
            # file_extension = ".m4a" # Un fallback possible.
            # Pour l'instant, on va se fier à ce que le client envoie.
            # Si original_filename est juste "audio" sans extension, file_extension sera vide.
            # Dans ce cas, il faut que le client envoie bien "audio.m4a" ou "audio.wav".
            if not file_extension: # Si vraiment aucune extension
                 # Tenter de déduire du content_type (peut être moins fiable)
                if file.content_type == "audio/wav":
                    file_extension = ".wav"
                elif file.content_type == "audio/m4a" or file.content_type == "audio/mp4": # mp4 est le conteneur pour m4a
                    file_extension = ".m4a"
                else:
                    print(f"Type de contenu non géré pour fallback: {file.content_type}")
                    file_extension = ".m4a" # Fallback ultime


        # Utiliser l'extension correcte pour le fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_audio_path = tmp.name
            print(f"Fichier audio temporaire sauvegardé sous: {temp_audio_path} (original: {original_filename})")


        user_transcript = await transcribe_audio(temp_audio_path) # On passe le chemin avec la bonne extension
        # Si transcribe_audio a besoin du nom de fichier original pour le passer à l'API OpenAI:
        # user_transcript = await transcribe_audio(temp_audio_path, original_filename=original_filename)

        print(f"🎙️ Transcrit : {user_transcript}")
        # ... (le reste de ta logique)

        assistant_response_data = await ask_gpt(user_transcript, lat=lat, lng=lng)
        
        assistant_text_response = assistant_response_data.get("text_response")
        action_data = assistant_response_data.get("action_data")

        if not assistant_text_response and not action_data:
            assistant_text_response = "Je ne sais pas quoi répondre à cela."
        elif not assistant_text_response and action_data:
            assistant_text_response = "Ok."

        print(f"🤖 Réponse de l'assistant (texte) : {assistant_text_response}")
        if action_data:
            print(f"🎬 Action de l'assistant : {action_data}")

        mp3_path_response = None
        audio_base64_response = ""
        if assistant_text_response:
            mp3_path_response = await synthesize_speech(assistant_text_response)
            if mp3_path_response:
                with open(mp3_path_response, "rb") as f_mp3:
                    audio_base64_response = base64.b64encode(f_mp3.read()).decode("utf-8")
                os.remove(mp3_path_response)
        
        return JSONResponse(content={
            "transcript": user_transcript,
            "response_text": assistant_text_response,
            "audio_base64": audio_base64_response,
            "action_data": action_data
        })

    except Exception as e:
        print(f"Erreur majeure dans process_voice: {e}") # Log l'erreur spécifique
        # En cas d'erreur, essayer de synthétiser un message d'erreur si possible
        error_message_for_tts = "Désolé, une erreur interne est survenue."
        mp3_path_error = await synthesize_speech(error_message_for_tts) # Peut aussi échouer
        audio_base64_error = ""
        if mp3_path_error:
            try:
                with open(mp3_path_error, "rb") as f_error:
                    audio_base64_error = base64.b64encode(f_error.read()).decode("utf-8")
                os.remove(mp3_path_error)
            except Exception as e_tts_file:
                print(f"Erreur gestion fichier TTS d'erreur: {e_tts_file}")

        return JSONResponse(
            status_code=500, # Indiquer clairement une erreur serveur
            content={
                "transcript": "Erreur de traitement",
                "response_text": error_message_for_tts,
                "audio_base64": audio_base64_error,
                "action_data": None
            }
        )
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path) # Assurer le nettoyage du fichier temporaire

# ... (tes autres routes tts-only et transcribe-only)
# Pour transcribe-only, la même logique d'extension s'appliquerait
@app.post("/transcribe-only")
async def transcribe_only(file: UploadFile = File(...)):
    temp_path = None
    try:
        original_filename = file.filename
        _, file_extension = os.path.splitext(original_filename)
        if not file_extension: # Fallback si besoin
            if file.content_type == "audio/wav": file_extension = ".wav"
            elif file.content_type == "audio/m4a" or file.content_type == "audio/mp4": file_extension = ".m4a"
            else: file_extension = ".m4a"

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            tmp.write(await file.read())
            temp_path = tmp.name

        transcript_text = await transcribe_audio(temp_path)
        return {"transcript_text": transcript_text}
    except Exception as e:
        print(f"Erreur dans transcribe-only: {e}")
        return JSONResponse(status_code=500, content={"error": f"Erreur interne du serveur: {str(e)}"})
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)