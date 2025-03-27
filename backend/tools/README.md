# MCP Servers Guide

This guide outlines the steps for setting up and using Model Context Protocol (MCP) servers, which allow external models to be used within Introspect. This feature is currently not integrated into the application.

## 1. Set Up Your MCP Servers
Set up your MCP servers by following the official [SDKs](https://github.com/modelcontextprotocol).
If you're hosting them outside of this application, ensure that your servers operate with [SSE transport](https://modelcontextprotocol.io/docs/concepts/transports#server-sent-events-sse).

```python
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP with an available port
mcp = FastMCP(
  name="name_of_remote_server",
  port=3001,
)

# Add your tools and prompts
# @mcp.tool()
# async def example_tool():
#     ...

# Start the server with SSE transport
if __name__ == "__main__":
    mcp.run(transport="sse")
```

## 2. Configure mcp_config.json

After your servers are running, configure `mcp_config.json` to connect to them:

```json
{
    "mcpServers": {
        "name_of_remote_server": {
            "command": "sse", 
            "args": ["http://host.docker.internal:3001"]
        },
        "name_of_local_server": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/package-name"]
        }
    }
}
```

### Configuration Options:

1. **Remote Servers (SSE):**
   - Use `"command": "sse"` 
   - Use `"args": ["url_to_server"]` for remote servers
   - Use `"args": ["http://host.docker.internal:PORT/sse"]` for servers running on your local machine
   - Make sure the port matches your server's configuration

2. **Local Servers in this Docker (stdio):**
   - Specify the command to run the server (e.g., `"npx"`, `"python"`)
   - Provide arguments in an array (e.g., `["-y", "package-name"]`)
   - Optionally provide environment variables with `"env": {}`

## 3. Using MCPClient

Once your servers are configured, use the `MCPClient` class to interact with them:

### Step 1: Initialize and Connect

```python
from utils_mcp import MCPClient
import json

# Load config
with open("path/to/mcp_config.json", "r") as f:
    config = json.load(f)

# Initialize client with your preferred model. Only Claude and OpenAI models are supported.
mcp_client = MCPClient(model_name="claude-3-7-sonnet-20250219")

# Connect to all servers defined in config
await mcp_client.connect_to_server_from_config(config)
```

### Step 2: Process Queries

```python
# Send a query to be processed by the LLM with access to MCP tools
# The response contains the final text output
# tool_outputs is a list of all tool calls made during processing
response, tool_outputs = await mcp_client.mcp_chat(query="What is the average sale in the northeast region?")
```

### Step 3: Clean Up

```python
# Always clean up when done to close connections
await mcp_client.cleanup()
```

## 4. Using Prompt Templates

Prompt templates that are defined in the MCP servers can be invoked in queries using the `/command` syntax:

```python
# This will apply the "gen_report" prompt template to "sales by region"
response, _ = await mcp_client.mcp_chat(query="/gen_report sales by region")
```
If no further text is provided after the command, the prompt template will be applied to the output of the previous message in the message history.

## 5. Troubleshooting

If you encounter the "unhandled errors in a TaskGroup" error:

1. **Check Server Status**: Make sure your server is running on the specified port
2. **Verify Configuration**: Ensure port numbers match in both server and config
3. **Host Binding**: Server must use `host="0.0.0.0"` (not `127.0.0.1`)
4. **Network Access**: For Docker, ensure host.docker.internal resolves correctly
5. **Port Exposure**: Make sure the port is accessible from the Docker container

If using stdio servers, check for syntax errors in your command or arguments.

## 6. MCPClient Reference

Key methods in `MCPClient`:

- `connect_to_server_from_config(config)`: Connect to all servers in config json file
- `mcp_chat(query)`: Process a query using LLM and available tools
  - Calls tools in a loop until no more tools are called or max tokens are reached
  - Stores messages in message history so the LLM can use it as context for following queries
- `call_tool(tool_name, tool_args)`: Directly call a specific tool
- `get_prompt(prompt_name, args)`: Retrieve a specific prompt template
- `cleanup()`: Close all server connections