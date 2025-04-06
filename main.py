from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
from deepgram import Deepgram
from dotenv import load_dotenv
import os
import asyncio
import json
from utils.compare import compare_transcript  # returns List[Tuple[word, correct]]

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
    deepgram_ready = asyncio.Event()
    confirmed_words = []
    word_index = 0

    try:
        while True:
            try:
                message = await websocket.receive()
            except RuntimeError as e:
                print(f"⚠️ Client likely disconnected: {e}")
                break

            if "text" in message:
                data = json.loads(message["text"])

                if data.get("type") == "script":
                    reference_script = data["payload"].split()
                    confirmed_words = [(word, False) for word in reference_script]
                    print(f"📜 Received script with {len(reference_script)} words")

                    try:
                        dg_connection = await dg_client.transcription.live({
                            "punctuate": True,
                            "interim_results": True
                        })
                        print(f"🧪 dg_connection type: {type(dg_connection)}")
                        print(f"🧪 dg_connection.send: {getattr(dg_connection, 'send', None)}")

                        def on_transcript(transcript, **kwargs):
                            nonlocal word_index
                            print("📝 Deepgram transcript received")

                            words = (
                                transcript.get("channel", {})
                                .get("alternatives", [{}])[0]
                                .get("transcript", "")
                                .split()
                            )

                            feedback = compare_transcript(
                                reference_script[word_index:],  # expected
                                words  # said
                            )


                            for i, (matched_word, correct) in enumerate(feedback):
                                abs_index = word_index + i
                                if abs_index >= len(reference_script):
                                    break

                                expected_word = reference_script[abs_index]

                                if correct and matched_word.lower() == expected_word.lower() and abs_index == word_index:
                                    confirmed_words[abs_index] = (expected_word, True)
                                elif confirmed_words[abs_index][1] is False:
                                    confirmed_words[abs_index] = (expected_word, False)
                                else:
                                    break

                            while word_index < len(confirmed_words) and confirmed_words[word_index] == (reference_script[word_index], True):
                                word_index += 1

                            async def safe_send():
                                try:
                                    await websocket.send_text(json.dumps({
                                        "type": "transcript",
                                        "payload": confirmed_words
                                    }))
                                except Exception as e:
                                    print(f"⚠️ Failed to send transcript: {e}")

                            if websocket.client_state == WebSocketState.CONNECTED:
                                asyncio.create_task(safe_send())
                            else:
                                print("⚠️ Tried to send transcript, but WebSocket is closed.")

                        print("🔧 Registering transcript handler")
                        dg_connection.registerHandler(dg_connection.event.TRANSCRIPT_RECEIVED, on_transcript)

                        deepgram_ready.set()

                    except Exception as e:
                        print(f"❌ Error initializing Deepgram: {e}")
                        if websocket.client_state == WebSocketState.CONNECTED:
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
                    if hasattr(dg_connection, "send") and callable(dg_connection.send):
                        print(f"🎤 Sending audio chunk to Deepgram: {len(message['bytes'])} bytes")
                        dg_connection.send(message["bytes"])
                    else:
                        print("⚠️ Deepgram connection 'send' is not callable")
                except Exception as e:
                    print(f"💥 Failed to send audio to Deepgram: {e}")

    except WebSocketDisconnect:
        print("❌ WebSocket disconnected")

    finally:
        if dg_connection and hasattr(dg_connection, "finish"):
            try:
                await dg_connection.finish()
                print("🔚 Deepgram connection closed")
            except Exception as e:
                print(f"⚠️ Failed to close Deepgram connection: {e}")

        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
                print("🔒 WebSocket connection closed")
            else:
                print("⚠️ WebSocket already closed by client")
        except RuntimeError:
            print("⚠️ WebSocket was already closed")
