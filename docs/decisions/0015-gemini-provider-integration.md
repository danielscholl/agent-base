# ADR 0015: Google Gemini Provider Integration

## Status

Accepted

## Context

The agent-base framework currently supports four LLM providers (OpenAI, Anthropic, Azure OpenAI, and Azure AI Foundry) but lacks support for Google's Gemini models. Users have requested Gemini integration for:

1. Access to Google Cloud Platform infrastructure
2. Gemini-specific features (multimodal capabilities, long context windows)
3. Integration with existing Google Cloud services
4. Flexibility in provider choice and cost optimization

The Microsoft Agent Framework doesn't provide an official `agent-framework-gemini` package, but its `BaseChatClient` interface makes custom provider implementations straightforward.

## Decision

We will implement Google Gemini support through a **custom `GeminiChatClient`** that extends `BaseChatClient` and uses the official `google-genai` Python SDK.

### Implementation Approach

1. **Custom Client Pattern**: Create `GeminiChatClient` extending `BaseChatClient`
2. **Dual Authentication**: Support both API key (Gemini Developer API) and Vertex AI (GCP credentials)
3. **Message Conversion**: Implement bidirectional conversion between agent-framework and Gemini formats
4. **Full Feature Parity**: Support chat completions, streaming, and function calling

### File Structure

```
src/agent/providers/
└── gemini/
    ├── __init__.py          # Public API exports
    ├── chat_client.py       # GeminiChatClient implementation
    └── types.py             # Message conversion utilities
```

## Alternatives Considered

### 1. Use Gemini's OpenAI-Compatible API

**Approach**: Gemini provides OpenAI-compatible endpoints that could reuse `OpenAIChatClient`.

**Pros**:
- Less code to write and maintain
- Immediate compatibility with existing patterns

**Cons**:
- Limited to OpenAI's feature set
- Cannot leverage Gemini-specific capabilities (multimodal, long context)
- Less control over error handling and response processing
- Unclear long-term stability of compatibility layer

**Decision**: Rejected - Custom client provides better control and extensibility.

### 2. Wait for Official agent-framework-gemini Package

**Approach**: Wait for Microsoft to release official Gemini support.

**Pros**:
- Official support and maintenance
- Guaranteed compatibility with framework updates

**Cons**:
- Unknown timeline (may never be released)
- Blocks current user needs
- No guarantee of desired feature set

**Decision**: Rejected - User needs are immediate, custom implementation is feasible.

### 3. Use LangChain Wrapper

**Approach**: Integrate via LangChain's `ChatGoogleGenerativeAI`.

**Pros**:
- Existing abstraction layer
- Community-maintained

**Cons**:
- Adds heavy dependency (LangChain ecosystem)
- Doesn't align with agent-framework patterns
- Unnecessary complexity for our use case

**Decision**: Rejected - Direct SDK integration is cleaner and lighter.

## Consequences

### Positive

1. **Full Feature Access**: Direct SDK usage enables all Gemini capabilities
2. **Dual Authentication**: Users can choose between API key and GCP credentials
3. **Consistent Pattern**: Follows same architecture as OpenAI/Anthropic clients
4. **Extensibility**: Easy to add Gemini-specific features (caching, grounding)
5. **Testability**: Clean dependency injection for mocking and testing

### Negative

1. **Maintenance Burden**: We own the implementation and must track SDK changes
2. **Framework Compatibility**: Must ensure compatibility with agent-framework updates
3. **Testing Complexity**: Requires both unit tests (mocked) and LLM tests (real API)

### Neutral

1. **Package Structure**: Creates `providers/` package for potential future provider additions
2. **Documentation**: Requires ADR, README updates, and usage examples

## Implementation Details

### Authentication Methods

#### Option 1: API Key (Gemini Developer API)
```python
client = GeminiChatClient(
    model_id="gemini-2.0-flash-exp",
    api_key=os.getenv("GEMINI_API_KEY")
)
```

**Use case**: Quick prototyping, development, personal projects

**Limitations**: Lower rate limits, no SLA

#### Option 2: Vertex AI (GCP Credentials)
```python
client = GeminiChatClient(
    model_id="gemini-2.5-pro",
    project_id=os.getenv("GEMINI_PROJECT_ID"),
    location=os.getenv("GEMINI_LOCATION"),
    use_vertexai=True
)
```

**Use case**: Production deployments, enterprise applications

**Benefits**: Higher rate limits, SLA, integration with Google Cloud

### Message Conversion Strategy

We implement three core conversion functions in `types.py`:

1. **`to_gemini_message()`**: ChatMessage → Gemini format
   - Maps roles (user, assistant, system)
   - Converts content types (text, function calls, function results)

2. **`from_gemini_message()`**: Gemini response → ChatMessage
   - Extracts text and function calls from response
   - Handles streaming chunk accumulation

3. **`to_gemini_tools()`**: AIFunction → Gemini function declarations
   - Converts tool definitions to Gemini's schema format
   - Maps parameter types and required fields

### Required Methods

As a `BaseChatClient` subclass, `GeminiChatClient` must implement:

1. **`_inner_get_response()`**: Synchronous chat completion
2. **`_inner_get_streaming_response()`**: Streaming chat completion

Both methods handle:
- Message conversion
- Generation config preparation
- Response processing
- Error handling
- Usage metadata extraction

## Future Considerations

1. **Multimodal Support**: Gemini supports image inputs - consider adding in future
2. **Long Context**: Gemini models support up to 2M tokens - may need special handling
3. **Prompt Caching**: Gemini offers caching for cost optimization
4. **Grounding**: Vertex AI provides Google Search grounding capabilities
5. **Batch Requests**: Consider batch API support for bulk operations
6. **Model Versioning**: Track and handle model version changes (2.0 → 2.5, etc.)

## References

- [Google Gen AI Python SDK](https://ai.google.dev/gemini-api/docs/sdks/python)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/start/quickstarts/api-quickstart)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [ADR 0001: Provider Architecture Pattern](./0001-provider-architecture.md)

## Date

2025-11-10

## Authors

- danielscholl (Implementation)
- Claude (AI Assistant)
