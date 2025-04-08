from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from websocket.deepgram_client import init_deepgram
import asyncio
import json

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ Client connected")

    reference_script = []
    confirmed_words = []
    dg_connection = None
    deepgram_ready = asyncio.Event()

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
                    confirmed_words = [{"word": word, "correct": False} for word in reference_script]

                    dg_connection = await init_deepgram(
                        reference_script,
                        confirmed_words,
                        websocket,
                        deepgram_ready
                    )

                elif data.get("type") == "end":
                    print("🛑 Session end requested")
                    break

            elif "bytes" in message:
                await deepgram_ready.wait()

                if dg_connection:
                    try:
                        dg_connection.send(message["bytes"])
                    except Exception as e:
                        print(f"💥 Failed to send audio: {e}")

    except WebSocketDisconnect:
        print("❌ WebSocket disconnected")

    finally:
        if dg_connection and hasattr(dg_connection, "finish"):
            await dg_connection.finish()
            print("🔚 Deepgram connection closed")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
            print("🔒 WebSocket connection closed")
        else:
            print("⚠️ WebSocket was already closed")
