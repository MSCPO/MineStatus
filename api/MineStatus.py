import asyncio
from mcstatus import BedrockServer, JavaServer
from mcstatus.status_response  import BedrockStatusResponse, JavaStatusResponse

class get_status:
    """
    A class for get minecraft server status.
    """
    async def java(host: str):
        """
        Retrieves the status of the Java Minecraft server.

        Args:
            host (str): The hostname or IP address of the Java server to query.
        
        Returns:
            dict: A dictionary containing the server's status. If an error occurs,
                        the dictionary will contain an error message.
        """
        try:
            response = await handle_tools.java(host)
            return format_tools.response(response)
        except Exception as e:
            return {"error": str(e)}

    async def bedrock(host: str):
        """
        Retrieves the status of the Bedrock Minecraft server.

        Args:
            host (str): The hostname or IP address of the Bedrock server to query.
        
        Returns:
            dict: A dictionary containing the server's status. If an error occurs,
                        the dictionary will contain an error message.
        """
        try:
            response = await handle_tools.bedrock(host)
            return format_tools.response(response)
        except Exception as e:
            return {"error": str(e)}

    async def unclassified(host: str):
        """
        Retrieves the status of a Minecraft server, which can be either Java or Bedrock.

        Args:
            host (str): The hostname or IP address of the any server to query.

        Returns:
            dict: A dictionary containing the server's status. If an error occurs,
                        the dictionary will contain an error message.
        """
        tasks = [
            asyncio.create_task(handle_tools.java(host), name="Get status as Java"),
            asyncio.create_task(handle_tools.bedrock(host), name="Get status as Bedrock")
        ]
        last_error = None 
        for task in asyncio.as_completed(tasks): 
            try:
                result = await task 
                for task in tasks:
                    if not task.done()  and not task.cancelled(): 
                        task.cancel() 
                return format_tools.response(result) 
            except Exception as e:
                last_error = e 
        return {"error": str(last_error) or "No server status detected, Is server offline?"}

class handle_tools:
    """
    A class for handles the status retrieval based on the server type.
    """
    async def java(host: str) -> JavaStatusResponse:
        """
        Pings a Java Minecraft server and returns its status.

        Args:
            host (str): The hostname or IP address of the Java server to query.

        Returns:
            JavaStatusResponse: The status of the Java Minecraft server.

        Raises:
            ValueError: If the connection to the Java server fails.
        """
        try:
            server = await JavaServer.async_lookup(host)
            return await server.async_status()
        except Exception as e:
            raise ValueError(f"Failed to connect to Java server at {host}: {e}") from e


    async def bedrock(host: str) -> BedrockStatusResponse:
        """
        Pings a Bedrock Minecraft server and returns its status.

        Args:
            host (str): The hostname or IP address of the Bedrock server to query.

        Returns:
            BedrockStatusResponse: The status of the Bedrock Minecraft server.

        Raises:
            ValueError: If the connection to the Bedrock server fails.
        """
        try:
            server = BedrockServer.lookup(host)
            return await server.async_status()
        except Exception as e:
            raise ValueError(f"Failed to connect to Bedrock server at {host}: {e}") from e

class format_tools:
    """
    A class for format response and motd.
    """
    def response(response: JavaStatusResponse | BedrockStatusResponse) -> dict:
        """
        Formats the server status response into a dictionary with the required structure.

        Args:
            response (JavaStatusResponse | BedrockStatusResponse): The server status response
                                                                from either Java or Bedrock server.

        Returns:
            dict: A dictionary containing the formatted server status information.

        Raises:
            ValueError: If the response type is not JavaStatusResponse or BedrockStatusResponse.
        """
        if isinstance(response, JavaStatusResponse | BedrockStatusResponse):
            return {
                "online": True,
                "players": {
                    "online": response.players.online,
                    "max": response.players.max,
                },
                "delay": response.latency,
                "version": response.version.name,
                "motd": format_tools.motd(response.motd),
            }
        else:
            raise ValueError("Unexpected response type")

    def motd(motd):
        """
        Helper function to format the Message of the Day (MOTD) into various formats.

        Args:
            motd: The MOTD object that contains the server's message.

        Returns:
            dict: A dictionary with the MOTD in different formats such as plain, HTML, Minecraft, and ANSI.
        """
        return {
            "plain": motd.to_plain(),
            "html": motd.to_html(),
            "minecraft": motd.to_minecraft(),
            "ansi": motd.to_ansi(),
        }