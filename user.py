from fastapi.responses import ORJSONResponse
from cachetools.func import ttl_cache
from pydantic import BaseModel
from fastapi import APIRouter
from httpx import AsyncClient
from functools import cache
from hashlib import md5
from redis import Redis
from secret import pool, app_id as ak, app_secret as sk

router = APIRouter()
client = AsyncClient(http2=True)
users = Redis(connection_pool=pool, db=0)
ids = Redis(connection_pool=pool, db=1)


@router.get("/openid")
async def get_openid(code: str):
    try:
        return ids[code]
    except KeyError:
        openid = (await client.get(
            "https://api.weixin.qq.com/sns/jscode2session", params=dict(
                appid=ak, secret=sk, js_code=code, grant_type="authorization_code"
            ))).json().get("openid", None)
        ids.set(code, openid, 120)
        return openid


class User:
    @cache
    def __new__(cls, openid):
        return super().__new__(cls)

    def __init__(self, openid):
        self.openid = openid

    def __repr__(self):
        return f"User(openid={self.openid})"

    @staticmethod
    def field(key):
        def getter(self: "User"):
            return users.hget(self.openid, key)

        def setter(self: "User", value):
            users.hset(self.openid, key, value)

        def deleter(self: "User"):
            users.hdel(self.openid, key)

        return property(getter, setter, deleter)

    pwd_hash = field("p")
    email = field("e")
    tel = field("t")


class NewUser(BaseModel):
    code: str
    pwd: str | None
    email: str | None
    tel: str | None


class VerifyUser(BaseModel):
    code: str
    pwd: str


@router.put("/user")
async def new_user(userinfo: NewUser):
    user = User(await get_openid(userinfo.code))
    if userinfo.pwd is not None:
        user.pwd_hash = md5(userinfo.pwd).digest()

    if userinfo.email is not None:
        user.email = userinfo.email

    if userinfo.tel is not None:
        user.tel = userinfo.tel


@router.get("/user")
async def show_user(code: str):
    user = User(await get_openid(code))
    return ORJSONResponse({"tel": user.tel, "email": user.email})


@router.post("/login")
async def check_pwd(userinfo: VerifyUser):
    user = User(await get_openid(userinfo.code))
    return user.pwd_hash == md5(userinfo.pwd.encode()).digest()
