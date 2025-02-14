import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from MineStatus import handle_bedrock, handle_java, status

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
    host = request.query_params.get("ip")
    return await status(host) if host else {"error": "Missing 'ip' parameter"}


@app.get("/java/")
async def _(request: Request):
    if host := request.query_params.get("ip"):
        return await handle_java(host)
    else:
        return {"error": "Missing 'ip' parameter"}


@app.get("/bedrock/")
async def _(request: Request):
    if host := request.query_params.get("ip"):
        return await handle_bedrock(host)
    else:
        return {"error": "Missing 'ip' parameter"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
