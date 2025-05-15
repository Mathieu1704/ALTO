from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import tempfile, os, base64

from app.utils import transcribe_audio, ask_gpt, synthesize_speech

app = FastAPI()

@app.post("/process-voice")
async def process_voice(
    file: UploadFile = File(...),
    lat: float = Form(None),
    lng: float = Form(None)
):
    # 1️⃣ Sauvegarde du WAV reçu
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        audio_path = tmp.name

    # 2️⃣ Transcription
    user_transcript = await transcribe_audio(audio_path)
    print("🎙️ Transcrit :", user_transcript)

    # 3️⃣ Appel à GPT pour texte + action
    assistant_result = await ask_gpt(user_transcript, lat=lat, lng=lng)
    text_to_speak = assistant_result.get("text_to_speak") or "Désolé, je n'ai pas de réponse."
    action_details = assistant_result.get("action")

    print("🤖 Réponse GPT :", text_to_speak)
    if action_details:
        print("🎬 Action :", action_details)

    # 4️⃣ Synthèse vocale
    mp3_path = await synthesize_speech(text_to_speak)
    os.remove(audio_path)

    audio_base64 = ""
    if os.path.exists(mp3_path):
        with open(mp3_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode()
        os.remove(mp3_path)
    else:
        print(f"Erreur TTS : fichier {mp3_path} introuvable.")

    # 5️⃣ Réponse JSON pour le front
    return JSONResponse({
        "transcript": user_transcript,
        "response_text": text_to_speak,
        "audio": audio_base64,
        "action": action_details
    })

@app.post("/tts-only")
async def tts_only(text: str = Form(...)):
    mp3_path = await synthesize_speech(text)

    if os.path.exists(mp3_path):
        with open(mp3_path, "rb") as f:
            audio = base64.b64encode(f.read()).decode()
        os.remove(mp3_path)
        return {"audio": audio}
    return JSONResponse(status_code=500, content={"error": "TTS generation failed."})

@app.post("/transcribe-only")
async def transcribe_only(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        audio_path = tmp.name

    transcript = await transcribe_audio(audio_path)
    os.remove(audio_path)
    return {"transcript": transcript}
