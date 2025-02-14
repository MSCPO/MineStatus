from fastapi import FastAPI, Request 
from fastapi.responses import JSONResponse 
from mcstatus import JavaServer, BedrockServer 
import asyncio
import uvicorn
 
app = FastAPI()
 
async def fetch_server_info(host: str):
    try:
        server = JavaServer.lookup(host)  
        status = server.status()  
        return {
            "online": True,
            "players": {
                "online": status.players.online,  
                "max": status.players.max  
            },
            "delay": status.latency,  
            "icon": status.icon,  
            "motd": {
                "plain": status.motd.to_plain(),  
                "html": status.motd.to_html(),  
                "minecraft": status.motd.to_minecraft(),  
                "ansi": status.motd.to_ansi()  
            }
        }
    except Exception as e:
        return {"error": str(e), "online": False}
 
async def fetch_bedrock_server_info(host: str):
    try:
        server = BedrockServer.lookup(host)  
        status = server.status()  
        return {
            "online": True,
            "players": {
                "online": status.players.online,  
                "max": status.players.max  
            },
            "delay": status.latency,  
            "version": status.version.name,  
            "motd": {
                "plain": status.motd.to_plain(),  
                "html": status.motd.to_html(),  
                "minecraft": status.motd.to_minecraft(),  
                "ansi": status.motd.to_ansi()  
            }
        }
    except Exception as e:
        return {"error": str(e), "online": False}
 
@app.get("/") 
async def return_data(request: Request):
    host = request.query_params.get('ip') 
    if not host:
        return JSONResponse(content={"error": "Missing 'ip' parameter"}, status_code=400)
 
    tasks = [
        fetch_server_info(host),
        fetch_bedrock_server_info(host)
    ]
    results = await asyncio.gather(*tasks,  return_exceptions=True)
 
    # Check if any server is online and return the first one found. If none are online, return an error message.
    for result in results:
        if isinstance(result, dict) and result.get("online",  False):
            return JSONResponse(content=result)
 
    return JSONResponse(content={"error": "Both servers are offline", "online": False}, status_code=500)
 
if __name__ == "__main__":
    uvicorn.run(app,  host="0.0.0.0", port=3000)
