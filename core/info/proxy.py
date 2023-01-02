from .common import router, client
from starlette.responses import Response


@router.get("/proxy")
async def fetch_http_resource(url):
    response = await client.get(url, follow_redirects=True)
    if "content-length" in response.headers:
        del response.headers["content-length"]
    return Response(response.content, response.status_code, response.headers)
