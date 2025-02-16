import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api import MineStatus

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],  # Allows all origins
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.get("/")
async def _(request: Request):
    if host := request.query_params.get("ip"):
        return await MineStatus.unclassified(host)
    else:
        return {"error": "Missing 'ip' parameter"}


@app.get("/java/")
async def _(request: Request):
    if host := request.query_params.get("ip"):
        response = await MineStatus.handle_java_stats(host)
        return MineStatus.format_response(response)
    else:
        return {"error": "Missing 'ip' parameter"}


@app.get("/bedrock/")
async def _(request: Request):
    if host := request.query_params.get("ip"):
        response = await MineStatus.handle_bedrock_stats(host)
        return MineStatus.format_response(response)
    else:
        return {"error": "Missing 'ip' parameter"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
