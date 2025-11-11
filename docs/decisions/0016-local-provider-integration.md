---
status: accepted
contact: danielscholl
date: 2025-11-10
deciders: danielscholl
---

# Local Provider Integration with Docker Models

> **Note**: This ADR documents a specific complex provider implementation decision. See [ADR-0003: Multi-Provider LLM Architecture Strategy](./0003-multi-provider-llm-architecture.md) for the overall provider strategy and when client reuse is appropriate.

## Context and Problem Statement

The agent-base framework currently supports five cloud-based LLM providers (OpenAI, Anthropic, Azure OpenAI, Azure AI Foundry, and Google Gemini), but all require internet connectivity, API keys, and incur usage costs. Users need local model support for cost-free development, offline operation, data privacy (all data stays local), fast iteration without network latency, and educational use without credit card requirements. Docker Desktop now provides built-in model serving with OpenAI-compatible API endpoints, enabling local execution of models like phi4, qwen3, and llama3.2. How should we implement local model support while minimizing complexity and maintenance burden?

## Decision Drivers

- **Cost Efficiency**: Enable free local development without API charges
- **Simplicity**: Minimize code changes and dependencies
- **Compatibility**: Leverage existing OpenAI-compatible standards
- **Offline Capability**: Work without internet connectivity
- **Ease of Setup**: Use widely-installed Docker Desktop, not additional software
- **Maintenance Burden**: Avoid creating new client implementations if possible
- **Testing Support**: Enable free LLM testing without API costs

## Considered Options

1. **Reuse OpenAIChatClient with Docker endpoint** - Point existing OpenAI client to local Docker URL
2. **Ollama Integration** - Integrate with Ollama's model serving platform
3. **LM Studio Integration** - Support LM Studio's local model serving
4. **Custom LocalChatClient** - Create dedicated client similar to GeminiChatClient

## Decision Outcome

Chosen option: **"Reuse OpenAIChatClient with Docker endpoint"**, because:

- **Zero New Code**: Docker Model Runner exposes OpenAI-compatible API, direct reuse of existing client
- **Minimal Configuration**: Only adds two config fields (`local_base_url`, `local_model`)
- **No New Dependencies**: No additional Python packages required beyond what we already have
- **Docker Ecosystem**: Leverages widely-installed Docker Desktop (70M+ users)
- **OpenAI Compatibility**: Works with any OpenAI-compatible local server, not just Docker
- **Proven Pattern**: OpenAIChatClient already battle-tested with cloud OpenAI
- **Simple Maintenance**: No custom client code to maintain for local provider

### Implementation Pattern

```python
# Configuration
config = AgentConfig(
    llm_provider="local",
    local_base_url="http://localhost:12434/engines/llama.cpp/v1",
    local_model="ai/phi4",
)

# Client creation (in Agent._create_chat_client)
elif self.config.llm_provider == "local":
    from agent_framework.openai import OpenAIChatClient

    return OpenAIChatClient(
        model_id=self.config.local_model,
        base_url=self.config.local_base_url,
        api_key="not-needed",  # Docker doesn't authenticate locally
    )
```

**No custom provider code needed** - just configuration and client instantiation.

## Consequences

### Positive

- **Completely Free**: Zero API costs after initial model download
- **Minimal Code Changes**: Only configuration additions, no new client implementation
- **Zero New Dependencies**: No new Python packages required
- **Offline Capability**: Full functionality without internet connection
- **Docker Ecosystem**: Uses widely-installed Docker Desktop
- **Fast Testing**: Developers can iterate without burning API credits
- **Data Privacy**: All prompts and responses stay on local machine
- **OpenAI Standard**: Any OpenAI-compatible server works (Ollama, LM Studio with compat mode)

### Neutral

- **Provider Count**: Increases total providers from 5 to 6
- **Configuration Scope**: Adds 2 environment variables (`LOCAL_BASE_URL`, `AGENT_MODEL`)
- **Testing Markers**: Requires `@pytest.mark.requires_local` for LLM tests using local models

### Negative

- **Docker Dependency**: Requires Docker Desktop installation (not available on all systems)
- **Model Quality Gap**: Local models (phi4, llama3.2) capable but not GPT-4o level
- **Resource Requirements**: Models need significant RAM (8GB+ recommended for good performance)
- **Function Calling Variance**: Tool support quality depends on specific model capabilities
- **Large Downloads**: Model files are 5GB+, slow first-time setup
- **Limited Documentation**: Docker model serving is relatively new feature with sparse docs

## Pros and Cons of the Options

### Reuse OpenAIChatClient with Docker endpoint

Point existing OpenAI client to local Docker Model Runner.

- Good, because requires zero new client implementation code
- Good, because no new Python dependencies to manage
- Good, because Docker Desktop widely installed (70M+ users)
- Good, because Docker provides OpenAI-compatible API out of box
- Good, because works with any OpenAI-compatible local server (Ollama, LM Studio)
- Good, because proven OpenAIChatClient already battle-tested
- Neutral, because adds Docker as system dependency
- Bad, because Docker Model Runner documentation still limited
- Bad, because local models not as capable as cloud GPT-4o/Claude

### Ollama Integration

Integrate with Ollama's model serving platform.

- Good, because popular open-source solution with active community
- Good, because large model library with easy management
- Neutral, because requires separate Ollama installation (not built into Docker)
- Bad, because Ollama's API not natively OpenAI-compatible (needs custom client)
- Bad, because requires custom client implementation similar to GeminiChatClient
- Bad, because less standardized than Docker's approach
- Bad, because another system dependency to install and manage

### LM Studio Integration

Support LM Studio's local model serving.

- Good, because provides user-friendly GUI for model management
- Good, because good model performance and optimization
- Neutral, because GUI-focused (less suitable for headless/CI environments)
- Bad, because less standardized API requires custom implementation
- Bad, because additional software installation needed
- Bad, because smaller user base compared to Docker Desktop
- Bad, because primarily desktop application, not infrastructure tool

### Custom LocalChatClient

Create dedicated local client implementation extending BaseChatClient.

- Good, because more explicit provider naming and separation
- Good, because could add local-specific features later (model switching, management)
- Neutral, because follows same pattern as GeminiChatClient
- Bad, because unnecessary code duplication of OpenAIChatClient
- Bad, because Docker models already OpenAI-compatible, no value add
- Bad, because creates maintenance burden for identical functionality
- Bad, because no immediate benefit over reusing existing proven client

## More Information

**Setup Instructions:**

```bash
# 1. Enable Docker Model Runner
docker desktop enable model-runner --tcp=12434

# 2. Pull a model (qwen3 recommended for best tool calling)
docker model pull ai/qwen3

# 3. Verify model availability
curl http://localhost:12434/engines/llama.cpp/v1/models

# 4. Configure agent-base
export LLM_PROVIDER=local
export AGENT_MODEL=ai/qwen3

# 5. Run agent
agent --check  # Verify setup
agent          # Start interactive session
```

**Recommended Models (in priority order):**

1. **ai/qwen3** (RECOMMENDED) - Best tool-calling accuracy among local models
   - Excellent function calling support
   - 8B/14B parameter variants available
   - [Docker evaluation shows best tool-calling results](https://www.docker.com/blog/local-llm-tool-calling-a-practical-evaluation/)

2. **ai/phi4** - Microsoft's phi-4 (14B parameters)
   - Good general-purpose capabilities
   - Solid instruction following
   - Decent function calling support

3. **ai/llama3.2** - Meta's Llama 3.2
   - Strong reasoning abilities
   - Good multilingual support
   - Larger context window

4. **ai/mistral** - Mistral AI
   - Excellent multilingual capabilities
   - Good code understanding
   - Efficient inference

**Environment Variables:**

```bash
LLM_PROVIDER=local
LOCAL_BASE_URL=http://localhost:12434/engines/llama.cpp/v1  # Optional, has default
AGENT_MODEL=ai/qwen3  # Overrides default model
```

**Future Considerations:**
- Model health check on startup with helpful error messages
- Multi-model support (switch models mid-session)
- CLI commands for model management (list, pull, remove via `docker model`)
- Performance metrics tracking (local vs cloud latency comparison)
- Ollama support if user demand justifies custom client complexity
- Model download progress indicators
- Memory optimization guidance for Docker Desktop resource allocation
- GPU acceleration documentation for users with NVIDIA GPUs

**References:**
- [Docker Desktop Model Serving](https://docs.docker.com/desktop/features/models/)
- [Docker Tool Calling Evaluation](https://www.docker.com/blog/local-llm-tool-calling-a-practical-evaluation/)
- [OpenAI API Compatibility](https://platform.openai.com/docs/api-reference)
- [Microsoft phi-4 Model](https://huggingface.co/microsoft/phi-4)
