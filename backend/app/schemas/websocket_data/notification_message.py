from pydantic import BaseModel, Field
from typing import Literal, Union, Annotated, Optional

class NotificationBase(BaseModel):
    sender: Optional[str] = None
    profile: Optional[str] = None
    pubsub_publisher: Optional[str] = None

class NotificationMessage(NotificationBase):
    chat: Literal['notification'] = "notification"
    type: Literal["message"] = "message"
    dm: int
    receiver: str
    count: Optional[int] = None

class NotificationNewDm(NotificationBase):
    chat: Literal['notification']= "notification"
    type: Literal["newdm"] = "newdm"
    receiver: str

Notification = Annotated[Union[NotificationMessage,NotificationNewDm],Field(...,discriminator='type')]
