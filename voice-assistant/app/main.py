from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import JSONResponse
import tempfile
import os
import base64
from app.utils import transcribe_audio, ask_gpt, synthesize_speech

app = FastAPI()

@app.post("/process-voice")
async def process_voice(
    file: UploadFile = File(...),
    lat: float = Form(None),
    lng: float = Form(None)
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        temp_path = tmp.name

    user_transcript = await transcribe_audio(temp_path)
    print("🎙️ Transcrit :", user_transcript)

    # Appelle ask_gpt qui retourne maintenant une structure plus détaillée
    assistant_result = await ask_gpt(user_transcript, lat=lat, lng=lng)
    
    # NEW: Récupération des nouvelles clés de assistant_result
    text_to_speak = assistant_result.get("text_to_speak", "Je n'ai pas de réponse à vous donner.") # Texte pour TTS et affichage
    action_details = assistant_result.get("action") # Peut être None ou un objet {type: "...", data: {...}}

    print("🤖 Assistant (texte à vocaliser) :", text_to_speak)
    if action_details:
        print(f"🎬 Action détectée : {action_details.get('type')}")
        print(f"📊 Données de l'action : {action_details.get('data')}")
    else:
        print("🎬 Aucune action spécifique détectée.")


    # NEW: Utilisation de text_to_speak pour la synthèse vocale
    mp3_path = await synthesize_speech(text_to_speak)
    os.remove(temp_path) # Suppression du fichier audio temporaire de l'upload

    audio_base64 = ""
    if os.path.exists(mp3_path): # S'assurer que le fichier existe avant de lire
        with open(mp3_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")
        os.remove(mp3_path) # Suppression du fichier mp3 temporaire après lecture
    else:
        print(f"Erreur: Le fichier TTS {mp3_path} n'a pas été créé.")


    # NEW: Adaptation de la réponse JSON
    response_content = {
        "transcript": user_transcript,
        "response_text": text_to_speak, # Le texte que l'assistant doit prononcer / afficher
        "audio": audio_base64,
        "action": action_details # Envoie l'objet action complet au frontend
    }
    
    # Pour la compatibilité avec l'ancien frontend qui attendait "maps_url" directement:
    # On peut l'ajouter si l'action est de type "maps"
    # Cependant, il est préférable que le frontend s'adapte à la nouvelle structure "action"
    # if action_details and action_details.get("type") == "maps":
    #     response_content["maps_url"] = action_details.get("data", {}).get("maps_url")
    # else:
    #     response_content["maps_url"] = None


    return JSONResponse(content=response_content)

@app.post("/tts-only")
async def tts_only(request: Request):
    data = await request.json()
    text = data.get("text", "")
    if not text: # Petite validation
        return JSONResponse(status_code=400, content={"error": "No text provided for TTS."})

    mp3_path = await synthesize_speech(text)
    audio_base64 = ""
    if os.path.exists(mp3_path):
        with open(mp3_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode("utf-8")
        os.remove(mp3_path)
    else:
        print(f"Erreur: Le fichier TTS {mp3_path} n'a pas été créé pour tts-only.")
        # Peut-être retourner une erreur ici aussi ou un audio vide
        return JSONResponse(status_code=500, content={"error": "TTS generation failed."})


    return {"audio": audio_base64}

@app.post("/transcribe-only")
async def transcribe_only(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        temp_path = tmp.name

    transcript = await transcribe_audio(temp_path)
    os.remove(temp_path)

    return {"transcript": transcript}