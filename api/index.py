from api.MineStatus import MineStatus
from fastapi import FastAPI, Request 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses  import JSONResponse
import uvicorn

api = FastAPI()

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@api.get("/")
async def Status(request: Request):
    host = request.query_params.get('ip')
    response = await MineStatus.status(host)
    return response

@api.get("/java/")
async def Status(request: Request):
    host = request.query_params.get('ip')
    response = await MineStatus.java_status(host)
    return response

@api.get("/bedrock/")
async def Status(request: Request):
    host = request.query_params.get('ip')
    response = await MineStatus.bedrock_status(host)
    return response

if __name__ == "__main__":
    uvicorn.run(api,  host="0.0.0.0", port=3000)
