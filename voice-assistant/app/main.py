from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import JSONResponse
import tempfile
import os
import base64
from app.utils import transcribe_audio, ask_gpt, synthesize_speech # Assurez-vous que ce chemin est correct

app = FastAPI()

@app.post("/process-voice")
async def process_voice(
    file: UploadFile = File(...),
    lat: float = Form(None), # Latitude de l'utilisateur
    lng: float = Form(None)  # Longitude de l'utilisateur
):
    # 1. Enregistrer temporairement le fichier audio reçu
    # Utilisation d'un suffixe plus générique si le format peut varier, bien que Whisper s'attende à des formats courants.
    # Si vous êtes sûr que c'est du .wav, vous pouvez garder .wav
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmpaudio") as tmp:
            content = await file.read()
            tmp.write(content)
            temp_audio_path = tmp.name
    except Exception as e:
        print(f"Erreur lors de la lecture ou sauvegarde du fichier uploadé: {e}")
        return JSONResponse(status_code=500, content={"error": "Erreur traitement fichier audio"})

    # 2. Transcrire l'audio en texte
    user_transcript = "" # Initialiser au cas où la transcription échoue
    try:
        user_transcript = await transcribe_audio(temp_audio_path)
        print(f"🎙️ Transcrit : {user_transcript}")
        if not user_transcript: # Si la transcription est vide (ex: silence)
            print("⚠️ Transcription vide, peut-être un silence.")
            # Vous pourriez vouloir gérer ce cas spécifiquement, ex: retourner un message "Je n'ai rien entendu"
            # Pour l'instant, on laisse ask_gpt gérer une chaîne vide si c'est le cas.
    except Exception as e:
        print(f"Erreur de transcription: {e}")
        os.remove(temp_audio_path) # Nettoyer le fichier temporaire
        return JSONResponse(status_code=500, content={"error": "Erreur de transcription audio"})

    # 3. Envoyer le texte transcrit (et la géolocalisation) à GPT pour obtenir une réponse
    assistant_response_data = None
    try:
        # MODIFIÉ: ask_gpt retourne maintenant un dictionnaire plus structuré
        assistant_response_data = await ask_gpt(user_transcript, lat=lat, lng=lng)
        
        # Extraire le texte de la réponse et les données d'action
        assistant_text_response = assistant_response_data.get("text_response")
        action_data = assistant_response_data.get("action_data") # Peut être None

        if not assistant_text_response and not action_data:
            # Si ask_gpt retourne une réponse invalide ou vide sans action
            print("⚠️ Réponse vide ou invalide de ask_gpt.")
            assistant_text_response = "Je ne sais pas quoi répondre à cela." # Réponse par défaut
        elif not assistant_text_response and action_data:
            # Si il y a une action mais pas de texte (ex: "Ok." implicite)
            assistant_text_response = "Ok." # Ou un autre texte par défaut pour l'action

        print(f"🤖 Réponse de l'assistant (texte) : {assistant_text_response}")
        if action_data:
            print(f"🎬 Action de l'assistant : {action_data}")

    except Exception as e:
        print(f"Erreur lors de l'appel à ask_gpt: {e}")
        os.remove(temp_audio_path)
        # Retourner une erreur générique que le client peut vocaliser
        error_message_for_tts = "Désolé, une erreur interne est survenue."
        mp3_path_error = await synthesize_speech(error_message_for_tts)
        audio_base64_error = ""
        if mp3_path_error:
            with open(mp3_path_error, "rb") as f_error:
                audio_base64_error = base64.b64encode(f_error.read()).decode("utf-8")
            os.remove(mp3_path_error)
        
        return JSONResponse(
            status_code=500, 
            content={
                "transcript": user_transcript,
                "response": error_message_for_tts,
                "audio": audio_base64_error,
                "action_data": None # Pas d'action en cas d'erreur
            }
        )

    # 4. Synthétiser la réponse textuelle de l'assistant en audio
    mp3_path_response = None
    audio_base64_response = ""
    try:
        if assistant_text_response: # Ne synthétiser que s'il y a du texte
            mp3_path_response = await synthesize_speech(assistant_text_response)
            if mp3_path_response:
                with open(mp3_path_response, "rb") as f:
                    audio_base64_response = base64.b64encode(f.read()).decode("utf-8")
                os.remove(mp3_path_response) # Nettoyer le fichier MP3 temporaire
            else:
                print("⚠️ La synthèse vocale n'a pas retourné de chemin de fichier.")
                # Peut-être fournir un audio pré-enregistré d'erreur de TTS ? Ou laisser vide.
        else:
            print("ℹ️ Pas de texte à synthétiser pour la réponse vocale.")

    except Exception as e:
        print(f"Erreur de synthèse vocale: {e}")
        # Si la synthèse échoue, on envoie quand même le texte et l'action, mais sans audio.
        # Le client devra gérer l'absence d'audio.
        # On pourrait aussi tenter de synthétiser un message d'erreur ici.

    # 5. Nettoyer le fichier audio d'entrée initial
    os.remove(temp_audio_path)

    # 6. Retourner la réponse JSON au client
    # MODIFIÉ: Inclure la nouvelle structure de réponse
    return JSONResponse(content={
        "transcript": user_transcript,
        "response_text": assistant_text_response, # Renommé pour clarté (était "response")
        "audio_base64": audio_base64_response,    # Renommé pour clarté (était "audio")
        "action_data": action_data                # Nouvelle clé pour les actions client
    })


@app.post("/tts-only")
async def tts_only(request: Request):
    try:
        data = await request.json()
        text_to_synthesize = data.get("text", "")

        if not text_to_synthesize.strip():
            return JSONResponse(status_code=400, content={"error": "Le texte à synthétiser ne peut pas être vide."})

        mp3_path = await synthesize_speech(text_to_synthesize)
        if not mp3_path:
            return JSONResponse(status_code=500, content={"error": "Erreur lors de la synthèse vocale, aucun fichier audio généré."})

        with open(mp3_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")
        os.remove(mp3_path)

        return {"audio_base64": audio_base64} # MODIFIÉ: pour cohérence
    except Exception as e:
        print(f"Erreur dans tts-only: {e}")
        return JSONResponse(status_code=500, content={"error": f"Erreur interne du serveur: {str(e)}"})


@app.post("/transcribe-only")
async def transcribe_only(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmpaudio") as tmp:
            content = await file.read()
            tmp.write(content)
            temp_path = tmp.name

        transcript_text = await transcribe_audio(temp_path) # MODIFIÉ: pour cohérence
        os.remove(temp_path)

        return {"transcript_text": transcript_text} # MODIFIÉ: pour cohérence
    except Exception as e:
        print(f"Erreur dans transcribe-only: {e}")
        return JSONResponse(status_code=500, content={"error": f"Erreur interne du serveur: {str(e)}"})