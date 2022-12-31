from sqlmodel import SQLModel, Field as DbField, select, Session
from starlette.exceptions import HTTPException
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from ..common.auth import Bearer
from ..common.sql import engine
from ..user.impl import ensure
from time import time

router = APIRouter(tags=["reminder"])


class ReminderItem(SQLModel, table=True):
    __tablename__ = "reminders"
    id: int | None = DbField(default=None, primary_key=True)
    user_id: str = DbField(foreign_key="users.id")
    creator: str = DbField(foreign_key="users.id")
    content: str
    creation_time: float | None = DbField(default_factory=time)
    modification_time: float | None
    notification_time: float | None

    class Config:
        schema_extra = {"example": {
            "id": 1, "user_id": None, "creator": "id",
            "content": "今天你守护青松了吗👀",
            "creation_time": 1664258595.830831,
            "modification_time": 1664258607.3446724,
            "notification_time": 1664262000.0
        }}


@router.get("/reminder", response_model=list[ReminderItem])
def get_reminders(bearer: Bearer = Depends(), user_id: str = None):
    if user_id is None:
        user_id = bearer.id
    else:
        bearer.ensure_been_permitted_by(ensure(user_id))
    with Session(engine) as session:
        return session.exec(select(ReminderItem).where(ReminderItem.user_id == user_id)).all()


class ReminderPut(BaseModel):
    user_id: str | None = Field(title="用户openid", description="可以填有权限的联系人，若不填即默认自己")
    content: str | None = Field(title="内容", description="也可以先创建空的以后再修改")
    creation_time: float | None = Field(default_factory=time, example=1664257424.4382992, title="创建时间",
                                        description="创建时间，不填则用服务器时间")
    notification_time: float | None = Field(None, example=1664258400.0, title="提醒时间",
                                            description="会出现在当日的备忘列表中")


@router.put("/reminder", response_model=ReminderItem)
def add_reminder(data: ReminderPut, bearer: Bearer = Depends()):
    creator = bearer.id
    if data.user_id is None:
        user_id = creator
    else:
        user_id = data.user_id
        bearer.ensure_been_permitted_by(user_id)

    with Session(engine) as session:
        session.add(item := ReminderItem(
            user_id=user_id, creator=creator, content=data.content,
            creation_time=data.creation_time, modification_time=data.creation_time,
            notification_time=data.notification_time
        ))
        session.commit()
        session.refresh(item)

        return item


class ReminderPatch(BaseModel):
    id: int
    content: str = Field(description="一般认为只有修改内容了才算修改，所以这项必填")
    modification_time: float | None = Field(example=1664258283.3689516, default_factory=time, title="修改时间",
                                            description="不填则用服务器时间")
    notification_time: float | None = Field(None, example=1664258400.0, title="提醒时间",
                                            description="会出现在当日的备忘列表中")


@router.patch("/reminder", response_model=ReminderItem)
def update_reminder(data: ReminderPatch, bearer: Bearer = Depends()):
    with Session(engine) as session:
        item = session.exec(select(ReminderItem).where(ReminderItem.id == data.id)).one_or_none()
        bearer.ensure_been_permitted_by(item.user_id)

        item.content = data.content
        item.modification_time = data.modification_time
        if data.notification_time is not None:
            item.notification_time = data.notification_time

        session.add(item)
        session.commit()
        session.refresh(item)

    return item


@router.delete("/reminder", response_model=str)
def remove_reminder(reminder_id: int, bearer: Bearer = Depends()):
    user_id = bearer.id
    with Session(engine) as session:
        reminder = session.exec(select(ReminderItem).where(ReminderItem.id == reminder_id)).one_or_none()
        if reminder is None:
            raise HTTPException(404, f"reminder {reminder_id} does not exist")

        bearer.ensure_been_permitted_by(reminder.user_id)
        session.delete(reminder)
        session.commit()

    return f"delete {reminder_id} successfully"
