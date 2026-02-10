# End-to-End Testing Guide

This guide covers different approaches for end-to-end testing of the RLM-based schema exploration with real LLMs.

## Option 1: Simulated E2E Test (Easiest)

**What it does**: Simulates intelligent tool selection decisions and measures token usage.

**Pros**:
- No external dependencies
- Fast and deterministic
- Shows optimal RLM behavior

**Run it:**
```bash
uv run python e2e_test_ollama.py
```

**Sample Output:**
```
Scenario 1: Find cancer-related fields
  Tokens used: 3,740
  vs Baseline: 24,424
  Savings: 20,684 (84.7%)
  Steps:
    ✓ search_schema('cancer') → 97 tokens
    ✓ get_type_details('Target') → 3,643 tokens
```

---

## Option 2: Ollama E2E Test (Local LLM)

**What it does**: Uses Ollama (local LLM) to make real tool-calling decisions.

### Prerequisites

1. **Install Ollama**:
   ```bash
   # macOS/Linux
   curl -fsSL https://ollama.ai/install.sh | sh

   # Or download from https://ollama.ai
   ```

2. **Start Ollama**:
   ```bash
   ollama serve
   ```

3. **Pull a model with tool support**:
   ```bash
   # Recommended models for tool calling:
   ollama pull llama3.2
   ollama pull mistral
   ollama pull qwen2.5
   ```

### Run Test

```bash
# Make sure MCP dependencies are installed
uv sync

# Run E2E test
uv run python e2e_test_ollama.py
```

### How It Works

1. Script starts with MCP tools registered
2. Sends user query to Ollama with tool definitions
3. Ollama decides which tools to call
4. Script executes MCP tools
5. Returns results to Ollama
6. Measures total token usage

**Note**: Tool calling support varies by model:
- ✅ llama3.2, mistral, qwen2.5 - Good tool support
- ⚠️ llama2, older models - Limited support

---

## Option 3: MCP Inspector (Visual Testing)

**What it does**: Visual UI for testing MCP tools manually.

### Setup

1. **Install MCP Inspector**:
   ```bash
   npm install -g @anthropic/mcp-inspector
   ```

2. **Start your MCP server**:
   ```bash
   uv run otp-mcp
   ```

3. **Launch Inspector**:
   ```bash
   mcp-inspector
   ```

4. **Connect to server**:
   - URL: `http://localhost:8000/mcp`
   - Or use stdio mode with: `uv run otp-mcp`

### Manual Test Workflow

1. **List available tools** - See all 3 RLM tools + legacy tool
2. **Call `list_schema_types()`** - Observe small response
3. **Call `search_schema("cancer")`** - See targeted results
4. **Call `get_type_details("Target")`** - Get full type info
5. **Compare token usage** vs calling old `get_open_targets_graphql_schema()`

**Visual comparison** makes it easy to see the difference!

---

## Option 4: Claude Desktop Integration

**What it does**: Use Claude (via Claude Desktop) with your MCP server.

### Setup

1. **Edit Claude Desktop config**:
   ```bash
   # macOS
   code ~/Library/Application\ Support/Claude/claude_desktop_config.json

   # Linux
   code ~/.config/Claude/claude_desktop_config.json
   ```

2. **Add your server**:
   ```json
   {
     "mcpServers": {
       "open-targets": {
         "command": "uv",
         "args": [
           "run",
           "--directory",
           "/path/to/open-targets-platform-mcp",
           "otp-mcp"
         ]
       }
     }
   }
   ```

3. **Restart Claude Desktop**

4. **Test in conversation**:
   ```
   User: "Find cancer-related fields in the Open Targets schema"

   Claude will:
   1. See your MCP tools
   2. Choose RLM tools intelligently
   3. Call search_schema("cancer")
   4. Call get_type_details("Target")
   5. Construct GraphQL query
   ```

### Advantages

- **Real conversation**: See how RLM works in practice
- **Smart decisions**: Claude chooses best tool order
- **Token tracking**: Monitor actual usage in Claude UI
- **Production-like**: Tests real-world scenario

---

## Option 5: Integration Test with Python

**What it does**: Programmatic test using MCP Python SDK.

### Create Test Script

```python
# test_e2e_integration.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_rlm_workflow():
    """Test RLM workflow with real MCP server."""

    # Start MCP server
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "otp-mcp"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()

            # List tools
            tools = await session.list_tools()
            print(f"Available tools: {len(tools.tools)}")

            # Call RLM tools in sequence
            result1 = await session.call_tool(
                "search_schema",
                {"pattern": "cancer"}
            )
            print(f"search_schema: {len(str(result1))} chars")

            result2 = await session.call_tool(
                "get_type_details",
                {"type_name": "Target"}
            )
            print(f"get_type_details: {len(str(result2))} chars")

            # Compare with old approach
            result3 = await session.call_tool(
                "get_open_targets_graphql_schema",
                {}
            )
            print(f"full_schema: {len(str(result3))} chars")

if __name__ == "__main__":
    asyncio.run(test_rlm_workflow())
```

### Run

```bash
uv add mcp
uv run python test_e2e_integration.py
```

---

## Comparison Matrix

| Approach | Setup Effort | Realism | Automation | Token Tracking |
|----------|--------------|---------|------------|----------------|
| Simulated | ★☆☆☆☆ | ★★☆☆☆ | ★★★★★ | ★★★★★ |
| Ollama | ★★★☆☆ | ★★★★☆ | ★★★★☆ | ★★★★★ |
| MCP Inspector | ★★☆☆☆ | ★★★☆☆ | ★☆☆☆☆ | ★★★☆☆ |
| Claude Desktop | ★★☆☆☆ | ★★★★★ | ★★☆☆☆ | ★★★★☆ |
| Python SDK | ★★★☆☆ | ★★★☆☆ | ★★★★★ | ★★★★★ |

---

## Recommended Testing Workflow

### For Quick Validation
```bash
# 1. Run simulated test (instant)
uv run python e2e_test_ollama.py

# 2. Visual inspection
mcp-inspector
```

### For Production Validation
```bash
# 1. Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 2. Pull model
ollama pull llama3.2

# 3. Run E2E test
uv run python e2e_test_ollama.py

# 4. Test with Claude Desktop
# (Edit config, restart, test in conversation)
```

### For CI/CD Pipeline
```bash
# Automated testing without LLM
uv run pytest test/test_tools/ -v
uv run python benchmark_rlm.py
uv run python e2e_test_ollama.py  # Uses simulation mode
```

---

## Expected Results

### Token Usage (Typical)

| Test Scenario | Old Approach | RLM Approach | Savings |
|--------------|--------------|--------------|---------|
| "Find cancer fields" | 24,424 | 3,740 | 84.7% |
| "List available types" | 24,424 | 1,162 | 95.2% |
| "Get Target details" | 24,424 | 6,166 | 74.8% |

### Tool Call Patterns

**Smart LLM (Expected)**:
1. search_schema() for targeted discovery
2. get_type_details() for specific types
3. Rarely uses list_schema_types() (only for broad questions)
4. Never uses get_open_targets_graphql_schema() (deprecated)

**Less Smart LLM (Acceptable)**:
1. list_schema_types() first (safe but verbose)
2. get_type_details() after identifying types
3. May occasionally use old schema tool

---

## Troubleshooting

### Ollama Connection Failed
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve
```

### Model Doesn't Support Tools
```bash
# Try different models
ollama pull llama3.2  # Best tool support
ollama pull mistral
ollama pull qwen2.5
```

### MCP Server Won't Start
```bash
# Check dependencies
uv sync

# Test server directly
uv run otp-mcp --help
```

### Token Counts Seem Off
- Make sure tiktoken is installed: `uv add tiktoken`
- Different models use different tokenizers (we use GPT-4 for comparison)
- Token counts are approximate but consistent for comparison

---

## Next Steps

1. **Run simulated test first**: `uv run python e2e_test_ollama.py`
2. **Set up Ollama** if you want real LLM testing
3. **Try MCP Inspector** for visual exploration
4. **Integrate with Claude Desktop** for production-like testing
5. **Add to CI/CD** for continuous validation

The RLM approach is validated! 🎉
