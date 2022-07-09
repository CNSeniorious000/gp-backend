from fastapi import FastAPI
from starlette.templating import Jinja2Templates
from starlette.requests import Request

app = FastAPI()

count = 0

templates = Jinja2Templates(".")


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
