from sqlmodel import SQLModel, Field, Session, select, or_
from ..common.secret import app_secret as sk, pool
from starlette.responses import PlainTextResponse
from functools import cached_property, lru_cache
from fastapi.responses import ORJSONResponse
from sqlalchemy.exc import NoResultFound
from ..common.auth import parse_id
from ujson import dumps, loads
from pydantic import BaseModel
from fastapi import APIRouter
from httpx import AsyncClient
from itertools import chain
from ..common.sql import *
from asyncio import sleep
from hashlib import md5
from redis import Redis
from time import time
import jwt

router = APIRouter(tags=["user"])

client = AsyncClient(http2=True)
openid_cache = Redis(connection_pool=pool, db=1)


def md5_hash(string: str) -> bytes:
    return md5(string.encode()).digest()


class UserItem(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(nullable=False, primary_key=True)
    pwd_hash: bytes
    meta: str = "{}"


class PwdChecker:
    class Checker:
        def __init__(self, pwd_hash):
            assert isinstance(pwd_hash, bytes), "md5 digest can only be bytes"
            self.pwd_hash = pwd_hash

        def __eq__(self, other):
            assert isinstance(other, str), "can only compare with string"
            return self.pwd_hash == md5_hash(other)

        def __repr__(self):
            return f"<PasswordChecker holding md5 {self.pwd_hash}>"

    def __set_name__(self, owner, name):
        self.public_name = name
        self.private_name = f"_{name}_checker"

    def __get__(self, instance, owner):
        assert isinstance(instance, User), "password must belongs to a user"
        return self.Checker(instance.item.pwd_hash)

    def __set__(self, instance: "User", value: str):
        with Session(engine) as session:
            instance.item.pwd_hash = md5_hash(value)
            session.add(instance.item)
            session.commit()
            session.refresh(instance.item)


class User:
    pwd = PwdChecker()

    @lru_cache(maxsize=1000)
    def __new__(cls, id):
        return super().__new__(cls)

    def __init__(self, id):
        self.id = id

    def __getitem__(self, key):
        return self.meta.get(key)

    def __setitem__(self, key, val):
        self.meta[key] = val
        with Session(engine) as session:
            self.item.meta = dumps(self.meta, ensure_ascii=False)
            # del self.meta
            session.add(self.item)
            session.commit()
            session.refresh(self.item)  # maybe redundant

    @cached_property
    def meta(self) -> dict:
        return loads(self.item.meta)

    @cached_property
    def item(self):
        with Session(engine) as session:
            return session.exec(select(UserItem).where(UserItem.id == self.id)).one()

    def __repr__(self):
        return f"User({self.id})"

    @property
    def profile(self):
        return {"id": self.id, "meta": self.meta}


class UserForm(BaseModel):
    id: str
    pwd: str


class ResetPwdForm(BaseModel):
    token: str
    new_pwd: str


@router.get("/user")
def exist(id: str):
    try:
        return User(id).item.id == id
    except NoResultFound:
        return False


@router.put("/user")
async def register(form: UserForm):
    if exist(form.id):
        return PlainTextResponse(f"user {form.id} already exists", 403)

    with Session(engine) as session:
        user = UserItem()
        user.id = form.id
        user.pwd_hash = md5_hash(form.pwd)
        session.add(user)
        session.commit()
        session.refresh(user)  # maybe redundant

    return ORJSONResponse({"hex": User(form.id).pwd.pwd_hash.hex()}, 201)


@router.post("/user")
async def login(form: UserForm):
    if not exist(form.id):
        return PlainTextResponse(f"user {form.id} doesn't exist", 404)

    user = User(form.id)
    if user.pwd == form.pwd:
        return PlainTextResponse(jwt.encode(
            {"time": time(), "id": form.id},
            sk, "HS256"
        ))
    else:
        return PlainTextResponse("wrong password", status_code=401)


@router.patch("/user")
async def reset_pwd(form: ResetPwdForm):
    try:
        id = jwt.decode(form.token, sk, "HS256")["id"]  # ensure valid
    except jwt.InvalidSignatureError as err:
        return PlainTextResponse(f"{type(err).__qualname__}: {str(err)}", 403)  # hacking?
    except jwt.DecodeError as err:
        return PlainTextResponse(f"{type(err).__qualname__}: {str(err)}", 400)  # just playing
    except (TypeError, KeyError):
        import traceback
        return PlainTextResponse(traceback.format_exc(chain=False), 500)  # maybe wrong jwt or wrong head

    User(id).pwd = form.new_pwd
    return ORJSONResponse({"hex": repr(User(id).pwd.pwd_hash.hex())}, 201)


@router.delete("/user")
async def erase(token: str):
    id = parse_id(token)
    if not exist(id):
        return PlainTextResponse(f"user {id} doesn't exist", 404)

    from .relation import RelationItem
    from ..userdata.favorite import FavoriteItem
    from ..userdata.activity import ActivityItem, Activity

    with Session(engine) as session:
        for item in chain(
                session.exec(select(RelationItem).where(or_(
                    RelationItem.from_user_id == id, RelationItem.to_user_id == id
                ))),
                session.exec(select(FavoriteItem).where(FavoriteItem.user_id == id)),
                session.exec(select(ActivityItem).where(ActivityItem.user_id == id))
        ):
            session.delete(item)
        session.commit()
        session.delete(User(id).item)
        session.commit()

    User.__new__.cache_clear()
    Activity.__new__.cache_clear()

    return not exist(id)


@router.get("/avatar/{id}")
async def get_avatar(id: str):
    """获取用户头像"""
    return User(id)["avatar"]


@router.put("/avatar")
async def set_avatar(token: str, url: str):
    """设置用户头像"""
    user = User(parse_id(token))
    user["avatar"] = url


@router.get("/name/{id}")
async def get_name(id: str):
    """获取用户昵称"""
    return User(id)["name"]


@router.put("/name")
async def set_name(token: str, name: str):
    """设置用户昵称"""
    user = User(parse_id(token))
    user["name"] = name
