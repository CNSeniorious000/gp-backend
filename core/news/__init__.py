from fastapi import APIRouter, Path, Query, HTTPException
from pydantic import BaseModel, Field
from httpx import AsyncClient
from bs4 import BeautifulSoup
import re

router = APIRouter(tags=["news"])
client = AsyncClient(http2=True, base_url="https://www.yanglao.com.cn/")
get_id_reg = re.compile(r"\d+")


class Article(BaseModel):
    articleId: int = Field(alias="article_id", title="文章唯一标识，用于请求文章详情")
    title: str = Field(title="文章标题")

    class Config:
        schema_extra = {"example": {"articleId": 521502, "title": "大兴区精心康复托养中心十二月康复展示"}}


class ArticleWithDate(Article):
    date: str = Field(title="文章发布日期")

    class Config:
        schema_extra = {
            "example": {"articleId": 521433, "title": "地方立法密集落地优化养老服务升级", "date": "2022-12-12"},
        }


class ArticleDetails(BaseModel):
    title: str = Field(title="文章标题")
    source: str = Field(title="文章来源", description="可能为空字符串")
    hits: int = Field(title="浏览量", description="经测试就是请求次数")
    datetime: str = Field(title="文章发布日期和时间", description="按照 yyyy-mm-dd hh:mm:ss 格式")
    html: str = Field(title="正文html", description="可能很长，可能包含图片文字甚至富文本")
    related: list[Article] = Field(title="相关文章", description="可以搞成一个列表")

    class Config:
        schema_extra = {
            "example": {
                "title": "2022天津河西区老年痴呆养老院哪家好？2022河西区老年痴呆养老院多少钱？",
                "source": "国家卫健委门户网站",
                "hits": 27,
                "datetime": "2022-12-27 15:10:26",
                "html": """\
<div class="news-content">
 位于上海市静安区保德路545号的**护理院也是<a href="https://www.yanglao.com.cn/resthome">收阿尔兹海默老人的养老机构</a>。
</div>""",
                "related": [
                    {'articleId': 521504, 'title': '仙栖谷精神障碍托养中心告诉您精神障碍患者“阳”了怎么办？'},
                    {'articleId': 521501, 'title': '椿萱茂日间照料｜家门口的健康养老很幸福'},
                    {'articleId': 521497, 'title': '2022成都青羊区老年痴呆养老院有哪些，2022青羊区认知症养老院地址'}
                ]
            }
        }


@router.get("/articles", response_model=list[ArticleWithDate], responses={404: {"description": "分页超出范围"}})
async def get_articles(page: int | None = Query(1, description="分页（从1开始）", ge=1)) -> list[ArticleWithDate]:
    """### fetch new articles directly from the web"""

    dom = BeautifulSoup((await client.get(f"/article_{page}")).text, "lxml")
    news_list = dom.select_one("ul.news-list")
    if news_list is None:
        raise HTTPException(404, "page not found")
    return [ArticleWithDate(
        article_id=int(get_id_reg.findall(li.a["href"])[0]), title=li.a.string, date=li.span.string
    ) for li in news_list.find_all("li")]


@router.get("/article/{articleId}", response_model=ArticleDetails, responses={404: {"description": "不存在该文章"}})
async def get_article_info(article_id: int = Path(alias="articleId", description="文章唯一标识")) -> ArticleDetails:
    """### get an article's details and its related articles"""

    dom = BeautifulSoup((await client.get(f"/article/{article_id}.html")).text, "lxml")
    news_view = dom.select_one("div.news-view")
    if news_view is None:
        raise HTTPException(404, "article not found")
    li_source, li_hits, li_datetime = news_view.select("ul.info > li")[:3]
    return ArticleDetails(
        title=news_view.h1.string,
        source=li_source.string.strip()[3:],
        hits=int(li_hits.string.strip()[3:]),
        datetime=li_datetime.string.strip(),
        html=news_view.select_one("div.news-content").prettify(),
        related=[
            Article(article_id=int(get_id_reg.findall(li.a["href"])[0]), title=li.a["title"])
            for li in news_view.select("div.related-read li")
        ]
    )
