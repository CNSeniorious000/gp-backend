from fastapi import APIRouter, Response, Path
from httpx import AsyncClient
from random import choice, randrange
from pydantic import BaseModel

router = APIRouter(tags=["card"])
names = open("core/card/names.txt", encoding="utf-8").read().split()
client = AsyncClient(http2=True, follow_redirects=True, verify=False)


class HomeCard(BaseModel):
    id: int
    name: str
    image_url: str
    location: str
    view_count: int
    search_count: int


def get_random_name():
    return choice(names)


@router.get("/home/{n:int}")
@router.get("/home")
def get_homes(n: int = Path(ge=1, example=3)):
    return [
        HomeCard(id=i, name=choice(names), location="金凤路18号",
                 view_count=randrange(100, 100_000), search_count=randrange(100, 100_000),
                 image_url=f"https://gp.muspimerol.site/image/home/{randrange(10)}")
        for i in range(n)
    ]


image_cache = {}


@router.get("/image/home/{n}")
async def get_home_image(n: int):
    if n in image_cache:
        response = image_cache[n]
        return response

    r = await client.get("https://place.dog/800/400")
    headers = r.headers
    for key in ["content-length", "content-length"]:
        if key in headers:
            del headers[key]

    response = Response(r.content, r.status_code, headers)
    image_cache[n] = response
    return response
