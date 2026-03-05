from fastmcp import Client
from mcp.types import TextContent, TextResourceContents
import asyncio


async def test_tools(client: Client):
    """Test all available tools."""
    print("\n" + "=" * 50)
    print("🔧 TOOLS")
    print("=" * 50)

    # Add sample tasks
    sample_tasks = [
        {"title": "Learn MCP", "description": "Build a task tracker with FastMCP"},
        {"title": "Write tests", "description": "Add unit tests to the project"},
        {"title": "Fix login bug", "description": "Users can't log in with Google"},
        {"title": "Update docs", "description": "Document the new API endpoints"},
        {"title": "Deploy to prod", "description": "Deploy the latest release"},
    ]

    print("\n📝 Adding tasks...")
    for t in sample_tasks:
        result = await client.call_tool("add_task", t)
        assert isinstance(result.content[0], TextContent)
        print(f"  ✅ Added: {t['title']}")

    # Complete a task
    print("\n✔️  Completing task #1...")
    result = await client.call_tool("complete_task", {"task_id": 1})
    assert isinstance(result.content[0], TextContent)
    print(f"  {result.content[0].text}")

    # Filter by status
    print("\n🔍 Filtering pending tasks...")
    result = await client.call_tool("filter_tasks_by_status", {"status": "pending"})
    assert isinstance(result.content[0], TextContent)
    print(f"  {result.content[0].text}")

    # Search by keyword
    print("\n🔎 Searching for 'bug'...")
    result = await client.call_tool("search_tasks", {"keyword": "bug"})
    assert isinstance(result.content[0], TextContent)
    print(f"  {result.content[0].text}")

    # Combined filter
    print("\n🧩 Combined filter (pending + 'docs')...")
    result = await client.call_tool(
        "filter_tasks", {"status": "pending", "keyword": "docs"}
    )
    assert isinstance(result.content[0], TextContent)
    print(f"  {result.content[0].text}")

    # Delete a task
    print("\n🗑️  Deleting task #5...")
    result = await client.call_tool("delete_task", {"task_id": 5})
    assert isinstance(result.content[0], TextContent)
    print(f"  {result.content[0].text}")


async def test_resources(client: Client):
    """Test all available resources."""
    print("\n" + "=" * 50)
    print("📦 RESOURCES")
    print("=" * 50)

    resources = await client.list_resources()
    print(f"\nFound {len(resources)} resources: {[str(r.uri) for r in resources]}")

    for resource in resources:
        print(f"\n--- {resource.uri} ---")
        content = await client.read_resource(resource.uri)
        assert isinstance(content[0], TextResourceContents)
        print(content[0].text)


async def test_prompts(client: Client):
    """Test all available prompts."""
    print("\n" + "=" * 50)
    print("💬 PROMPTS")
    print("=" * 50)

    prompts = await client.list_prompts()
    print(f"\nFound {len(prompts)} prompts: {[p.name for p in prompts]}")

    # Test each prompt and print the generated message
    for prompt in prompts:
        print(f"\n--- {prompt.name} ---")

        # Pass available_hours for scheduling_prompt
        args = {"available_hours": "6"} if prompt.name == "scheduling_prompt" else {}
        result = await client.get_prompt(prompt.name, args)

        for message in result.messages:
            if isinstance(message.content, TextContent):
                # Truncate long prompts for readability
                text = message.content.text
                print(text[:300] + "..." if len(text) > 300 else text)


async def test_server():
    async with Client("test_server.py") as client:
        tools = await client.list_tools()
        print(f"🚀 Connected — {len(tools)} tools available: {[t.name for t in tools]}")

        await test_tools(client)
        await test_resources(client)
        await test_prompts(client)

        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_server())
