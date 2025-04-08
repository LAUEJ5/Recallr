from deepgram import Deepgram
from starlette.websockets import WebSocketState
from utils.compare import compare_transcript
import os
import asyncio
import json
from dotenv import load_dotenv

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
dg_client = Deepgram(DEEPGRAM_API_KEY)

async def init_deepgram(reference_script, confirmed_words, websocket, ready_event):
    word_index = 0

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
            print("🎧 Deepgram words:", words)

            feedback = compare_transcript(reference_script[word_index:], words)

            for i, (matched_word, correct) in enumerate(feedback):
                abs_index = word_index + i
                if abs_index >= len(reference_script):
                    break

                expected_word = reference_script[abs_index]

                if correct and matched_word.lower() == expected_word.lower():
                    confirmed_words[abs_index]["correct"] = True




            while word_index < len(confirmed_words) and confirmed_words[word_index] == (reference_script[word_index], True):
                word_index += 1

            print("🧪 Launching safe_send task")

            async def safe_send():
                try:
                    print("🧪 Launching safe_send task")
                    print("📤 Confirmed words sending to frontend:", confirmed_words)
                    print("📤 WebSocket state (inside safe_send):", websocket.client_state)

                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_text(json.dumps({
                            "type": "transcript",
                            "payload": confirmed_words
                        }))
                    else:
                        print("⚠️ WebSocket is closed in safe_send")
                except Exception as e:
                    print(f"⚠️ Failed to send: {e}")

            asyncio.create_task(safe_send())



        dg_connection.registerHandler(dg_connection.event.TRANSCRIPT_RECEIVED, on_transcript)
        ready_event.set()
        return dg_connection

    except Exception as e:
        print(f"❌ Error setting up Deepgram: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            websocket.close()
        return None