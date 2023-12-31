from ..info.news import get_article_info, ArticleDetails
from sqlmodel import SQLModel, Field, select, Session
from starlette.exceptions import HTTPException
from datetime import datetime, timezone
from fastapi import Depends, APIRouter
from ..common.auth import Bearer
from urllib.parse import urljoin
from ..common.sql import engine
from ..user.impl import ensure
from pydantic import BaseModel

router = APIRouter(tags=["favorite"])


@router.get("/parse", deprecated=True)
async def get_meta(url):
    """ # return title, description of a web page

    以前准备用来解析任意url的接口，现在作废了~
    """
    from ..info.common import get_html

    html = await get_html(url)
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
        if (redirected := tag["content"]) != url:
            result["redirected"] = redirected

    return result


class FavoriteItem(SQLModel, table=True):
    __tablename__ = "favorites"
    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    time_stamp: datetime = Field(default_factory=lambda: datetime.utcnow().replace(tzinfo=timezone.utc))
    article_id: int = Field(title="文章唯一标识")


class FavoriteResponse(BaseModel):
    id: int
    timeStamp: datetime
    articleId: int
    details: ArticleDetails | None


async def get_article_details(article_id: int) -> ArticleDetails | None:
    try:
        return await get_article_info(article_id)
    except HTTPException:
        return None


@router.get("/favorite", response_model=list[FavoriteResponse])
async def get_favorites(bearer: Bearer = Depends(), user_id: str = None):
    if user_id is None:
        owner = bearer.id
    else:
        owner = ensure(user_id)
        bearer.ensure_been_permitted_by(owner)

    with Session(engine) as session:
        return [
            {
                "id": item.id,
                "timeStamp": item.time_stamp,
                "articleId": item.article_id,
                "details": await get_article_details(article_id=item.article_id)
            }
            for item in session.exec(select(FavoriteItem).where(FavoriteItem.user_id == owner))
        ]


class FavoriteForm(BaseModel):
    user_id: str | None = None
    article_id: int = Field(alias="articleId")


@router.post("/favorite", response_model=FavoriteItem)
def add_favorite(data: FavoriteForm, bearer: Bearer = Depends()):
    if data.user_id is None:
        owner = bearer.id
    else:
        owner = ensure(data.user_id)
        bearer.ensure_been_permitted_by(owner)

    with Session(engine) as session:
        session.add(item := FavoriteItem(user_id=owner, article_id=data.article_id))
        session.commit()
        session.refresh(item)

    return item


@router.delete("/favorite")
def remove_favorite(id: int, bearer: Bearer = Depends()):
    with Session(engine) as session:
        favorite = session.exec(select(FavoriteItem).where(FavoriteItem.id == id)).one_or_none()
        if favorite is None:
            raise HTTPException(404, f"favorite {id} does not exist")

        bearer.ensure_been_permitted_by(favorite.user_id)

        session.delete(favorite)
        session.commit()

    return f"delete {favorite.id} successfully"
