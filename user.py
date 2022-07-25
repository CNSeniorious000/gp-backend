from secret import pool, app_id as ak, app_secret as sk
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
        if openid is not None:
            ids.set(code, openid, 120)
        return openid


@router.get("/test_md5", response_class=PlainTextResponse)
async def get_md5_hash(string: str):
    return md5(string.encode()).hexdigest()


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


class NewUserFromCode(BaseModel):
    code: str
    pwd: str | None
    email: str | None
    tel: str | None


class VerifyUser(BaseModel):
    id: str
    pwd: str


class VerifyUserFromCode(BaseModel):
    code: str
    pwd: str


@router.put("/test_id2user")
async def new_user(userinfo: NewUser):
    user = User(userinfo.id)
    if userinfo.pwd is not None:
        user.pwd = userinfo.pwd

    if userinfo.email is not None:
        user.email = userinfo.email

    if userinfo.tel is not None:
        user.tel = userinfo.tel


@router.put("/user")
async def new_user_from_code(userinfo: NewUserFromCode):
    user = User(await get_openid(userinfo.code))
    if userinfo.pwd is not None:
        user.pwd = userinfo.pwd

    if userinfo.email is not None:
        user.email = userinfo.email

    if userinfo.tel is not None:
        user.tel = userinfo.tel


@router.get("/id2user", response_class=ORJSONResponse)
async def get_user(id: str):
    if id in users:
        return User(id).profile
    else:
        return HTTPException(404, f"not user's id is {id}")


@router.get("/user", response_class=ORJSONResponse)
async def get_user_from_code(code: str):
    return await get_user(await get_openid(code))


@router.post("/id2login")
async def check_pwd(userinfo: VerifyUser):
    user = User(userinfo.id)
    if user.check_password(userinfo.pwd):
        return PlainTextResponse(jwt.encode({1: 2}, sk, "HS256"))
    else:
        return PlainTextResponse(status_code=401)


@router.post("/login")
async def check_pwd_from_code(userinfo: VerifyUserFromCode):
    user = User(await get_openid(userinfo.code))
    if user.check_password(userinfo.pwd):
        return PlainTextResponse(jwt.encode({1: 2}, sk, "HS256"))
    else:
        return PlainTextResponse(status_code=401)


@router.get("/test_verify_jwt")
async def decode(token: str):
    try:
        return ORJSONResponse(jwt.decode(token, sk, "HS256"))
    except jwt.InvalidSignatureError:
        return PlainTextResponse(status_code=403)
    except jwt.DecodeError:
        return PlainTextResponse(status_code=400)
    except Exception as err:
        raise HTTPException(500, f"{type(err).__name__}: {err.args[0]}")
