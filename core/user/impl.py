from ..common.secret import pool, app_secret as sk
from starlette.responses import PlainTextResponse
from starlette.exceptions import HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from fastapi import APIRouter
from httpx import AsyncClient
from functools import cache
from hashlib import md5
from redis import Redis
import jwt

router = APIRouter()
client = AsyncClient(http2=True)
users = Redis(connection_pool=pool, db=0)


def get_hash_string(string: str):
    return md5(string.encode()).digest()


class User:
    @cache
    def __new__(cls, id):
        return super().__new__(cls)

    def __init__(self, id):
        self.id = id

    def __repr__(self):
        return f"User({self.id})"

    @staticmethod
    def simple_field(key):
        def getter(self: "User"):
            return users.hget(self.id, key)

        def setter(self: "User", value):
            users.hset(self.id, key, value)

        def deleter(self: "User"):
            users.hdel(self.id, key)

        return property(getter, setter, deleter)

    pwd_hash = simple_field("p")
    email = simple_field("e")
    tel = simple_field("t")

    def set_password(self, pwd: str):
        self.pwd_hash = get_hash_string(pwd)

    def check_password(self, pwd: str):
        return self.pwd_hash == get_hash_string(pwd)

    pwd = property(fset=set_password)

    @property
    def profile(self):
        return {
            "email": self.email,
            "tel": self.tel
        }


class NewUser(BaseModel):
    id: str
    pwd: str | None
    email: str | None
    tel: str | None


@router.put("/user")
async def new_user(userinfo: NewUser):
    user = User(userinfo.id)
    if userinfo.pwd is not None:
        user.pwd = userinfo.pwd

    if userinfo.email is not None:
        user.email = userinfo.email

    if userinfo.tel is not None:
        user.tel = userinfo.tel


class VerifyUser(BaseModel):
    id: str
    pwd: str


@router.post("/user")
async def login(userinfo: VerifyUser):
    user = User(userinfo.id)
    if user.check_password(userinfo.pwd):
        return PlainTextResponse(jwt.encode({1: 2}, sk, "HS256"))
    else:
        return PlainTextResponse(status_code=401)


@router.get("/user", response_class=ORJSONResponse)
async def show_profile(id: str):
    if id in users:
        return User(id).profile
    else:
        return HTTPException(404, f"not user's id is {id}")
