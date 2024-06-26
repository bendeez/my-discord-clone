from fastapi import WebSocket
from typing import Union
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.server_websocket import save_message, send_notification
from app.crud.server_websocket import set_user_status
from app.schemas.websocket_data.websocket_data import WebsocketData,websocket_data_adaptor
from datetime import datetime
from app.firebase.firebase_startup import firebase_storage
import uuid
import asyncio
from uuid import uuid4
import base64


class ServerConnectionManager:
    def __init__(self):
        self.active_connections: list[dict[str, Union[list[int], str, WebSocket]]] = []

    async def connect(self, websocket: WebSocket, current_user: dict,db: AsyncSession):
        await websocket.accept()
        self.active_connections.append(current_user)
        await set_user_status(db=db, status="online", current_user=current_user)
        data = websocket_data_adaptor.validate_python({"chat": "notificationall", "type": "status", "status": "online",
                                                       "username": current_user["username"]})
        await self.broadcast(websocket=websocket,
                             data=data,
                             current_user=current_user)

    async def disconnect(self, websocket: WebSocket, current_user: dict,db: AsyncSession):
        self.active_connections.remove(current_user)
        await set_user_status(db=db, status="offline", current_user=current_user)
        data = websocket_data_adaptor.validate_python({"chat": "notificationall", "type": "status", "status": "offline",
                                                        "username": current_user["username"]})
        await self.broadcast(websocket=websocket,
                             data=data,
                             current_user=current_user)

    async def broadcast_from_route(self, sender_username: str, message: dict, db: AsyncSession):
        for connection in self.active_connections:
            if connection.get("username") == sender_username:
                await server_manager.broadcast(websocket=connection.get("websocket"), data=message,
                                               current_user=connection)

    async def broadcast(self, websocket: WebSocket, data: dict, current_user: dict):
        data = websocket_data_adaptor.validate_python(data)
        try:
            chat = data.chat
            if chat == "dm": # checks if the message is being sent to a dm
                await self.broadcast_dm(websocket=websocket,data=data,current_user=current_user)
            elif chat == "server":
                await self.broadcast_server(websocket=websocket,data=data,current_user=current_user)
            elif chat == "notification":
                await self.broadcast_notification(websocket=websocket,data=data,current_user=current_user)
            elif chat == "notificationall":
                await self.broadcast_notification_all(websocket=websocket,data=data,current_user=current_user)
        except Exception as e:
            print(e)

    async def save_file(self, data: WebsocketData):
        file_type = data.filetype
        filename = f"{uuid.uuid4()}.{file_type}"
        if "," in data.file:
            file = data.file.split(",")[1]
        else:
            file = data.file
        encoded_file = base64.b64decode(file)
        await asyncio.to_thread(firebase_storage.child(filename).put, encoded_file)
        data.file = f"https://firebasestorage.googleapis.com/v0/b/discord-83cd2.appspot.com/o/{filename}?alt=media&token=c27e7352-b75a-4468-b14b-d06b74839bd8"

    async def broadcast_dm(self, websocket: WebSocket, data: WebsocketData, current_user: dict):
        if data.type == "file" or data.type == "textandfile":
            await self.save_file(data)
        if data.type == "link":
            data.link = str(uuid4())
        data.username = current_user["username"]
        data.profile = current_user["profile"]
        data.date = datetime.now()
        dm = data.dm  # get the dm id
        if dm in current_user.get("dm_ids", []):  # checks if the dm id is a part of the user's dms
            data_dict = data.dict()
            data_dict["date"] = str(data_dict["date"])
            for connection in self.active_connections:  # loops through all connections
                if dm in connection.get("dm_ids", []):  # checks if the dm id is a part of the remote user's dms
                    asyncio.create_task(connection.get("websocket").send_json(data=data_dict))  # sends a message if it is
            asyncio.create_task(save_message(data=data))
            asyncio.create_task(send_notification(websocket=websocket, data=data, current_user=current_user))

    async def broadcast_server(self, websocket: WebSocket, data: WebsocketData, current_user: dict):
        if data.type == "file" or data.type == "textandfile":
            await self.save_file(data)
        data.username = current_user["username"]
        data.profile = current_user["profile"]
        data.date = datetime.now()
        server = data.server
        if server in current_user.get("server_ids", []):
            data_dict = data.dict()
            data_dict["date"] = str(data_dict["date"])
            for connection in self.active_connections:
                if server in connection.get("server_ids", []):
                    asyncio.create_task(connection.get("websocket").send_json(data=data_dict))
            asyncio.create_task(save_message(data=data))

    async def broadcast_notification(self, websocket: WebSocket, data: WebsocketData, current_user: dict):
        data.sender = current_user["username"]
        data.profile = current_user["profile"]
        for connection in self.active_connections:
            if data.receiver == connection.get("username"):
                asyncio.create_task(connection.get("websocket").send_json(data=data.dict()))
        asyncio.create_task(save_message(data=data))

    async def broadcast_notification_all(self, websocket: WebSocket, data: WebsocketData, current_user: dict):
        data.username = current_user["username"]
        for connection in self.active_connections:
            asyncio.create_task(connection.get("websocket").send_json(data.dict()))
        asyncio.create_task(save_message(data=data))


    def add_valid_server_or_dm(self, usernames: list, type: str, id: str):
        for connection in self.active_connections:
            if connection.get("username") in usernames:
                if isinstance(connection.get(type), list):
                    connection.get(type).append(int(id))


server_manager = ServerConnectionManager()
