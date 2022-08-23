from starlette.responses import RedirectResponse, HTMLResponse
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from core.user import router as user_router
from brotli_asgi import BrotliMiddleware
from starlette.requests import Request
from httpx import AsyncClient
from fastapi import FastAPI
from os import system

app = FastAPI(title="守护青松 Guard Pine")
app.add_middleware(BrotliMiddleware, quality=11, minimum_size=256)
app.include_router(user_router)

count = 0

templates = Jinja2Templates("static")


@app.get("/")
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


@app.get("/refresh")
def git_pull():
    """trigger a git pull command in local terminal and redirect to document page"""
    system("git pull")
    return RedirectResponse("/docs")


client = AsyncClient(http2=True)


async def get_iframe(url, title=None) -> bytes:
    return (await client.get("http://localhost/link", params={"url": url, "title": title})).content


@app.get("/notes", response_class=HTMLResponse)
async def get_notes():
    return await get_iframe("https://www.craft.do/s/bbKnMXuNDudwop", "守护青松 - 开发者说")


@app.get("/apifox", response_class=HTMLResponse)
async def get_apidoc():
    return await get_iframe("https://www.apifox.cn/apidoc/project-1338127", "守护青松 - 接口文档")


app.mount("/static", StaticFiles(directory="static"))
app.mount("/", StaticFiles(directory="static"))
