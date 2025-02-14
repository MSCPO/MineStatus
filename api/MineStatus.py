import asyncio

from mcstatus import BedrockServer, JavaServer
from mcstatus.status_response import BedrockStatusResponse, JavaStatusResponse


async def status(host: str) -> dict:
    """
    Retrieves the status of a Minecraft server, which can be either Java or Bedrock.

    Args:
        host (str): The hostname or IP address of the server to query.

    Returns:
        dict: A dictionary containing the server's status. If an error occurs,
              the dictionary will contain an error message.
    """
    try:
        response = await get_server_status(host)
        return format_response(response)
    except Exception as e:
        return {"error": f"Failed to get server status: {e}"}


async def get_server_status(host: str):
    """
    Pings the server for both Java and Bedrock editions, returning the first successful response.

    Args:
        host (str): The hostname or IP address of the server to query.

    Returns:
        JavaStatusResponse | BedrockStatusResponse: The first successful server status response
                                                     from either Java or Bedrock server.

    Raises:
        ValueError: If neither Java nor Bedrock server responses are successful.
    """
    tasks = [handle_java(host), handle_bedrock(host)]

    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    # If any task completed successfully, we get the first result
    for task in done:
        return task.result()

    # If no tasks were successful
    raise ValueError("No tasks were successful. Is server offline?")


async def handle_java(host: str) -> JavaStatusResponse:
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


async def handle_bedrock(host: str) -> BedrockStatusResponse:
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


def format_response(response: JavaStatusResponse | BedrockStatusResponse) -> dict:
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
    if isinstance(response, JavaStatusResponse):
        return {
            "online": True,
            "players": {
                "online": response.players.online,
                "max": response.players.max,
            },
            "delay": response.latency,
            "version": response.version.name,
            "motd": format_motd(response.motd),
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
            "motd": format_motd(response.motd),
        }
    else:
        raise ValueError("Unexpected response type")


def format_motd(motd):
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
