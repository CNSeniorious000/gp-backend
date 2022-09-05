from starlette.exceptions import HTTPException
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


class WeChatForm(BaseModel):
    code: str


@router.get("/wechat/user")
async def wechat_exist(code: str):
    return exist(await get_openid(code))


@router.put("/wechat/user", deprecated=True)
async def wechat_register(form: WeChatForm):
    id = await get_openid(form.code)
    return await register(UserForm(id=id, pwd=sk + id))


@router.post("/wechat/user")
async def wechat_login(form: WeChatForm):
    id = await get_openid(form.code)
    if not exist(id):
        await register(UserForm(id=id, pwd=sk + id))
    return await login(UserForm(id=id, pwd=sk + id))
