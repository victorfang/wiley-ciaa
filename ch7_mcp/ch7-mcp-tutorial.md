# Chapter 7 — Build the Investigation Agent: RAG, Tools, and MCP

Cryptocurrency Investigation with Agentic AI · Victor Fang · Wiley · 2026

The Model Context Protocol (MCP) is an open standard for connecting an investigation application to an external capability without embedding that capability in the application. This companion chapter introduces the protocol and then traces a complete handshake between an OpenAI language model and a local sanctions server. The server reads a frozen teaching file of OFAC-published addresses. The file is not a current or complete sanctions list. Absence from the sample is not evidence that an address is unsanctioned.

## 1. The Model Context Protocol

Anthropic announced MCP on 25 November 2024. The protocol was created at Anthropic by David Soria Parra and Justin Spahr-Summers. The initial release comprised a specification, software libraries, and example servers for systems including Google Drive, Slack, GitHub, Git, and Postgres. Claude Desktop was the first host with local server support. Subsequent AI applications added MCP clients of their own.

Anthropic analogizes MCP to a USB-C connector: one physical interface serves a display, a storage device, or a phone. Analogously, one protocol serves a sanctions dataset, a blockchain node, or a case archive. The application implements the protocol once. Each external system publishes a server.

Without a shared protocol, five applications that each require three external systems need fifteen custom connectors. With MCP, those three systems publish three servers, and each application connects through the same interface.

MCP messages are JSON-RPC. Three roles participate:

- The **host** is the AI application. It communicates with the language model and controls which results the model may see.
- The **client** resides in the host. The host instantiates one client for each server.
- The **server** exposes the tool or the dataset.

The language model and the server do not exchange messages. The host mediates every step: it discovers the server’s capabilities, presents those capabilities to the model, executes the function the model selects, and returns the result.

A server may advertise three primitive types:

| Primitive | Consumer | This companion |
| --- | --- | --- |
| Tool | The model requests execution through the host | `check_sanctions` |
| Resource | The host loads the data as evidence | `ofac://dprk-crypto-sample` |
| Prompt | The user initiates a reusable review | `screen_crypto_address` |

MCP defines two transports. Both carry `initialize`, `tools/list`, and `tools/call`.

**stdio** is local and one-to-one. The host starts the server as a child process; JSON-RPC travels on stdin and stdout; the child exits with the host. Claude Desktop and this companion use stdio.

**Streamable HTTP** is remote and many-to-one. A process binds a URL, remains running, and accepts multiple hosts. That is the production configuration for a shared sanctions service (Section 3).

This companion uses stdio so a single script can demonstrate the handshake. The protocol sequence is production; the process model is not.

### Direct function call and MCP

A conventional function-calling integration copies `check_sanctions`, a JSON Schema, and a dispatcher into every application. MCP retains the function on the server. The host discovers the advertised name and argument schema, then invokes the tool through the protocol.

```text
Direct API:   host → check_sanctions()
MCP:          host → client → MCP server → check_sanctions()
```

| Concern | Direct API | MCP |
| --- | --- | --- |
| Location of the function | Each application | The server |
| Discovery of arguments | A schema copied into the application | `tools/list` |
| Invocation | `check_sanctions(...)` | `tools/call` |
| Dataset and review wording | Custom in each application | Resource and prompt on the same server |

The match rule does not change. MCP changes ownership of the contract. A second host starts the same server and discovers `check_sanctions` without copying the function.

## 2. Handshake between the OpenAI host and the MCP server

This demonstration shows how an OpenAI model screens a crypto address through MCP without embedding the lookup in the host. The model never opens the sanctions file. The host discovers the server’s tools, the model selects `check_sanctions`, the server evaluates the match, and the model reports the record. The teaching file is a frozen OFAC sample, not a current list. A miss means absence from that sample, not that the address is unsanctioned.

**Files.** All paths are relative to `ch7_mcp/`.

| File | Role |
| --- | --- |
| `mcp_ofac_screening_server.py` | MCP server: match rule and `check_sanctions` |
| `openai_mcp_ofac.py` | Host: starts the server, calls `gpt-6-luna`, runs the tool the model names |
| `ofac-dprk-crypto-sample.json` | Frozen teaching dataset loaded by the server |
| `.env` | `OPENAI_API_KEY` and optional `OPENAI_MODEL` (copy from `.env_example`) |

**Outline.** Four steps follow.

1. Open an MCP session over stdio.
2. Call `tools/list` and hand that catalog to OpenAI.
3. The model selects `check_sanctions`; the host runs `tools/call`.
4. Return the tool JSON; the model writes the answer.

Copy `.env_example` to `.env` and set `OPENAI_API_KEY`. The host loads that file only. `OPENAI_MODEL` defaults to `gpt-6-luna`.

```bash
cd ch7_mcp
python openai_mcp_ofac.py
```

The model never addresses the server. The host is the intermediary.

```text
investigator question
        │
        ▼
openai_mcp_ofac.py  (host)
   │            \
   │ stdio       \  HTTPS
   ▼              ▼
MCP server     OpenAI model
tools/list        gpt-6-luna
tools/call
```

### Step 1. Open a session

The host does not attach to a service that is already running. `stdio_client` starts `mcp_ofac_screening_server.py` as a child process. JSON-RPC travels on stdin and stdout. No TCP port is opened. `initialize` then exchanges protocol versions; the server identifies itself as `OFAC Crypto Screening Demo`. Until that returns, the host must not request tools.

`openai_mcp_ofac.py`, lines 77–82:

```python
params = StdioServerParameters(
    command=sys.executable, args=[str(SERVER)], cwd=str(HERE),
    env={**os.environ, "FASTMCP_LOG_LEVEL": "ERROR"})
async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
```

stdio is specified for a local, one-to-one session. A shared OFAC service uses Streamable HTTP instead. `tools/list` and `tools/call` are the same on both transports.

### Step 2. Discover the tool list and give it to OpenAI

This is the handshake the protocol is for. The host does not import `check_sanctions`. It asks the server what it can do.

`session.list_tools()` is MCP `tools/list`. The server returns every advertised tool: name, description, and JSON Schema for the arguments. This teaching server returns one entry. The host wraps that list in the same statement (`openai_mcp_ofac.py`, line 83):

```python
tools = openai_tools(await session.list_tools())
```

Runtime `tools/list` payload:

```json
[{
  "name": "check_sanctions",
  "description": "Exact-match a crypto address against the local OFAC teaching sample.",
  "inputSchema": {
    "type": "object",
    "required": ["blockchain_id", "address"],
    "properties": {
      "blockchain_id": {"type": "string"},
      "address": {"type": "string"}
    }
  }
}]
```

OpenAI Chat Completions does not accept that MCP object as-is. It expects each tool nested under `type: "function"`. `openai_tools` copies name, description, and schema into that shape (`openai_mcp_ofac.py`, lines 28–33). After the conversion, the model can name `check_sanctions`. Only the server can run it.

```python
def openai_tools(listed):
    """Nest each MCP tool schema in the shape the OpenAI chat API expects."""
    return [{
        "type": "function",
        "function": {"name": tool.name, "description": tool.description or "", "parameters": tool.inputSchema},
    } for tool in listed.tools]
```

A later server might advertise several tools. The host would still call `tools/list` once and hand the full catalog to the model. The model then selects the name that matches the question.

### Step 3. The model selects a tool; the host runs `tools/call`

`answer_with_mcp` sends the investigator’s question with that catalog attached. The system instruction requires screening through `check_sanctions` and treats a negative result as absence from this sample (`openai_mcp_ofac.py`, lines 37–45). `reasoning_effort` is `"none"` because `gpt-6-luna` rejects function tools on `/v1/chat/completions` when reasoning is enabled (`openai_mcp_ofac.py`, lines 48–51):

```python
reply = client.chat.completions.create(
    model=MODEL, messages=messages, tools=tools,
    max_completion_tokens=800, reasoning_effort="none",
).choices[0].message
```

Worked question (`openai_mcp_ofac.py`, line 23):

```text
Does 0x098B716B8Aaf21512996dC57EB0615e2383E2f96 on ethereum-mainnet
appear in this sanctions sample?
```

The first completion is a function call, not a screening result. The model chose `check_sanctions` from the list returned in Step 2.

Runtime tool call:

```json
{"name": "check_sanctions",
 "arguments": {"blockchain_id": "ethereum-mainnet",
               "address": "0x098B716B8Aaf21512996dC57EB0615e2383E2f96"}}
```

The host forwards those arguments. `session.call_tool` is MCP `tools/call`. The server, not the model, evaluates the match (`openai_mcp_ofac.py`, lines 54–57):

```python
call = reply.tool_calls[0]
arguments = json.loads(call.function.arguments)
result = await session.call_tool(call.function.name, arguments)
```

A match requires the same `blockchain_id` and the same address. Ethereum, Arbitrum, and BNB Smart Chain addresses are lowercased; Bitcoin and Tron are not (`mcp_ofac_screening_server.py`, lines 10–26). The tool the server advertised is `check_sanctions` (`mcp_ofac_screening_server.py`, lines 28–38):

```python
@mcp.tool()
def check_sanctions(blockchain_id: str, address: str) -> dict:
    """Exact-match a crypto address against the local OFAC teaching sample."""
    matches = exact_matches(blockchain_id, address)
    return {
        "match": bool(matches),
        "match_count": len(matches),
        "records": matches,
        "dataset": DB["dataset_name"],
        "warning": DB["compliance_warning"],
    }
```

For this address the server returns `match: true`, entity LAZARUS GROUP, program DPRK3, source date 2022-05-06, and `https://ofac.treasury.gov/recent-actions/20220506`.

### Step 4. Return the tool result; the model writes the answer

The Chat Completions API requires the assistant’s tool-call message before the tool result. `tool_call_id` correlates the two. The second request omits `tools`, so the model produces narrative text (`openai_mcp_ofac.py`, lines 60–69):

```python
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
```

The second completion is the host’s printed answer (`old/openai_mcp_ofac.txt`):

```text
Yes. The address appears in the sample:

- Entity: LAZARUS GROUP
- Program: DPRK3
- Source date: 2022-05-06
- Source URL: https://ofac.treasury.gov/recent-actions/20220506

This is a partial sample, not a current or complete sanctions list.
```

A second question, `0x000…0001` on Ethereum (`openai_mcp_ofac.py`, line 24), repeats Steps 3–4. The model again selects `check_sanctions` from the same discovered list. The server returns `match: false`. The second completion is:

```text
0x0000000000000000000000000000000000000001 is absent from this partial sanctions sample.
```

That statement is absence from the teaching file, not a finding that the address is unsanctioned.

A host that cannot predict the number of lookups repeats Step 3 until the completion has no tool call, with a small turn bound. This companion omits that loop because each question names one address.

The resource `ofac://dprk-crypto-sample` (`mcp_ofac_screening_server.py`, lines 40–43) and the prompt `screen_crypto_address` (`mcp_ofac_screening_server.py`, lines 45–53) are advertised on the same server. This OpenAI host uses neither. It discovers tools, then calls `check_sanctions`.

## 3. Demonstration and production

This companion’s stdio child demonstrates the protocol. It is not a deployed sanctions service. Production keeps one process running on Streamable HTTP and gives each host that URL. The host still lists tools and calls `check_sanctions`; it does not spawn the server on every question.

Retain `check_sanctions`. Load the current official list and record its version and update time. Restart the service when the list or the tool definition changes. Hosts continue to discover the tool with `tools/list` and invoke it with `tools/call`. A negative result still means only that the address is absent from the list that was queried.

Restrict access to authenticated hosts. Persist the tool result and an audit record of which principal screened which address. This demonstration prints a sentence to the terminal and accepts any operator who can execute the script.

A production host also iterates the model exchange until the completion contains no tool call. Each completion that still contains a tool call executes `call_tool` and continues. A small turn bound stops a model that never finishes. The bound belongs in the host. This companion omits that loop because each question names one address.
