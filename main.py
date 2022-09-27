from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from starlette.responses import RedirectResponse, HTMLResponse
from core.userdata import activity, favorite, reminder
from core.common.sql import create_db_and_tables
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from fastapi.responses import ORJSONResponse
from core.user import router, dev_router
from brotli_asgi import BrotliMiddleware
from starlette.requests import Request
from fastapi import FastAPI, Depends
from core.common.secret import host
from core.common.auth import Bearer
from core.user import relation
from httpx import AsyncClient
from core import card
from os import system

create_db_and_tables()
app = FastAPI(title="守护青松 Guard Pine", version="0.3.2",
              license_info={"name": "MIT License", "url": "https://mit-license.org/"},
              contact={"name": "Muspi Merol", "url": "https://muspimerol.site/", "email": "admin@muspimerol.site"},
              openapi_tags=[
                  {"name": "dev", "description": "Develop tools, **will be removed in the future.**"},
                  {"name": "user", "description": "**User login** and more."},
                  {"name": "reminder", "description": "备忘录增删查改"},
                  {"name": "activity", "description": "活动增删查改"},
                  {"name": "favorite", "description": "收藏增删查改"},
                  {"name": "relation", "description": "关系增删查改"},
                  {"name": "card", "description": "首页卡片 **fake news**"}
              ],
              # description=open("./readme.md", encoding="utf-8").read(),
              description="### “守护青松”国家级大创项目 [部署地址](https://muspimerol.site:9999/)",
              docs_url=None, redoc_url=None, default_response_class=ORJSONResponse)
app.add_middleware(BrotliMiddleware, quality=11, minimum_size=256)

count = 0

templates = Jinja2Templates("static")


@app.get("/me", tags=["dev"])
async def read_me(bearer: Bearer = Depends()):
    return {
        "id": bearer.id,
        "permissions": bearer.user.permissions,
        "meta": bearer.user.meta
    }


@app.get("/", include_in_schema=False)
async def index_page(request: Request):
    global count
    count += 1
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "count": count,
        }
    )


@dev_router.get("/refresh")
def git_pull():
    """trigger a git pull command in local terminal and redirect to document page"""
    system("git pull")
    return RedirectResponse("/docs")


client = AsyncClient(http2=True)


async def get_iframe(url, title=None) -> bytes:
    # noinspection HttpUrlsUsage
    return (await client.get(f"http://{host}/link", params={"url": url, "title": title})).content


@app.get("/notes", response_class=HTMLResponse, include_in_schema=False)
async def get_notes():
    return await get_iframe("https://www.craft.do/s/bbKnMXuNDudwop", "守护青松 - 开发者说")


@app.get("/apifox", response_class=HTMLResponse, include_in_schema=False)
async def get_apidoc():
    return await get_iframe("https://www.apifox.cn/apidoc/project-1338127", "守护青松 - 接口文档")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(request: Request):
    await request.send_push_promise("/openapi.json")
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_html(request: Request):
    await request.send_push_promise("/openapi.json")
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
    )


app.include_router(dev_router)
app.include_router(router)
app.include_router(reminder.router)
app.include_router(relation.router)
app.include_router(activity.router)
app.include_router(favorite.router)
app.include_router(card.router)
app.mount("/static", StaticFiles(directory="static"))
app.mount("/", StaticFiles(directory="static"))
