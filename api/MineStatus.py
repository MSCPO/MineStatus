import asyncio
from mcstatus import BedrockServer, JavaServer
from mcstatus.status_response  import BedrockStatusResponse, JavaStatusResponse

class MineStatus:
    async def status(host: str) -> dict:
        """Get status from server, which can be Java or Bedrock.

        The function will ping server as Java and as Bedrock in one time, and return the first response.
        """
        done, pending = await asyncio.wait( 
            {
                asyncio.create_task(MineStatus.handle_java(host),  name="Get status as Java"),
                asyncio.create_task(MineStatus.handle_bedrock(host),  name="Get status as Bedrock"),
            },
            return_when=asyncio.FIRST_COMPLETED,
        )

        success_task = await MineStatus.handle_exceptions(done,  pending)

        if success_task is None:
            return {"error": "No tasks were successful. Is server offline?"}

        response = success_task.result() 
        return MineStatus.format_response(response) 

    async def java_status(host: str) -> dict:
        """Get status from server, which can be Java.

        The function will ping server as Java.
        """
        try:
            response = await MineStatus.handle_java(host) 
            return MineStatus.format_response(response) 
        except Exception as e:
            return {"error": f"Failed to get Java status: {e}"}

    async def bedrock_status(host: str) -> dict:
        """Get status from server, which can be Bedrock.

        The function will ping server as Bedrock.
        """
        try:
            response = await MineStatus.handle_bedrock(host) 
            return MineStatus.format_response(response) 
        except Exception as e:
            return {"error": f"Failed to get Bedrock status: {e}"}

    async def handle_exceptions(done: set[asyncio.Task], pending: set[asyncio.Task]) -> asyncio.Task | None:
        """Handle exceptions from tasks.

        Also, cancel all pending tasks, if found correct one.
        """
        if len(done) == 0:
            return {"error": "No tasks were given to `done` set."}

        for task in done:
            if task.exception()  is not None:
                if len(pending) > 0:
                    return await MineStatus.handle_exceptions(*await  asyncio.wait(pending,  return_when=asyncio.FIRST_COMPLETED))
            else:
                for pending_task in pending:
                    pending_task.cancel() 
                return task

        return None

    async def handle_java(host: str) -> JavaStatusResponse:
        """A wrapper around mcstatus, to compress it in one function."""
        try:
            server = await JavaServer.async_lookup(host) 
            return await server.async_status() 
        except Exception as e:
            return {"error": f"Failed to connect to Java server at {host}: {e}"}

    async def handle_bedrock(host: str) -> BedrockStatusResponse:
        """A wrapper around mcstatus, to compress it in one function."""
        try:
            server = BedrockServer.lookup(host) 
            return await server.async_status() 
        except Exception as e:
            return {"error": f"Failed to connect to Bedrock server at {host}: {e}"}

    def format_response(response: JavaStatusResponse | BedrockStatusResponse) -> dict:
        """Format the response into a dictionary with the required structure."""
        if isinstance(response, JavaStatusResponse):
            return {
                "online": True,
                "players": {
                    "online": response.players.online, 
                    "max": response.players.max, 
                },
                "delay": response.latency, 
                "version": response.version.name, 
                "motd": {
                    "plain": response.motd.to_plain(), 
                    "html": response.motd.to_html(), 
                    "minecraft": response.motd.to_minecraft(), 
                    "ansi": response.motd.to_ansi() 
                }
            }
        elif isinstance(response, BedrockStatusResponse):
            return {
                "online": True,
                "players": {
                    "online": response.players_online, 
                    "max": response.players_max, 
                },
                "delay": response.latency, 
                "version": response.version.version, 
                "motd": {
                    "plain": response.motd.to_plain(), 
                    "html": response.motd.to_html(), 
                    "minecraft": response.motd.to_minecraft(), 
                    "ansi": response.motd.to_ansi() 
                }
            }
        else:
            return response