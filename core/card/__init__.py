from fastapi import APIRouter, Response
from httpx import AsyncClient
from random import choice, randrange
from pydantic import BaseModel, Field

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


@router.get("/home/{n}")
def get_homes(n: int = Field(3, ge=1)):
    return [
        HomeCard(id=i, name=choice(names), image_url="/image/home", location="金凤路18号",
                 view_count=randrange(100, 100_000), search_count=randrange(100, 100_000))
        for i in range(n)
    ]


@router.get("/image/home")
async def get_home_image():
    r = await client.get("https://place.dog/800/400")
    headers = r.headers
    for key in ["content-length", "content-length"]:
        if key in headers:
            del headers[key]
    return Response(r.content, r.status_code, headers=headers)
