from fastmcp import Client
from mcp.types import TextContent, TextResourceContents
import asyncio


async def test_server():
    async with Client("test_server.py") as client:
        # List available tools
        tools = await client.list_tools()
        print("Available tools:", [t.name for t in tools])

        # Add a task
        result = await client.call_tool(
            "add_task",
            {"title": "Learn MCP", "description": "Build a task tracker with FastMCP"},
        )
        assert isinstance(result.content[0], TextContent)
        print("\nAdded task:", result.content[0].text)

        # View all tasks
        resources = await client.list_resources()
        print("\nAvailable resources:", [r.uri for r in resources])

        task_list = await client.read_resource("tasks://all")
        assert isinstance(task_list[0], TextResourceContents)
        print("\nAll tasks:\n", task_list[0].text)


if __name__ == "__main__":
    asyncio.run(test_server())
