from sqlmodel import SQLModel, Field as DbField, select, Session
from starlette.exceptions import HTTPException
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from ..common.auth import Bearer
from ..common.sql import engine
from functools import lru_cache
from ..user.impl import ensure
from autoprop import autoprop
from enum import Enum

router = APIRouter(tags=["activity"])


class Progress(Enum):
    todo = "todo"
    doing = "doing"
    done = "done"
    canceled = "canceled"


class ActivityItem(SQLModel, table=True):
    __tablename__ = "activities"
    id: int | None = DbField(default=None, primary_key=True)
    user_id: str = DbField(foreign_key="users.id")
    creator: str = DbField(foreign_key="users.id")
    name: str
    description: str
    situation: Progress

    class Config:
        schema_extra = {"example": {
            "id": 1,
            "user_id": "id",
            "name": "活动名",
            "description": "这是一个活动",
            "situation": Progress.doing
        }}


@autoprop
class Activity:
    @lru_cache(maxsize=100)
    def __new__(cls, id):
        return super().__new__(cls)

    def __init__(self, id):
        self.id = id

    @property
    def item(self):
        with Session(engine) as session:
            return session.exec(select(ActivityItem).where(ActivityItem.id == self.id)).one()

    def get_user(self):
        from ..user.impl import User
        return User(self.item.user_id)

    def get_name(self):
        return self.item.name

    def get_description(self):
        return self.item.description

    def get_situation(self):
        return self.item.situation

    def set_name(self, name: str):
        with Session(engine) as session:
            self.item.name = name
            session.add(self.item)
            session.commit()
            session.refresh(self.item)

    def set_description(self, description: str):
        with Session(engine) as session:
            self.item.description = description
            session.add(self.item)
            session.commit()
            session.refresh(self.item)

    def set_situation(self, situation: Progress):
        with Session(engine) as session:
            self.item.situation = situation
            session.add(self.item)
            session.commit()
            session.refresh(self.item)


@router.get("/activity", response_model=list[ActivityItem])
def get_activities(bearer: Bearer = Depends(), user_id: str | None = Query(None, title="列出谁的活动", example="id")):
    """获取活动。获取亲友的活动暂时只能分别去获取"""
    if user_id is not None:
        bearer.ensure_been_permitted_by(ensure(user_id))
    else:
        user_id = bearer.id
    with Session(engine) as session:
        return session.exec(select(ActivityItem).where(ActivityItem.user_id == user_id)).all()


class ActivityPut(BaseModel):
    name: str = Field(..., example="活动名称")
    description: str = Field(..., example="活动描述")
    situation: Progress
    user_id: str | None = Field(None, example="用户openid", description="可以填有权限的联系人，不填则默认为自己")


@router.put("/activity", response_model=ActivityItem)
def add_activity(data: ActivityPut, bearer: Bearer = Depends()):
    creator = bearer.id
    if data.user_id is not None:
        user_id = data.user_id
        bearer.ensure_been_permitted_by(user_id)
    else:
        user_id = creator

    with Session(engine) as session:
        session.add(item := ActivityItem(user_id=user_id,
                                         creator=creator,
                                         name=data.name,
                                         description=data.description,
                                         situation=data.situation))
        session.commit()
        session.refresh(item)

        return item


class ActivityPatch(ActivityPut):
    """修改活动。暂时还只能号主修改自己的活动"""

    id: int = Field(..., example="1")


@router.patch("/activity", response_model=ActivityItem)
def update_activity(data: ActivityPatch, bearer: Bearer = Depends()):
    user_id = bearer.id
    activity_id = data.id
    with Session(engine) as session:
        item = session.exec(select(ActivityItem).where(ActivityItem.id == activity_id)).one_or_none()
        if item is None:
            raise HTTPException(404, f"activity {activity_id} does not exist")
        if item.user_id != user_id:
            raise HTTPException(401, f"activity {activity_id} does not belongs to {user_id}")

        if data.description is not None:
            item.description = data.description
        if data.situation is not None:
            item.situation = data.situation  # if no ".value" will fail this update

        session.add(item)
        session.commit()
        session.refresh(item)

    return item


@router.delete("/activity", response_model=str)
def remove_activity(activity_id: int, bearer: Bearer = Depends()):
    user_id = bearer.id
    with Session(engine) as session:
        activity = session.exec(select(ActivityItem).where(ActivityItem.id == activity_id)).one_or_none()
        if activity is None:
            raise HTTPException(404, f"activity {activity_id} does not exist")

        if user_id == activity.user_id:
            session.delete(activity)
            session.commit()
        else:
            raise HTTPException(401, f"activity {activity_id} does not belongs to {user_id}")

    Activity.__new__.cache_clear()

    return f"delete {activity_id} success"
