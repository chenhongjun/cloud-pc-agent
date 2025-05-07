import asyncio
import websockets
import json
import logging
import aioconsole

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
                            logger.info(f"\nReceived text: {param['output_text']}")
                else:
                    logger.info(f"Received: {response}")
            except websockets.exceptions.ConnectionClosed:
                logger.info("\nConnection closed")
                break

    async def interactive_chat(self):
        async with websockets.connect(self.uri) as websocket:
            # 启动接收消息的任务
            receive_task = asyncio.create_task(self.receive_messages(websocket))
            request_id = 1
            while True:
                user_input = await aioconsole.ainput()
                if user_input.lower() == "exit":
                    break
                request = {
                    "jsonrpc": "2.0",
                    "method": "input",
                    "params": [{"input_text": user_input}, {"input_image": ""}, {"input_audio": ""}],
                    "id": request_id
                }
                await websocket.send(json.dumps(request))
                logger.info(f"Sent: {request}")
                request_id += 1
            # Ensure that the receive task completes before closing the connection
            await receive_task

if __name__ == "__main__":
    # 创建 logger
    logger = logging.getLogger("my_app")
    logger.setLevel(logging.INFO)
    # 创建控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    # 创建文件 handler
    file_handler = logging.FileHandler("client.log", mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    # 创建格式器
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
    # 给 handler 加格式
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    # 添加 handler 到 logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    client = WebSocketRPCClient()
    asyncio.run(client.interactive_chat())
