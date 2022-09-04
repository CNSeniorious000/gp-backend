from sqlmodel import SQLModel, Field, select, Session
from functools import lru_cache, cached_property
from starlette.exceptions import HTTPException
from sqlalchemy.exc import NoResultFound
from ..common.auth import parse_id
from ..common.sql import engine
from contextlib import suppress
from pydantic import BaseModel
from autoprop import autoprop
from fastapi import APIRouter
from enum import IntEnum

router = APIRouter(tags=["activity"])


class Progress(IntEnum):
    canceled = 0
    todo = 1
    doing = 2
    done = 3


class ActivityItem(SQLModel, table=True):
    __tablename__ = "activities"
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    name: str
    description: str
    situation: Progress


@autoprop
class Activity:
    @lru_cache(maxsize=100)
    def __new__(cls, id):
        return super().__new__(cls)

    def __init__(self, id):
        self.id = id

    @cached_property
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


@router.get("/activity")
def get_activities(token: str):
    user_id = parse_id(token)
    with Session(engine) as session:
        return session.exec(select(ActivityItem).where(ActivityItem.user_id == user_id)).all()


class ActivityForm(BaseModel):
    name: str
    token: str
    description: str
    situation: Progress


@router.put("/activity")
def add_activity(form: ActivityForm):
    user_id = parse_id(form.token)
    with Session(engine) as session:
        session.add(ActivityItem(user_id=user_id,
                                 name=form.name,
                                 description=form.description,
                                 situation=form.situation))
        session.commit()

    return "add success"


@router.patch("/activity")
def update_activity(id: int, token: str, description: str | None = None, situation: Progress | None = None):
    if description is None and situation is None:
        raise HTTPException(400, "nothing changes")
    user_id = parse_id(token)
    with Session(engine) as session, suppress(NoResultFound):
        item = session.exec(select(ActivityItem).where(ActivityItem.id == id)).one()
        if item.user_id != user_id:
            raise HTTPException(401, f"activity {id} does not belongs to {user_id}")
        if description is not None:
            item.description = description
        if situation is not None:
            item.situation = situation.value  # if no ".value" will fail this update

        session.add(item)
        session.commit()
        return "update success"

    raise HTTPException(404, f"activity {id} does not exist")


@router.delete("/activity")
def remove_activity(token: str, id: str):
    user_id = parse_id(token)
    with Session(engine) as session:
        activity = session.exec(select(ActivityItem).where(ActivityItem.id == id)).one_or_none()
        if activity is None:
            raise HTTPException(404, f"activity {id} does not exist")

        if user_id == activity.user_id:
            session.delete(activity)
            session.commit()
        else:
            raise HTTPException(401, f"activity {id} does not belongs to {user_id}")

    Activity.__new__.cache_clear()

    return "delete success"
