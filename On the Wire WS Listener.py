#!/usr/bin/env python3

import time
import ssl
from websocket import WebSocketApp

# Change the WS when needed.
WS_URL = "wss://signals.holidayhackchallenge.com/wire/dq"

def on_open(ws):
    print(f"[OPEN] Connected to {WS_URL}")

def on_message(ws, message):
    # Print raw messages as they arrive
    print(f"[MSG] {message}")

def on_error(ws, error):
    print(f"[ERROR] {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"[CLOSE] code={close_status_code} msg={close_msg}")

def run():
    # Simple reconnect loop so it stays up if the server drops the connection
    while True:
        try:
            ws = WebSocketApp(
                WS_URL,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                # If the server requires specific headers, add them here:
                # header=[ "Origin: https://signals.holidayhackchallenge.com" ]
            )
            ws.run_forever(
                sslopt={"cert_reqs": ssl.CERT_REQUIRED},
                ping_interval=30,
                ping_timeout=10,
            )
        except KeyboardInterrupt:
            print("[EXIT] Keyboard interrupt")
            break
        except Exception as e:
            print(f"[RETRY] Exception: {e}")
        # brief backoff before reconnect
        time.sleep(2)


if __name__ == "__main__":
    run()
