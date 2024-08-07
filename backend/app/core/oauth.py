import jwt
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status, WebSocket, WebSocketException
from app.db.database import get_db
from app.core.config import settings
from app.crud.user import get_user,get_user_data
from sqlalchemy.ext.asyncio import AsyncSession

SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def create_access_token(data: dict):
    to_encode = data.copy()
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, ALGORITHM)
        username = payload.get("username")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        user = await get_user(db=db,remote_user_username=username)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


async def get_websocket_user(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    websocket_params = websocket.path_params
    token = websocket_params.get("token")
    if token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    try:
        payload = jwt.decode(token, SECRET_KEY, ALGORITHM)
        username = payload.get("username")
        if username is None:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        user = await get_user_data(db=db,username=username)
        if user is None:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        user_data_json = {"websocket": websocket, "username": user.username,"profile": user.profile,
                          "server_ids": [server.server_id for server in user.server_associations],
                          "dm_ids": [dm.id for dm in user.sent_dms + user.received_dms],"user_model":user}
        return user_data_json
    except jwt.PyJWTError:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)