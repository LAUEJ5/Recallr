from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from deepgram import Deepgram
import os
from utils.compare import compare_transcript
from dotenv import load_dotenv

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
dg_client = Deepgram(DEEPGRAM_API_KEY)

app = FastAPI()

# Allow frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🎤 Client connected to /ws")

    dg_connection = None
    reference_script = []
    word_index = 0

    try:
        while True:
            message = await websocket.receive()

            if "text" in message:
                data = json.loads(message["text"])

                if data.get("type") == "script":
                    # Receive the reference script once
                    reference_script = data["payload"].split()
                    print(f"📜 Script received with {len(reference_script)} words")

                    # Initialize Deepgram connection
                    dg_connection = await dg_client.transcription.live({
                        "punctuate": True,
                        "interim_results": True
                    })

                    # Start listening to Deepgram responses
                    async def handle_transcripts():
                        nonlocal word_index
                        async for response in dg_connection:
                            words = response.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "").split()
                            feedback = compare_transcript(words, reference_script[word_index:])
                            word_index += len(words)
                            await websocket.send_text(json.dumps({"type": "transcript", "payload": feedback}))

                    asyncio.create_task(handle_transcripts())

                elif data.get("type") == "end":
                    print("🔚 Ending session")
                    break

            elif "bytes" in message:
                # Audio chunk
                if dg_connection:
                    await dg_connection.send(message["bytes"])

    except WebSocketDisconnect:
        print("⚠️ Client disconnected")
    finally:
        if dg_connection:
            await dg_connection.finish()
        await websocket.close()

@app.websocket("/listen")
async def log_audio_chunks(websocket: WebSocket):
    await websocket.accept()
    print("🧪 Client connected to /listen (debug)")

    try:
        while True:
            audio_chunk = await websocket.receive_bytes()
            print(f"🎧 Received {len(audio_chunk)} bytes of audio")
    except WebSocketDisconnect:
        print("🛑 /listen client disconnected")
    finally:
        await websocket.close()
