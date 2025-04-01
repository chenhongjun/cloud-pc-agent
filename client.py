import asyncio
import websockets
import json

class WebSocketRPCClient:
    def __init__(self, uri="ws://localhost:8765"):
        self.uri = uri

    async def receive_messages(self, websocket):
        while True:
            try:
                response = await websocket.recv()
                response_data = json.loads(response)
                if "params" in response_data and isinstance(response_data["params"], list):
                    for param in response_data["params"]:
                        if "output_text" in param:
                            print(f"\nReceived text: {param['output_text']}")
                            print("Enter your message (or 'exit' to quit): ", end="")
                else:
                    print(f"Received: {response}")
            except websockets.exceptions.ConnectionClosed:
                print("\nConnection closed")
                break

    async def interactive_chat(self):
        async with websockets.connect(self.uri) as websocket:
            # 启动接收消息的任务
            receive_task = asyncio.create_task(self.receive_messages(websocket))
            request_id = 1
            while True:
                user_input = input("Enter your message (or 'exit' to quit): ")
                if user_input.lower() == "exit":
                    break
                request = {
                    "jsonrpc": "2.0",
                    "method": "input",
                    "params": [{"input_text": user_input}, {"input_image": ""}, {"input_audio": ""}],
                    "id": request_id
                }
                await websocket.send(json.dumps(request))
                print(f"Sent: {request}")
                request_id += 1
            # Ensure that the receive task completes before closing the connection
            await receive_task

if __name__ == "__main__":
    client = WebSocketRPCClient()
    asyncio.run(client.interactive_chat())
