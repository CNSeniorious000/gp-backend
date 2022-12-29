from fastapi import APIRouter, HTTPException
from httpx import AsyncClient
from bs4 import BeautifulSoup
import re

router = APIRouter(tags=["info"])

get_id_reg = re.compile(r"\d+")
sub_str_reg = re.compile(r"\n|\r|\t| +")

client = AsyncClient(http2=True, base_url="https://www.yanglao.com.cn/", headers={
    "user-agent": "gp-scraper / Guard Pine (https://gp.muspimerol.site/)",
    "x-scraper-contact-email": "admin@muspimerol.site",
    "x-gp-repo": "https://jihulab.com/CNSeniorious000/gp-backend"
})


async def get_html(path: str) -> BeautifulSoup:
    res = await client.get(path)
    if res.is_success:
        return BeautifulSoup(res.text, "lxml")
    else:
        raise HTTPException(res.status_code, res.text)
