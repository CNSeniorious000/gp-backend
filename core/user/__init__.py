from .impl import *
from .wechat import *


@router.get("/test_md5", response_class=PlainTextResponse)
async def get_md5_hash(string: str):
    return md5(string.encode()).hexdigest()


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


__all__ = {"router"}
