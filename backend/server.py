"""
WebSocket 서버 모듈
실시간 데이터를 웹 클라이언트에 전송합니다.
"""

import asyncio
import json
import websockets
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import os
from typing import Set


class WebSocketServer:
    """WebSocket 서버 클래스"""

    def __init__(self, ws_port: int = 8765, http_port: int = 8000):
        self.ws_port = ws_port
        self.http_port = http_port
        self.clients: Set = set()
        self.loop = None
        self.ws_server = None

    async def register_client(self, websocket):
        """클라이언트 등록"""
        self.clients.add(websocket)
        print(f"Client connected. Total clients: {len(self.clients)}")

    async def unregister_client(self, websocket):
        """클라이언트 해제"""
        self.clients.discard(websocket)
        print(f"Client disconnected. Total clients: {len(self.clients)}")

    async def handle_client(self, websocket, path):
        """클라이언트 연결 처리"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                # 클라이언트로부터 메시지 수신 (필요시 처리)
                print(f"Received message: {message}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)

    async def broadcast(self, message: dict):
        """모든 클라이언트에게 메시지 브로드캐스트"""
        if self.clients:
            message_json = json.dumps(message, ensure_ascii=False)
            # 연결이 끊긴 클라이언트 제거
            disconnected_clients = set()
            for client in self.clients:
                try:
                    await client.send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.add(client)

            # 끊긴 클라이언트 제거
            for client in disconnected_clients:
                self.clients.discard(client)

    def send_data(self, data: dict):
        """동기 함수에서 데이터 전송 (콜백용)"""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(data), self.loop)

    async def start_websocket_server(self):
        """WebSocket 서버 시작"""
        self.ws_server = await websockets.serve(
            self.handle_client,
            "0.0.0.0",
            self.ws_port
        )
        print(f"WebSocket server started on ws://localhost:{self.ws_port}")

    def run(self):
        """서버 실행"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.loop.run_until_complete(self.start_websocket_server())
        print(f"WebSocket server is running...")
        self.loop.run_forever()

    def start_in_thread(self):
        """별도 스레드에서 서버 시작"""
        server_thread = threading.Thread(target=self.run, daemon=True)
        server_thread.start()
        return server_thread


class HTTPServerHandler(SimpleHTTPRequestHandler):
    """HTTP 서버 핸들러"""

    def __init__(self, *args, **kwargs):
        # frontend 디렉토리를 루트로 설정
        super().__init__(*args, directory='frontend', **kwargs)

    def log_message(self, format, *args):
        """로그 메시지 커스터마이징"""
        pass  # 로그 출력 억제


def start_http_server(port: int = 8000):
    """HTTP 서버 시작"""
    server = HTTPServer(('0.0.0.0', port), HTTPServerHandler)
    print(f"HTTP server started on http://localhost:{port}")

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return server, server_thread


if __name__ == "__main__":
    # 테스트
    import time

    # WebSocket 서버 시작
    ws_server = WebSocketServer(ws_port=8765, http_port=8000)
    ws_server.start_in_thread()

    # HTTP 서버 시작
    http_server, http_thread = start_http_server(8000)

    # 테스트 데이터 전송
    try:
        count = 0
        while True:
            time.sleep(2)
            test_data = {
                "type": "test",
                "count": count,
                "message": f"Test message {count}"
            }
            ws_server.send_data(test_data)
            print(f"Sent test message {count}")
            count += 1
    except KeyboardInterrupt:
        print("\nShutting down...")
