---
status: accepted
contact: danielscholl
date: 2025-11-10
deciders: danielscholl
---

# Google Gemini Provider Integration

> **Note**: This ADR documents a specific complex provider implementation decision. See [ADR-0003: Multi-Provider LLM Architecture Strategy](./0003-multi-provider-llm-architecture.md) for the overall provider strategy and when custom clients are appropriate.

## Context and Problem Statement

The agent-base framework currently supports four LLM providers (OpenAI, Anthropic, Azure OpenAI, and Azure AI Foundry) but lacks support for Google's Gemini models. Users need Gemini integration for access to Google Cloud Platform infrastructure, Gemini-specific features (multimodal capabilities, long context windows), integration with existing Google Cloud services, and flexibility in provider choice for cost optimization. The Microsoft Agent Framework doesn't provide an official `agent-framework-gemini` package. How should we implement Google Gemini support while maintaining consistency with existing provider patterns?

## Decision Drivers

- **Framework Compatibility**: Must integrate cleanly with Microsoft Agent Framework's BaseChatClient interface
- **Feature Parity**: Support chat completions, streaming, and function calling like other providers
- **Authentication Flexibility**: Support both API key (Developer API) and GCP credentials (Vertex AI)
- **Maintenance Burden**: Balance functionality against long-term maintenance costs
- **User Experience**: Provide consistent configuration and usage patterns across all providers
- **Extensibility**: Enable future Gemini-specific features (caching, multimodal, grounding)

## Considered Options

1. **Custom GeminiChatClient** - Implement custom client extending BaseChatClient with google-genai SDK
2. **Use Gemini's OpenAI-Compatible API** - Reuse OpenAIChatClient with Gemini compatibility endpoint
3. **Wait for Official agent-framework-gemini Package** - Delay until Microsoft releases official support
4. **Use LangChain Wrapper** - Integrate via LangChain's ChatGoogleGenerativeAI

## Decision Outcome

Chosen option: **"Custom GeminiChatClient extending BaseChatClient"**, because:

- **Full Feature Access**: Direct SDK usage enables all Gemini capabilities including future features
- **Dual Authentication**: Users can choose between API key (prototyping) and GCP credentials (production)
- **Framework Native**: Follows same BaseChatClient pattern as OpenAI/Anthropic implementations
- **Clean Dependencies**: Only adds google-genai SDK, no heavy frameworks like LangChain
- **Proven Pattern**: Matches existing provider architecture successfully used for other providers
- **Extensibility**: Easy to add Gemini-specific features (prompt caching, grounding) later

### Implementation Architecture

```
src/agent/providers/
└── gemini/
    ├── __init__.py          # Public API exports
    ├── chat_client.py       # GeminiChatClient extending BaseChatClient
    └── types.py             # Message conversion utilities
```

**Message Conversion Strategy:**
1. `to_gemini_message()`: ChatMessage → Gemini format (maps roles, content types, function calls)
2. `from_gemini_message()`: Gemini response → ChatMessage (extracts text and function calls)
3. `to_gemini_tools()`: AIFunction → Gemini function declarations (converts schemas)

**Required Methods:**
- `_inner_get_response()`: Synchronous chat completion
- `_inner_get_streaming_response()`: Streaming chat completion with chunk accumulation

## Consequences

### Positive

- **Full Gemini API Access**: Can leverage all Gemini capabilities including multimodal and long context
- **Dual Authentication Options**: API key for development, Vertex AI for production with SLA
- **Consistent Provider Pattern**: Same architecture as OpenAI/Anthropic for maintainability
- **Future Ready**: Easy to add Gemini-specific features like prompt caching and grounding
- **Well Isolated**: Clean dependency injection enables mocking and comprehensive testing
- **No Heavy Dependencies**: Direct SDK usage avoids unnecessary abstraction layers

### Neutral

- **New Package Structure**: Creates `providers/` directory for potential future custom providers
- **Testing Scope**: Requires both unit tests (mocked SDK) and LLM integration tests (real API)
- **Configuration Fields**: Adds 5 new environment variables (API key, project, location, model, use_vertexai)

### Negative

- **Maintenance Ownership**: Team owns implementation and must track google-genai SDK changes
- **Framework Compatibility Risk**: Must ensure compatibility with Agent Framework updates
- **Documentation Burden**: Requires README updates, usage examples, and this ADR

## Pros and Cons of the Options

### Custom GeminiChatClient

Direct implementation using google-genai SDK.

- Good, because provides full access to Gemini-specific features (multimodal, long context, caching)
- Good, because supports both API key (Developer API) and Vertex AI (GCP credentials) authentication
- Good, because follows proven BaseChatClient pattern used by other providers
- Good, because enables future extensibility for Gemini-specific capabilities
- Neutral, because creates new `providers/` package structure for custom implementations
- Bad, because team owns maintenance and must track SDK breaking changes
- Bad, because requires comprehensive test coverage for message conversion logic

### Use Gemini's OpenAI-Compatible API

Reuse OpenAIChatClient with Gemini compatibility endpoint.

- Good, because minimal code changes and immediate compatibility
- Good, because leverages existing well-tested OpenAI client code
- Neutral, because Gemini compatibility layer may have unknown long-term stability
- Bad, because limited to OpenAI's feature set, cannot access Gemini-specific capabilities
- Bad, because less control over error handling and response processing
- Bad, because cannot leverage multimodal inputs or 2M token context windows

### Wait for Official agent-framework-gemini Package

Delay implementation until Microsoft releases official package.

- Good, because would provide official support and guaranteed framework compatibility
- Good, because Microsoft would handle maintenance and SDK updates
- Neutral, because release timeline is completely unknown (may never happen)
- Bad, because blocks current user needs and requests
- Bad, because no guarantee Microsoft's implementation would meet our requirements
- Bad, because users cannot access Gemini today despite clear demand

### Use LangChain Wrapper

Integrate via LangChain's ChatGoogleGenerativeAI.

- Good, because provides existing abstraction layer maintained by community
- Good, because LangChain has wide adoption and active development
- Neutral, because adds LangChain ecosystem as heavy dependency
- Bad, because doesn't align with Agent Framework patterns and architecture
- Bad, because introduces unnecessary complexity for our simple use case
- Bad, because larger dependency footprint for limited benefit

## More Information

**Authentication Methods:**

API Key (Gemini Developer API):
```python
client = GeminiChatClient(
    model_id="gemini-2.0-flash-exp",
    api_key=os.getenv("GEMINI_API_KEY")
)
```
- Use case: Quick prototyping, development, personal projects
- Limitations: Lower rate limits, no SLA

Vertex AI (GCP Credentials):
```python
client = GeminiChatClient(
    model_id="gemini-2.5-pro",
    project_id=os.getenv("GEMINI_PROJECT_ID"),
    location=os.getenv("GEMINI_LOCATION"),
    use_vertexai=True
)
```
- Use case: Production deployments, enterprise applications
- Benefits: Higher rate limits, SLA, Google Cloud integration

**Future Considerations:**
- Multimodal support (image inputs)
- Long context handling (up to 2M tokens)
- Prompt caching for cost optimization
- Grounding with Google Search (Vertex AI)
- Batch requests for bulk operations
- Model version tracking (2.0 → 2.5, etc.)

**References:**
- [Google Gen AI Python SDK](https://ai.google.dev/gemini-api/docs/sdks/python)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/start/quickstarts/api-quickstart)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
