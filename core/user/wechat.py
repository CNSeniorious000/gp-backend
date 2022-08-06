from ..common.secret import app_id as ak
from .impl import *

openid_cache = Redis(connection_pool=pool, db=1)


@router.get("/openid", response_class=PlainTextResponse)
async def get_openid(code: str):
    """ # 获取微信用户openid
    ## [登录凭证校验](https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-login/code2Session.html)
    - 结果将在服务端缓存120秒
    - 每个用户每分钟100次
    - 通过 wx.login 接口获得临时登录凭证 code
    > 小程序登录流程见 <https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/login.html>
    """
    try:
        return openid_cache[code]
    except KeyError:
        response: dict = (await client.get(
            "https://api.weixin.qq.com/sns/jscode2session", params=dict(
                appid=ak, secret=sk, js_code=code, grant_type="authorization_code"
            ))).json()
        if (openid := response.get("openid", None)) is not None:
            openid_cache.set(code, openid, 120)
            return openid
        else:
            match response["errcode"]:
                case 40029:
                    raise HTTPException(400, "js_code无效")
                case 45011:
                    raise HTTPException(429, "API调用太频繁，请稍候再试")
                case 40226:
                    raise HTTPException(451, "高风险等级用户，小程序登录拦截。风险等级详见"
                                             "[用户安全解方案](https://developers.weixin.qq.com/"
                                             "miniprogram/dev/framework/operation.html")
                case -1:
                    raise HTTPException(500, "微信接口繁忙，此时请开发者稍候再试")


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