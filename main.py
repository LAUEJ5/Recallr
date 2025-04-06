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
    print("✅ Client connected")

    dg_connection = None
    reference_script = []
    word_index = 0

    try:
        while True:
            message = await websocket.receive()

            if "text" in message:
                data = json.loads(message["text"])

                if data.get("type") == "script":
                    reference_script = data["payload"].split()
                    print(f"📜 Received script with {len(reference_script)} words")

                    # Initialize Deepgram
                    dg_connection = await dg_client.transcription.live({
                        "punctuate": True,
                        "interim_results": True
                    })

                    def on_transcript(response):
                        print("📝 Received response from Deepgram")
                        words = (
                            response.get("channel", {})
                            .get("alternatives", [{}])[0]
                            .get("transcript", "")
                            .split()
                        )
                        feedback = compare_transcript(words, reference_script[word_index:])
                        asyncio.create_task(
                            websocket.send_text(json.dumps({"type": "transcript", "payload": feedback}))
                        )

                    dg_connection.register_handler(on_transcript)

                elif data.get("type") == "end":
                    print("🛑 Ending session")
                    break

            elif "bytes" in message:
                if dg_connection is not None:
                    await dg_connection.send(message["bytes"])
                else:
                    print("⚠️ Tried to send audio before Deepgram was initialized")

    except WebSocketDisconnect:
        print("❌ Client disconnected")
    finally:
        if dg_connection:
            await dg_connection.finish()
        await websocket.close()
