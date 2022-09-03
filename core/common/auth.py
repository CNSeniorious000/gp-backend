from starlette.exceptions import HTTPException
from .secret import app_secret as sk
from time import time
import jwt


def parse_id(token: str):
    try:
        payload = jwt.decode(token, sk, "HS256")

        if (stamp := payload.get("time")) and (expire := payload.get("expire")):
            if stamp + expire <= time():
                raise HTTPException(401, "timeout")
        return payload["id"]
    except jwt.InvalidSignatureError as err:
        raise HTTPException(403, str(err))
    except jwt.DecodeError as err:
        raise HTTPException(400, str(err))
