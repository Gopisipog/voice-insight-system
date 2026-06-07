import asyncio
import websockets
import json
import os
from core.shell_runner import ShellRunner
from dotenv import load_dotenv

load_dotenv()

SERVER_URL = os.getenv("BRIDGE_SERVER_URL", "ws://localhost:9000/ws/bridge")
FILTER_COMMAND = os.getenv("FILTER_COMMAND", "powershell -Command \"$input | findstr /i 'insight'\"")

async def bridge_loop():
    runner = ShellRunner()
    
    print(f"Connecting to Bridge Server at {SERVER_URL}...")
    
    async for websocket in websockets.connect(SERVER_URL):
        try:
            print("Connected to server.")
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                if data.get("type") == "run_command":
                    input_text = data.get("input")
                    print(f"Executing local command for: {input_text[:50]}...")
                    
                    result = runner.run_command(FILTER_COMMAND, input_text)
                    
                    await websocket.send(json.dumps({
                        "type": "command_result",
                        "output": result
                    }))
        except websockets.ConnectionClosed:
            print("Disconnected. Retrying...")
            continue

if __name__ == "__main__":
    asyncio.run(bridge_loop())
