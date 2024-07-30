from pydantic import BaseModel
from typing import Union, List
from fastapi import WebSocket
from app.models.user import Users
from app.WebsocketManagers.CentralWebsocketServerInterface import PubSubWebsocketMock



class WebsocketConnection(BaseModel):
    websocket: Union[WebSocket,PubSubWebsocketMock]
    username: str
    profile: str
    server_ids: List[int]
    dm_ids: List[int]
    user_model: Users


