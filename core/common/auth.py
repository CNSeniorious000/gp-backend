from starlette.exceptions import HTTPException
from .secret import app_secret as sk
from fastapi import Header, Cookie
import jwt


class Bearer:
    def __init__(self, authorization: str = Header(default=None), token: str = Cookie(default=None)):
        auth = authorization or token
        if auth is None:
            raise self.no_auth_error

        try:
            if "Bearer " not in auth:
                raise self.bearer_error
            token = auth.removeprefix("Bearer ")
            result = jwt.decode(token, sk, "HS256")

            self.id = result["id"]
            self.scopes = result.get("scope").split()

        except (KeyError, jwt.InvalidSignatureError) as err:
            raise HTTPException(403, str(err))
        except jwt.DecodeError:
            raise self.bearer_error

    @property
    def user(self):
        from ..user.impl import User
        return User(self.id)

    @property
    def no_auth_error(self):
        return HTTPException(401, "can't find token in either headers or cookies", {"WWW-Authenticate": "Bearer"})

    @property
    def bearer_error(self):
        return HTTPException(400, f"broken token")


def parse_id(token: str):
    try:
        payload = jwt.decode(token, sk, "HS256")
        return payload["id"]
    except jwt.InvalidSignatureError as err:
        raise HTTPException(403, str(err))
    except jwt.DecodeError as err:
        raise HTTPException(400, str(err))
