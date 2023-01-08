from ..common.secret import app_id_0 as ak_0, app_id_1 as ak_1, app_secret_0 as sk_0
from .impl import *


@router.get("/openid", response_class=PlainTextResponse, deprecated=True,
            responses={400: {"description": "js_code无效"},
                       429: {"description": "API调用太频繁，请稍候再试"},
                       410: {"description": "code been used"},
                       451: {"description": "高风险等级用户，小程序登录拦截"},
                       500: {"description": "微信接口繁忙，此时请开发者稍候再试"}})
async def get_openid(code: str, is_elder: bool):
    """ # 获取微信用户openid
    ## [登录凭证校验](https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-login/code2Session.html)
    - 结果将在服务端缓存120秒
    - 每个用户每分钟100次
    - 通过 wx.login 接口获得临时登录凭证 code
    > 小程序登录流程见 <https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/login.html>
    """
    response: dict = (await client.get(
        "https://api.weixin.qq.com/sns/jscode2session", params=dict(
            appid=ak_1 if is_elder else ak_0, secret=sk_1 if is_elder else sk_0,
            js_code=code, grant_type="authorization_code"
        ))).json()
    if (openid := response.get("openid")) is not None:
        return openid
    else:
        match response["errcode"]:
            case 40029:
                raise HTTPException(400, "js_code无效")
            case 45011:
                raise HTTPException(429, "API调用太频繁，请稍候再试")
            case 40163:
                raise HTTPException(410, "code been used")
            case 40226:
                raise HTTPException(451, "高风险等级用户，小程序登录拦截。风险等级详见"
                                         "[用户安全解方案](https://developers.weixin.qq.com/"
                                         "miniprogram/dev/framework/operation.html")
            case -1:
                raise HTTPException(500, "微信接口繁忙，此时请开发者稍候再试")


@router.get("/wechat/user")
async def wechat_exist(code, is_elder: bool):
    return exist(await get_openid(code, is_elder))


@router.post("/wechat/user")
async def wechat_login(code, is_elder: bool):
    id = await get_openid(code, is_elder)
    if not exist(id):
        await register(UserPut(id=id, pwd=sk_1 + id))
    return await login(id, sk_1 + id)
