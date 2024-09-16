import streamlit as st
import websockets
import asyncio
import base64
import json
from configure import auth_key

import pyaudio

if 'text' not in st.session_state:
    st.session_state['text'] = 'Listening...'
    st.session_state['run'] = False

FRAMES_PER_BUFFER = 3200
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
p = pyaudio.PyAudio()

# starts recording
stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=FRAMES_PER_BUFFER
)

def start_listening():
    st.session_state['run'] = True
    st.session_state['text'] = 'Listening...'
    asyncio.run(send_receive())  # Start the async function

def stop_listening():
    st.session_state['run'] = False
    st.session_state['text'] = 'Stopped'

URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

async def send_receive():
    print(f'Connecting websocket to url {URL}')

    try:
        async with websockets.connect(
            URL,
            extra_headers={"Authorization": auth_key},
            ping_interval=5,
            ping_timeout=20
        ) as _ws:

            r = await asyncio.sleep(0.1)
            print("Receiving SessionBegins ...")

            session_begins = await _ws.recv()
            print(session_begins)
            print("Sending messages ...")

            async def send():
                while st.session_state['run']:
                    try:
                        data = stream.read(FRAMES_PER_BUFFER)
                        data = base64.b64encode(data).decode("utf-8")
                        json_data = json.dumps({"audio_data": str(data)})
                        await _ws.send(json_data)

                    except websockets.exceptions.ConnectionClosedError as e:
                        if hasattr(e, 'code') and e.code == 4008:
                            print(f"Connection closed with error code 4008: {e}")
                        else:
                            print(f"Connection closed with error: {e}")
                            break

                    except Exception as e:
                        print(e)
                        assert False, "Not a websocket 4008 error"

                    await asyncio.sleep(0.01)

            async def receive():
                while st.session_state['run']:
                    try:
                        result_str = await _ws.recv()
                        result = json.loads(result_str)['text']

                        if json.loads(result_str)['message_type'] == 'FinalTranscript':
                            print(result)
                            st.session_state['text'] = result
                            st.markdown(st.session_state['text'])

                    except websockets.exceptions.ConnectionClosedError as e:
                        if hasattr(e, 'code') and e.code == 4003:
                            print("This feature is paid-only. Please visit https://app.assemblyai.com/ to add a credit card to your account.")
                            break
                        
                        elif hasattr(e, 'code') and e.code == 4008:
                            print(f"Connection closed with error code 4008: {e}")
                        else:
                            print(f"Connection closed with error: {e}")
                            break

                    except Exception as e:
                        print(e)
                        assert False, "Not a websocket 4008 error"

            await asyncio.gather(send(), receive())

    except Exception as e:
        print(f"An error occurred: {e}")

st.title('My Speech to Text App')

start, stop = st.columns(2)
if start.button('Start Audio Processing'):
    start_listening()

if stop.button('Stop Audio'):
    stop_listening()

st.write(st.session_state['text'])