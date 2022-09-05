from sqlmodel import SQLModel, Field, select, Session
from starlette.exceptions import HTTPException
from httpx import AsyncClient, ReadTimeout
from functools import cached_property
from ..common.auth import parse_id
from urllib.parse import urljoin
from ..common.sql import engine
from pydantic import BaseModel
from fastapi import APIRouter
from bs4 import BeautifulSoup
from cachetools import TTLCache

router = APIRouter(tags=["favorite"])

client = AsyncClient(http2=True, follow_redirects=True)

url_meta_cache = TTLCache(1234, 1234)


@router.get("/parse")
async def get_meta(url):
    """ # return title, description of a web page
    TODO:
    - [x] html
    - [ ] image
    - [ ] pdf
    """
    if url in url_meta_cache:
        return url_meta_cache[url]

    try:
        response = await client.get(url)
    except ReadTimeout as err:
        url_meta_cache[url] = result = {"title": "ReadTimeout", "abstract": str(err)}
        return result

    html = BeautifulSoup(response.text, features="lxml")
    result = {}

    # title
    if tag := html.find("meta", {"property": "og:title"}):
        result["title"] = tag["content"]
    elif (tag := html.find("title")) and tag.text:
        result["title"] = tag.text

    # abstract
    if tag := html.find("meta", {"property": "og:description"}):
        result["abstract"] = tag["content"]

    # author
    if tag := html.find("meta", {"property": "og:article:author"}):
        result["author"] = tag["content"]

    # origin
    if tag := html.find("meta", {"property": "og:site_name"}):
        result["source"] = tag["content"]

    # avatar
    if tag := html.find("meta", {"property": "og:image"}):
        result["image"] = urljoin(url, tag["content"])
    elif tag := html.find("link", {"rel": "icon"}):
        result["image"] = urljoin(url, tag["href"])

    # shortcut
    if tag := html.find("meta", {"property": "og:url"}):
        result["redirected"] = tag["content"]
    elif str(response.url) != url:
        result["redirected"] = str(response.url)

    url_meta_cache[url] = result

    return result


class FavoriteItem(SQLModel, table=True):
    __tablename__ = "favorites"
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    timeStamp: int
    url: str


class Favorite:
    def __init__(self, id: int):
        self.id = id

    @cached_property
    def item(self):
        with Session(engine) as session:
            return session.exec(select(FavoriteItem).where(FavoriteItem.id == self.id)).one()

    @property
    def user(self):
        from ..user.impl import User
        return User(self.item.user_id)

    @property
    def url(self):
        return self.item.url

    @property
    def time_stamp(self):
        return self.item.timeStamp

    async def get_full_information(self):
        result = {
            "id": self.id,
            "url": self.url,
            "title": None,
            "source": None,
            "abstract": None,
            "timeStamp": self.time_stamp
        }
        result.update(await get_meta(self.url))
        return result


@router.get("/favorite")
async def get_favorites(token: str):
    user_id = parse_id(token)
    with Session(engine) as session:
        return [
            await Favorite(i.id).get_full_information()
            for i in session.exec(select(FavoriteItem).where(FavoriteItem.user_id == user_id))
        ]


class FavoriteForm(BaseModel):
    url: str
    timeStamp: int
    token: str


@router.put("/favorite")
def add_favorite(form: FavoriteForm):
    user_id = parse_id(form.token)
    with Session(engine) as session:
        session.add(FavoriteItem(user_id=user_id, url=form.url, timeStamp=form.timeStamp))
        session.commit()


@router.delete("/favorite")
def remove_favorite(token: str, id: str):
    user_id = parse_id(token)
    with Session(engine) as session:
        favorite = session.exec(select(FavoriteItem).where(FavoriteItem.id == id)).one()
        if user_id == favorite.user_id:
            session.delete(favorite)
            session.commit()
        else:
            raise HTTPException(401, f"favorite {id} does not belongs to {user_id}")
