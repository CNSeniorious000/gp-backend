from ..common.secret import app_id as ak
from .impl import *

openid_cache = Redis(connection_pool=pool, db=1)


@router.get("/openid")
async def get_openid(code: str):
    try:
        return openid_cache[code]
    except KeyError:
        openid = (await client.get(
            "https://api.weixin.qq.com/sns/jscode2session", params=dict(
                appid=ak, secret=sk, js_code=code, grant_type="authorization_code"
            ))).json().get("openid", None)
        if openid is not None:
            openid_cache.set(code, openid, 120)
        return openid


class NewUserFromCode(BaseModel):
    code: str
    pwd: str | None
    email: str | None
    tel: str | None


@router.put("/wechat/user")
async def new_user_from_code(userinfo: NewUserFromCode):
    user = User(await get_openid(userinfo.code))
    if userinfo.pwd is not None:
        user.pwd = userinfo.pwd

    if userinfo.email is not None:
        user.email = userinfo.email

    if userinfo.tel is not None:
        user.tel = userinfo.tel


class VerifyUserFromCode(BaseModel):
    code: str
    pwd: str


@router.post("/wechat/user")
async def login_from_code(userinfo: VerifyUserFromCode):
    user = User(await get_openid(userinfo.code))
    if user.check_password(userinfo.pwd):
        return PlainTextResponse(jwt.encode({1: 2}, sk, "HS256"))
    else:
        return PlainTextResponse(status_code=401)


@router.get("/wechat/user", response_class=ORJSONResponse)
async def get_user_from_code(code: str):
    return await show_profile(await get_openid(code))
