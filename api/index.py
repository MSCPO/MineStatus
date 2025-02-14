from MineStatus import MineStatus
from fastapi import FastAPI, Request 
from fastapi.responses  import JSONResponse
import uvicorn

app = FastAPI()

@app.get("/")
async def Status(request: Request):
    host = request.query_params.get('ip')
    response = await MineStatus.status(host)
    return response

@app.get("/java/")
async def Status(request: Request):
    host = request.query_params.get('ip')
    response = await MineStatus.java_status(host)
    return response

@app.get("/bedrock/")
async def Status(request: Request):
    host = request.query_params.get('ip')
    response = await MineStatus.bedrock_status(host)
    return response

if __name__ == "__main__":
    uvicorn.run(app,  host="0.0.0.0", port=3000)