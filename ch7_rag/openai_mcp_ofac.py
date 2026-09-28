## Cryptocurrency Investigation with Agentic AI, Victor Fang, 2026
"""Ask an OpenAI model to screen addresses through the local MCP server.

The model never reads the JSON file. It returns a function call. This host
runs that call on the MCP server and sends the record back.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

HERE = Path(__file__).parent
SERVER = HERE / "mcp_ofac_screening_server.py"
load_dotenv(HERE / ".env")
MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")
QUESTIONS = [
    "Does 0x098B716B8Aaf21512996dC57EB0615e2383E2f96 on ethereum-mainnet appear in this sanctions sample?",
    "Does 0x0000000000000000000000000000000000000001 on ethereum-mainnet appear in this sanctions sample?",
]


def openai_tools(listed):
    """Nest each MCP tool schema in the shape the OpenAI chat API expects."""
    return [{
        "type": "function",
        "function": {"name": tool.name, "description": tool.description or "", "parameters": tool.inputSchema},
    } for tool in listed.tools]


async def answer_with_mcp(session, client, tools, question):
    messages = [{
        "role": "system",
        "content": (
            "Screen addresses only by calling check_sanctions. "
            "When it matches, report the entity, program, source date, and source URL. "
            "When it does not match, say the address is absent from this partial sample. "
            "Do not call an address unsanctioned."
        ),
    }, {"role": "user", "content": question}]
    # One lookup, then the sentence. A general host repeats this until the model
    # stops, and quits after a small turn cap.
    reply = client.chat.completions.create(
        model=MODEL, messages=messages, tools=tools,
        max_completion_tokens=800, reasoning_effort="none",
    ).choices[0].message
    if not reply.tool_calls:
        raise RuntimeError("The first reply did not call the MCP tool.")
    call = reply.tool_calls[0]
    arguments = json.loads(call.function.arguments)
    print(f"  call {call.function.name} {arguments}")
    result = await session.call_tool(call.function.name, arguments)
    if result.isError:
        raise RuntimeError(result.content[0].text)
    messages += [
        {"role": "assistant", "content": reply.content, "tool_calls": [{
            "id": call.id, "type": "function",
            "function": {"name": call.function.name, "arguments": call.function.arguments},
        }]},
        {"role": "tool", "tool_call_id": call.id, "content": result.content[0].text},
    ]
    answer = client.chat.completions.create(
        model=MODEL, messages=messages, max_completion_tokens=800, reasoning_effort="none",
    ).choices[0].message
    return answer.content or ""


async def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Copy .env_example to .env in this folder and set OPENAI_API_KEY.")
    print(f"Using {MODEL}. The lookup runs on the local MCP server.")
    params = StdioServerParameters(
        command=sys.executable, args=[str(SERVER)], cwd=str(HERE),
        env={**os.environ, "FASTMCP_LOG_LEVEL": "ERROR"})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = openai_tools(await session.list_tools())
            print("Discovered", ", ".join(tool["function"]["name"] for tool in tools))
            client = OpenAI()
            for question in QUESTIONS:
                print(f"\nQ {question}")
                print(await answer_with_mcp(session, client, tools, question))


if __name__ == "__main__":
    asyncio.run(main())
