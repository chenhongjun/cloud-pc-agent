import asyncio
import websockets
import json
import openai
import base64
import logging
import openai
from PIL import Image
import base64
from io import BytesIO

def encode_image(image_path):
    with Image.open(image_path) as img:
        img_mini = img.resize((1024, 540))
        buffered = BytesIO()
        img_mini.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

def moke():
    img_path = "t2.png"
    return encode_image(img_path)

class WebSocketRPCServer:
    def __init__(self, host="0.0.0.0", port=8765, openai_api_key="YOUR_OPENAI_API_KEY"):
        self.host = host
        self.port = port
        self.send_queue = asyncio.Queue()
        self.openai_api_key = openai_api_key
        self.sessions = {}  # 存储每个 WebSocket 连接的聊天记录

    async def process_input(self, websocket, params, request_id):
        input_text = next((p["input_text"] for p in params if "input_text" in p), "")
        input_image = next((p["input_image"] for p in params if "input_image" in p), "")
        # 记录聊天历史
        session = self.sessions.setdefault(websocket, [])
        session.append({"role": "user", "content": input_text})
        
        input_image = moke()
        gpt_response = await self.call_gpt4o(session, input_image)
        session.append({"role": "assistant", "content": gpt_response})

        # logger.info(session)
        response = {
            "jsonrpc": "2.0",
            "method": "output",
            "params": [{"output_text": gpt_response}, {"output_image": ""}, {"output_audio": ""}],
            "id": request_id
        }

        await self.send_queue.put(json.dumps(response))
    async def call_gpt4o(self, session, input_image):
        client = openai.OpenAI(api_key=self.openai_api_key)
        
        content = [{"type": "text", "text": session[-1]["content"]}] if session else []
        
        if input_image:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{input_image}"
                }
            })
        
        # logger.info(f"content: {content}")
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": content}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

    async def process_other_method(self, params, request_id):
        response = {
            "jsonrpc": "2.0",
            "method": "output",
            "params": params,
            "id": request_id
        }
        await self.send_queue.put(json.dumps(response))

    async def handle_jsonrpc_request(self, websocket, message):
        try:
            request = json.loads(message)
            if not ("jsonrpc" in request and "method" in request and "id" in request):
                return json.dumps({"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": None})
            
            method = request["method"]
            params = request.get("params", [])
            request_id = request["id"]
            
            if method == "input":
                await self.process_input(websocket, params, request_id)
                return None  # 不直接返回，而是通过发送队列返回响应
            elif method == "other_method":
                await self.process_other_method(params, request_id)
                return None
            else:
                return json.dumps({"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": request_id})
        except json.JSONDecodeError:
            return json.dumps({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None})
    
    async def handler(self, websocket):
        self.sessions[websocket] = []  # 初始化该连接的会话历史
        try:
            receive_task = asyncio.create_task(self.receive_messages(websocket))
            send_task = asyncio.create_task(self.send_messages(websocket))
            await asyncio.gather(receive_task, send_task)
        finally:
            del self.sessions[websocket]  # 断开连接时删除会话历史

    async def receive_messages(self, websocket):
        async for message in websocket:
            response = await self.handle_jsonrpc_request(websocket, message)
            if response:
                await websocket.send(response)
                print(f"Sent: {response}")

    async def send_messages(self, websocket):
        while True:
            response = await self.send_queue.get()
            await websocket.send(response)
            print(f"Sent from queue: {response}")
            response_data = json.loads(response)
            if "params" in response_data and isinstance(response_data["params"], list):
                for param in response_data["params"]:
                    if "output_text" in param:
                        print(f"\nReceived text: {param['output_text']}")

    async def run(self):
        async with websockets.serve(self.handler, self.host, self.port):
            print(f"WebSocket JSON-RPC server started on ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever

if __name__ == "__main__":
    # 创建 logger
    logger = logging.getLogger("my_app")
    logger.setLevel(logging.INFO)
    # 创建控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    # 创建文件 handler
    file_handler = logging.FileHandler("server.log", mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    # 创建格式器
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
    # 给 handler 加格式
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    # 添加 handler 到 logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    server = WebSocketRPCServer(openai_api_key="")
    asyncio.run(server.run())
