# ADR 0016: Local Provider Integration with Docker Models

## Status

Accepted

## Context

The agent-base framework currently supports five cloud-based LLM providers (OpenAI, Anthropic, Azure OpenAI, Azure AI Foundry, and Google Gemini), but all require internet connectivity and API keys. Users have requested local model support for:

1. **Cost-free development**: Cloud API calls incur charges, making extensive testing expensive
2. **Offline operation**: Ability to work without internet connectivity or cloud service availability
3. **Data privacy**: All prompts and responses stay on local machine, no third-party data sharing
4. **Fast iteration**: Eliminate network latency for rapid development cycles
5. **Educational use**: Students and learners need free access without credit card requirements

Docker Desktop now provides built-in model serving with OpenAI-compatible API endpoints, enabling local execution of models like phi4, llama3.2, and mistral. However, agent-base lacks a provider configuration to utilize these local endpoints.

## Decision

We will implement a **"local" provider** that leverages Docker Desktop's model serving capability by **reusing the existing `OpenAIChatClient`** with a custom `base_url` pointing to the local Docker endpoint.

### Implementation Approach

1. **Reuse OpenAI Client**: Docker Model Runner exposes OpenAI-compatible API, so we use `OpenAIChatClient` directly
2. **Configuration Fields**: Add `local_base_url` and `local_model` to `AgentConfig`
3. **Default Endpoint**: Use `http://localhost:12434/engines/llama.cpp/v1` as default (DMR standard endpoint)
4. **No Authentication**: Docker Model Runner doesn't require API keys for local access, use placeholder value
5. **Model Flexibility**: Support any model pulled via `docker model pull` command

### Architecture

```python
# Configuration
config = AgentConfig(
    llm_provider="local",
    local_base_url="http://localhost:12434/engines/llama.cpp/v1",  # DMR endpoint
    local_model="ai/phi4",
)

# Client Creation (in Agent._create_chat_client)
elif self.config.llm_provider == "local":
    from agent_framework.openai import OpenAIChatClient

    return OpenAIChatClient(
        model_id=self.config.local_model,
        base_url=self.config.local_base_url,
        api_key="not-needed",  # Docker doesn't authenticate
    )
```

## Alternatives Considered

### 1. Ollama Integration

**Approach**: Integrate with Ollama's model serving platform.

**Pros**:
- Popular open-source solution
- Large model library
- Active community

**Cons**:
- Separate installation required (not built into Docker Desktop)
- Different API format (not OpenAI-compatible out of box)
- Requires custom client implementation similar to Gemini
- Less standardized than Docker's approach

**Decision**: Rejected - Docker Desktop is more widely installed, provides OpenAI-compatible API.

### 2. LM Studio Integration

**Approach**: Support LM Studio's local model serving.

**Pros**:
- User-friendly GUI for model management
- Good model performance

**Cons**:
- Less standardized API
- GUI-focused (less suitable for headless/CI environments)
- Additional software installation
- Smaller user base than Docker

**Decision**: Rejected - Docker Desktop integration is cleaner and more accessible.

### 3. Custom Local Provider Client

**Approach**: Create dedicated `LocalChatClient` similar to `GeminiChatClient`.

**Pros**:
- More explicit provider naming
- Could add local-specific features later

**Cons**:
- Unnecessary code duplication
- Docker models are already OpenAI-compatible
- More maintenance burden
- No immediate benefit over reusing OpenAI client

**Decision**: Rejected - Reusing OpenAI client minimizes complexity and maintenance.

### 4. No Local Support

**Approach**: Continue requiring cloud providers only.

**Pros**:
- No code changes needed
- Fewer providers to maintain

**Cons**:
- Excludes users without cloud API access
- Increases development costs for all users
- Misses Docker Desktop's built-in capability
- Reduces framework accessibility

**Decision**: Rejected - User need is clear and implementation is straightforward.

## Consequences

### Positive

1. **Minimal Code Changes**: Reuses proven `OpenAIChatClient`, only adds configuration
2. **Zero New Dependencies**: No new Python packages required
3. **Cost-Free Operation**: Completely free to run after model download
4. **Docker Ecosystem**: Leverages widely-installed Docker Desktop
5. **OpenAI Compatibility**: Any OpenAI-compatible local server works (not just Docker)
6. **Easy Testing**: Developers can test without burning through API credits
7. **Offline Capability**: Full functionality without internet connection

### Negative

1. **Docker Dependency**: Requires Docker Desktop installation (not available on all systems)
2. **Model Quality**: Local models (phi4, llama3.2) are capable but not GPT-4 level
3. **Resource Requirements**: Models need significant RAM (8GB+ recommended)
4. **Function Calling Variance**: Tool support depends on specific model capabilities
5. **Download Sizes**: Models are large (~5GB+), slow initial setup
6. **Limited Documentation**: Docker model serving is relatively new feature

### Neutral

1. **Provider Count**: Increases provider count from 5 to 6
2. **Configuration Complexity**: Adds two more environment variables
3. **Testing Scope**: Requires new integration tests marked `@pytest.mark.requires_local`

## Implementation Details

### Configuration

```python
# AgentConfig dataclass fields
local_base_url: str | None = None
local_model: str = "ai/phi4"  # Default model
```

### Environment Variables

```bash
LLM_PROVIDER=local
LOCAL_BASE_URL=http://localhost:12434/engines/llama.cpp/v1  # Optional, has default
AGENT_MODEL=ai/phi4  # Optional, overrides default
```

### Validation

```python
elif self.llm_provider == "local":
    if not self.local_base_url:
        raise ValueError(
            "Local provider requires base URL. Set LOCAL_BASE_URL environment variable "
            "(e.g., http://localhost:12434/engines/llama.cpp/v1). Ensure Docker Desktop is running "
            "with Model Runner enabled and model is pulled (e.g., docker model pull phi4)."
        )
```

### Display Name

```python
elif self.llm_provider == "local":
    return f"Local/{self.local_model}"  # e.g., "Local/phi4"
```

### Recommended Models

1. **phi4** (default) - Microsoft's phi-4 (7B parameters)
   - Excellent instruction following
   - Good reasoning capabilities
   - Supports function calling
   - Fast inference on consumer hardware

2. **llama3.2** - Meta's Llama 3.2
   - Very capable general-purpose model
   - Strong reasoning
   - Good multilingual support

3. **mistral** - Mistral AI
   - Strong multilingual capabilities
   - Good code understanding
   - Efficient inference

4. **codellama** - Meta's Code Llama
   - Optimized for code tasks
   - Good for development assistance
   - Code-specific training

## Future Considerations

1. **Model Health Check**: Ping endpoint on startup, provide helpful error if Docker not running
2. **Multi-Model Support**: Allow switching models mid-session without restart
3. **Model Management UI**: CLI commands to list, pull, remove models via `docker model` commands
4. **Performance Metrics**: Track local vs cloud latency and token throughput
5. **Ollama Support**: Add similar integration for Ollama if user demand exists
6. **Model Download Progress**: Show progress during `docker model pull` operations
7. **Memory Optimization**: Guidance on Docker Desktop resource allocation for optimal performance
8. **Model Caching**: Best practices for managing multiple downloaded models
9. **GPU Acceleration**: Documentation for users with NVIDIA GPUs

## Testing Strategy

### Unit Tests

- Configuration loading from environment variables
- Validation logic (requires `base_url`, no API key needed)
- Display name generation
- Model override via `AGENT_MODEL`

### Integration Tests

- Basic chat completion with local model
- Streaming responses
- Function calling (if model supports it)
- Multi-turn conversation state
- Marked with `@pytest.mark.requires_local` to skip when Docker not available

### Manual Testing

```bash
# Setup
docker desktop enable model-runner --tcp 12434
docker model pull phi4
export LLM_PROVIDER=local
export LOCAL_MODEL=phi4

# Test configuration
agent --check

# Test chat
agent -p "Say hello in one sentence"

# Test interactive session
agent
```

## References

- [Docker Desktop Model Serving](https://docs.docker.com/desktop/features/models/)
- [OpenAI API Compatibility](https://platform.openai.com/docs/api-reference)
- [Microsoft phi-4 Model](https://huggingface.co/microsoft/phi-4)
- [Agent Framework OpenAI Client](https://github.com/microsoft/agent-framework)

## Date

2025-11-10

## Authors

- danielscholl (Implementation)
- Claude (AI Assistant)
