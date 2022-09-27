from starlette.exceptions import HTTPException
from fastapi import Header, Cookie, Query
from .secret import app_secret_1 as sk_1
import jwt


class Bearer:
    def __init__(self,
                 authorization: str = Header(None, include_in_schema=False),
                 token_cookie: str = Cookie(None, include_in_schema=False, alias="token"),
                 token_query: str = Query(None, include_in_schema=False, alias="token")):
        auth = token_query or authorization or token_cookie
        if auth is None:
            raise self.no_auth_error

        try:
            if "Bearer " not in auth:
                raise self.bearer_error
            token = auth.removeprefix("Bearer ")
            result = jwt.decode(token, sk_1, "HS256")

            self.id = result["id"]

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
        payload = jwt.decode(token.removeprefix("Bearer "), sk_1, "HS256")
        return payload["id"]
    except jwt.InvalidSignatureError as err:
        raise HTTPException(403, str(err))
    except jwt.DecodeError as err:
        raise HTTPException(400, str(err))
