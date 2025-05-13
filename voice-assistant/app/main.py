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

    # Envoie le texte et la géoloc au backend
    assistant_result = await ask_gpt(user_transcript, lat=lat, lng=lng)
    assistant_text = assistant_result["text"]
    maps_url = assistant_result.get("maps_url")
    print("🤖 Assistant :", assistant_text)
    print("📍 URL Google Maps :", maps_url)  # ⬅️ ajoute ceci

    mp3_path = await synthesize_speech(assistant_text)
    os.remove(temp_path)

    with open(mp3_path, "rb") as f:
        audio_base64 = base64.b64encode(f.read()).decode("utf-8")
    os.remove(mp3_path)

    return JSONResponse(content={
        "transcript": user_transcript,
        "response": assistant_text,
        "audio": audio_base64,
        "maps_url": maps_url
    })

@app.post("/tts-only")
async def tts_only(request: Request):
    data = await request.json()
    text = data.get("text", "")

    mp3_path = await synthesize_speech(text)

    with open(mp3_path, "rb") as f:
        audio_base64 = base64.b64encode(f.read()).decode("utf-8")
    os.remove(mp3_path)

    return {"audio": audio_base64}

@app.post("/transcribe-only")
async def transcribe_only(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        temp_path = tmp.name

    transcript = await transcribe_audio(temp_path)
    os.remove(temp_path)

    return {"transcript": transcript}
