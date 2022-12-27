from ..common.secret import app_secret_0 as sk_0, app_secret_1 as sk_1, pool
from sqlmodel import SQLModel, Field, Session, select, or_
from starlette.responses import PlainTextResponse
from starlette.exceptions import HTTPException
from fastapi.responses import ORJSONResponse
from sqlalchemy.exc import NoResultFound
from fastapi import APIRouter, Depends
from cachetools.func import ttl_cache
from ..common.auth import Bearer
from functools import lru_cache
from ujson import dumps, loads
from pydantic import BaseModel
from httpx import AsyncClient
from itertools import chain
from ..common.sql import *
from fastapi import Form
from hashlib import md5
from redis import Redis
import jwt

router = APIRouter(tags=["user"])

client = AsyncClient(http2=True)
openid_cache = Redis(connection_pool=pool, db=1)


def md5_hash(string: str) -> bytes:
    return md5(string.encode()).digest()


class UserItem(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(None, nullable=False, primary_key=True)
    pwd_hash: bytes
    meta: str = "{}"
    permission: str = ""


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


# noinspection PyPropertyAccess
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
        (meta := self.meta)[key] = val
        with Session(engine) as session:
            item = self.item
            item.meta = dumps(meta, ensure_ascii=False)
            session.add(item)
            session.commit()

    @property
    def meta(self) -> dict:
        return loads(self.item.meta)

    @property
    def permissions(self) -> list:
        return [self.id] + self.item.permission.split()

    @property
    def item(self):
        with Session(engine) as session:
            return session.exec(select(UserItem).where(UserItem.id == self.id)).one()

    def __repr__(self):
        return f"User({self.id})"


def ensure(user_id: str):
    if not exist(user_id):
        raise HTTPException(400, f"user {user_id} doesn't exist")
    return user_id


@router.get("/permission")
def get_permissions(bearer: Bearer = Depends()):
    return bearer.user.permissions


@router.put("/permission", response_class=PlainTextResponse)
def add_permission(from_user_id: str = Depends(ensure), to_bearer: Bearer = Depends()):
    if from_user_id in to_bearer.user.permissions:
        return f"{User(from_user_id)} already in {to_bearer.user}'s permission list"

    to_user_item = to_bearer.user.item
    with Session(engine) as session:
        to_user_item.permission = " ".join(to_user_item.permission.split() + [from_user_id])
        session.add(to_user_item)
        session.commit()
        return f"add {User(from_user_id)} to {to_bearer.user}'s permission list successfully"


@router.delete("/permission", response_class=PlainTextResponse)
async def remove_permission(from_user_id: str = Depends(ensure), to_bearer: Bearer = Depends()):
    permission = to_bearer.user.item.permission

    if from_user_id not in permission:
        raise HTTPException(404, f"{User(from_user_id)} not in {to_bearer.user}'s permission list")

    to_user_item = to_bearer.user.item
    with Session(engine) as session:
        permissions = permission.split()
        permissions.remove(from_user_id)
        to_user_item.permission = " ".join(permissions)
        session.add(to_user_item)
        session.commit()
        return f"remove {User(from_user_id)} from {to_bearer.user}'s permission list successfully"


@router.get("/test_permission", deprecated=True)
def verify_permitted(from_user_id, to_user_id):
    if from_user_id not in User(to_user_id).permissions:
        raise HTTPException(403, f"User({from_user_id}) don't have permission to view User({to_user_id})'s information")
    return True


class UserPut(BaseModel):
    id: str
    pwd: str


class ResetPwd(BaseModel):
    old_pwd: str
    new_pwd: str


@router.get("/user")
@ttl_cache(1234, 5)
def exist(id: str):
    try:
        return User(id).item.id == id
    except NoResultFound:
        return False


@router.put("/user")
async def register(data: UserPut):
    if exist(data.id):
        return PlainTextResponse(f"user {data.id} already exists", 401)

    with Session(engine) as session:
        user = UserItem(id=data.id, pwd_hash=md5_hash(data.pwd))
        session.add(user)
        session.commit()
        session.refresh(user)  # maybe redundant

    return ORJSONResponse({"id": user.id, "hex": user.pwd_hash.hex()}, 201)


@router.post("/user")
async def login(id: str = Form(), pwd: str = Form()):
    if not exist(id):
        return PlainTextResponse(f"user {id} doesn't exist", 404)

    user = User(id)
    if user.pwd == pwd:
        token = f"Bearer {jwt.encode({'scope': 'user', 'id': id}, sk_1, 'HS256')}"
        response = ORJSONResponse({"token": token, "bio": user["bio"], "name": user["name"], "avatar": user["avatar"]})
        response.set_cookie("token", token)
        return response
    else:
        return PlainTextResponse("wrong password", status_code=401)


@router.patch("/user")
async def reset_pwd(form: ResetPwd, bearer: Bearer = Depends()):
    user = bearer.user
    if user.pwd == form.old_pwd:
        user.pwd = form.new_pwd
    else:
        return PlainTextResponse("wrong password", status_code=401)


@router.delete("/user")
async def erase(bearer: Bearer = Depends()):
    id = bearer.id
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
    try:
        return User(id)["avatar"]
    except NoResultFound:
        raise HTTPException(404, f"{id} is not a valid user id")


@router.put("/avatar")
async def set_avatar(url: str, bearer: Bearer = Depends()):
    """设置用户头像"""
    bearer.user["avatar"] = url
    return url


@router.get("/name/{id}")
async def get_name(id: str):
    """获取用户昵称"""
    try:
        return User(id)["name"]
    except NoResultFound:
        raise HTTPException(404, f"{id} is not a valid user id")


@router.put("/name")
async def set_name(name: str, bearer: Bearer = Depends()):
    """设置用户昵称"""
    bearer.user["name"] = name
    return name


@router.post("/bio")
async def set_bio(bio: str, bearer: Bearer = Depends()):
    """设置用户个性签名"""
    bearer.user["bio"] = bio
    return bio


@router.get("/geo")
async def get_location(id: str = None, bearer: Bearer = Depends()):
    if id is not None:
        bearer.ensure_been_permitted_by(ensure(id))
        user = User(id)
    else:
        user = bearer.user

    raw = user["location"]
    return raw and eval(raw)


@router.put("/geo")
async def set_location(location: tuple[float, float] = (113.5430570, 22.3571951), bearer: Bearer = Depends()):
    bearer.user["location"] = str(list(location))
    return list(location)
