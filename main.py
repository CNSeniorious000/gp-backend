from starlette.templating import Jinja2Templates
from starlette.responses import RedirectResponse
from brotli_asgi import BrotliMiddleware
from core.user import router as user_router
from starlette.requests import Request
from fastapi import FastAPI
from os import system

app = FastAPI(title="Guard Pine")
app.add_middleware(BrotliMiddleware, quality=11, minimum_size=256)
app.include_router(user_router)

count = 0

templates = Jinja2Templates("static")


@app.get("/")
async def root(request: Request):
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
    """trigger a git pull command in the terminal"""
    system("git pull")
    return RedirectResponse("/")
