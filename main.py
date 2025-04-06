from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from deepgram import Deepgram
from dotenv import load_dotenv
import os
import asyncio
import json
from utils.compare import compare_transcript

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
    deepgram_ready = asyncio.Event()

    try:
        while True:
            message = await websocket.receive()

            if "text" in message:
                data = json.loads(message["text"])

                if data.get("type") == "script":
                    reference_script = data["payload"].split()
                    print(f"📜 Received script with {len(reference_script)} words")

                    try:
                        # Create Deepgram live connection
                        dg_connection = await dg_client.transcription.live({
                            "punctuate": True,
                            "interim_results": True
                        })
                        print("🔌 Deepgram connection established")

                        def on_transcript(transcript, **kwargs):
                            print("📝 Deepgram transcript received")
                            words = (
                                transcript.get("channel", {})
                                .get("alternatives", [{}])[0]
                                .get("transcript", "")
                                .split()
                            )
                            feedback = compare_transcript(
                                ' '.join(reference_script[word_index:]),
                                ' '.join(words)
                            )
                            asyncio.create_task(websocket.send_text(json.dumps({
                                "type": "transcript",
                                "payload": feedback
                            })))

                        print("🔧 Registering transcript handler")
                        dg_connection.registerHandler(dg_connection.event.TRANSCRIPT_RECEIVED, on_transcript)

                        deepgram_ready.set()

                    except Exception as e:
                        print(f"❌ Error initializing Deepgram: {e}")
                        await websocket.close()
                        return

                elif data.get("type") == "end":
                    print("🛑 Session end requested")
                    break

            elif "bytes" in message:
                await deepgram_ready.wait()

                if dg_connection is None:
                    print("❗ Deepgram connection is None even after ready event!")
                    continue

                try:
                    print(f"🎤 Sending audio chunk to Deepgram: {len(message['bytes'])} bytes")
                    await dg_connection.send(message["bytes"])
                except Exception as e:
                    print(f"💥 Failed to send audio to Deepgram: {e}")

    except WebSocketDisconnect:
        print("❌ WebSocket disconnected")

    finally:
        if dg_connection:
            await dg_connection.finish()
            print("🔚 Deepgram connection closed")
        try:
            await websocket.close()
            print("🔒 WebSocket connection closed")
        except RuntimeError:
            print("⚠️ WebSocket was already closed")
