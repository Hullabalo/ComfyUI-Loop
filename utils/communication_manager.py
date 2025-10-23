import asyncio
import json
from typing import Dict, Any
from aiohttp import web
from server import PromptServer

class CommunicationManager:
    def __init__(self):
        self.message_store = {}
        self.response_callbacks = {}
        self.app = PromptServer.instance.app
        self.setup_routes()
        
    def setup_routes(self):
        """
        Setup all communication routes
        """
        self.app.router.add_post('/api/bridge/response', self.handle_response)
        
    async def send_message(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send message to frontend and wait for response
        """
        message_id = data.get('id', str(hash(json.dumps(data))))
        
        # Store callback for response
        future = asyncio.Future()
        self.response_callbacks[message_id] = future
        
        # Send message to frontend
        PromptServer.instance.send_sync(event_type, data)
        
        # Wait for response with timeout
        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            raise Exception(f"Timeout waiting for response for message {message_id}")
        finally:
            self.response_callbacks.pop(message_id, None)
    
    async def handle_response(self, request):
        """
        Handle response from frontend
        """
        try:
            data = await request.json()
            message_id = data.get('id')
            
            if message_id in self.response_callbacks:
                future = self.response_callbacks[message_id]
                if not future.done():
                    future.set_result(data)
                return web.json_response({"status": "ok"})
            else:
                return web.json_response({"status": "error", "message": "Unknown message ID"}, status=400)
                
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

# Global instance
comm_manager = CommunicationManager()