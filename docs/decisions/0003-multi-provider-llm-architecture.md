---
status: accepted
contact: danielscholl
date: 2025-11-11
deciders: danielscholl
---

# Multi-Provider LLM Architecture Strategy

## Context and Problem Statement

AI application developers need flexibility in choosing LLM providers based on cost, capabilities, availability, compliance requirements, and organizational preferences. Locking into a single provider (e.g., only OpenAI) creates vendor lock-in, limits feature access, increases costs, and reduces resilience. Users have diverse needs: some require cost-free local development, others need enterprise compliance (Azure), some want latest models (Gemini), and many want to optimize costs across providers. How should we architect agent-base to support multiple LLM providers while maintaining code quality, consistent user experience, and manageable complexity?

## Decision Drivers

- **User Flexibility**: Enable provider choice based on cost, features, compliance, and availability
- **Vendor Independence**: Avoid lock-in to any single LLM provider
- **Framework Integration**: Leverage Microsoft Agent Framework's multi-provider support
- **Maintainability**: Minimize code duplication and maintenance burden across providers
- **Consistent UX**: Provide uniform configuration and usage patterns regardless of provider
- **Extensibility**: Make it straightforward to add new providers as they emerge
- **Testing Strategy**: Enable cost-effective testing (free local models, mock clients)
- **Enterprise Readiness**: Support compliance requirements (Azure government clouds, data residency)

## Considered Options

1. **Multi-provider with framework clients** - Support multiple providers using Microsoft Agent Framework packages
2. **OpenAI-only** - Lock to OpenAI API exclusively
3. **Multi-provider with unified abstraction** - Create custom abstraction layer over all providers
4. **Plugin architecture** - Allow third-party provider plugins

## Decision Outcome

Chosen option: **"Multi-provider with framework clients"**, because:

- **Framework Native**: Microsoft Agent Framework provides first-class multi-provider support
- **Proven Packages**: `agent-framework-openai` and `agent-framework-anthropic` are production-ready
- **Minimal Maintenance**: Framework team maintains provider clients, we configure and integrate
- **Consistent Interface**: All framework clients implement `BaseChatClient` interface
- **Easy Extension**: Pattern established for when custom clients are needed (see ADR-0015, ADR-0016)
- **Best Practices**: Framework embeds best practices for each provider (retry logic, error handling)

### Architecture Pattern

**Three provider implementation approaches:**

1. **Framework-Provided Clients** (OpenAI, Anthropic, Azure)
   - Use official `agent-framework-{provider}` packages
   - Zero custom client code needed
   - Example: `OpenAIChatClient`, `AnthropicChatClient`
   - **When to use**: Framework package exists and meets our needs

2. **Custom Client Implementation** (Gemini - see ADR-0015)
   - Extend `BaseChatClient` for providers without framework package
   - Implement message conversion and API integration
   - Example: `GeminiChatClient` using `google-genai` SDK
   - **When to use**: No framework package available, provider has unique features

3. **Client Reuse with Configuration** (Local - see ADR-0016)
   - Reuse existing framework client with different endpoint
   - Example: `OpenAIChatClient` pointed at Docker Model Runner
   - **When to use**: Provider has OpenAI-compatible API

### Configuration Architecture

All providers follow consistent pattern in `AgentConfig`:

```python
@dataclass
class AgentConfig:
    llm_provider: str  # "openai" | "anthropic" | "azure" | "foundry" | "gemini" | "local"

    # Provider-specific fields grouped together
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # ... (similar for other providers)
```

**Validation pattern**: Each provider validates its own required fields in `config.validate()`

**Display pattern**: Consistent `{Provider}/{Model}` format in `get_model_display_name()`

### Provider Selection Decision Tree

```
Does framework package exist?
├─ YES: Use framework client (OpenAI, Anthropic)
└─ NO: Is API OpenAI-compatible?
   ├─ YES: Reuse OpenAIChatClient (Local)
   └─ NO: Custom client needed (Gemini)
```

## Consequences

### Positive

- **User Flexibility**: Developers choose best provider for their needs (cost, features, compliance)
- **Vendor Independence**: Not locked into single provider, can migrate or multi-home
- **Cost Optimization**: Local models for development, cheap APIs for testing, premium for production
- **Framework Leverage**: Benefit from Microsoft's provider client implementations and updates
- **Compliance Support**: Azure providers meet enterprise requirements (government clouds, data residency)
- **Testing Strategy**: Free local models enable extensive testing without API costs
- **Consistent UX**: Same configuration pattern and CLI experience across all providers
- **Future Ready**: Clear pattern for adding new providers as AI landscape evolves

### Neutral

- **Configuration Complexity**: More environment variables across all providers (managed via .env)
- **Documentation Scope**: Need to document 6 providers instead of 1
- **Testing Matrix**: Test suite covers multiple providers with different capabilities
- **Provider Count**: Currently 6 providers, will grow as AI ecosystem expands

### Negative

- **Dependency Footprint**: Requires multiple provider SDKs (openai, anthropic, google-genai, etc.)
- **Capability Variance**: Providers have different feature sets (multimodal, context length, function calling)
- **Error Handling Complexity**: Each provider has unique error types and retry strategies
- **Version Management**: Must track breaking changes across multiple provider SDKs
- **Test Cost**: Real LLM integration tests cost money across multiple paid providers

## Pros and Cons of the Options

### Multi-provider with framework clients

Support multiple providers using Microsoft Agent Framework packages where available.

- Good, because leverages framework's first-class multi-provider support
- Good, because framework team maintains provider clients (retry logic, error handling)
- Good, because consistent `BaseChatClient` interface across all providers
- Good, because enables user flexibility based on cost, features, compliance needs
- Good, because supports cost-effective testing with free local models
- Good, because clear pattern for adding providers (framework, custom, or reuse)
- Neutral, because requires multiple provider SDK dependencies
- Neutral, because providers have capability variance (context length, multimodal, etc.)
- Bad, because must track breaking changes across multiple provider SDKs
- Bad, because increases configuration complexity with provider-specific env vars
- Bad, because LLM integration tests cost money across multiple paid providers

### OpenAI-only

Lock exclusively to OpenAI API, no other providers.

- Good, because minimal configuration (only one set of env vars)
- Good, because single dependency (openai SDK)
- Good, because simplified testing (only one provider to test)
- Neutral, because OpenAI has excellent capabilities and reliability
- Bad, because creates vendor lock-in with no migration path
- Bad, because users cannot optimize costs across providers
- Bad, because excludes users without OpenAI access (students, privacy-conscious)
- Bad, because no compliance options (Azure government clouds, data residency)
- Bad, because cannot leverage provider-specific features (Gemini multimodal, Anthropic long context)
- Bad, because development/testing always costs money (no free local option)

### Multi-provider with unified abstraction

Create custom abstraction layer that unifies all provider differences.

- Good, because could provide completely uniform interface
- Good, because could normalize capability differences
- Neutral, because would hide provider-specific features behind abstractions
- Bad, because reinvents what Agent Framework already provides
- Bad, because massive maintenance burden for our small team
- Bad, because would lag behind provider updates and new features
- Bad, because abstractions leak, providers have fundamental differences
- Bad, because forces lowest-common-denominator feature set

### Plugin architecture

Allow third-party provider plugins loaded at runtime.

- Good, because community could add providers without our involvement
- Good, because very extensible and flexible
- Neutral, because matches plugin patterns in other ecosystems
- Bad, because adds significant architectural complexity (plugin loading, versioning)
- Bad, because security concerns with third-party code execution
- Bad, because would need plugin API stability guarantees
- Bad, because premature - current 6 providers meet user needs
- Bad, because framework doesn't provide plugin infrastructure

## More Information

### Current Supported Providers

| Provider | Type | Implementation | Cost | Use Case |
|----------|------|---------------|------|----------|
| **Local** | Docker Models | OpenAIChatClient reuse | Free | Development, testing, offline |
| **OpenAI** | Cloud API | agent-framework-openai | $$ | Production, latest models |
| **Anthropic** | Cloud API | agent-framework-anthropic | $$ | Production, long context |
| **Gemini** | Cloud API | Custom GeminiChatClient | $$ | Google Cloud, multimodal |
| **Azure OpenAI** | Cloud API | agent-framework-openai | $$ | Enterprise, compliance |
| **Azure AI Foundry** | Cloud API | agent-framework-openai | $$ | Enterprise, managed |

### When to Create ADR for New Provider

**ADR Required** when adding provider involves:
- Architectural decision between multiple viable approaches
- Custom client implementation (see ADR-0015 for Gemini)
- Novel integration pattern (see ADR-0016 for Local)
- Significant tradeoffs to document

**ADR Not Required** when:
- Using existing framework package straightforwardly
- Following established pattern with no decisions needed
- Example: OpenAI and Anthropic were trivial integrations

### Adding a New Provider: Checklist

When adding support for a new LLM provider:

1. **Evaluate approach** (framework client, custom, or reuse)
2. **Create ADR if complex decision** (see decision tree above)
3. **Add configuration fields** to `AgentConfig`
4. **Implement validation** in `config.validate()`
5. **Add client creation** in `Agent._create_chat_client()`
6. **Update display name** in `get_model_display_name()`
7. **Add test fixtures** in `tests/integration/llm/conftest.py`
8. **Write integration tests** in `tests/integration/llm/test_{provider}_integration.py`
9. **Update documentation** (README, docs/design/usage.md, --check command)
10. **Add to provider matrix** above

### Future Considerations

- **Model Router**: Automatically route requests to best provider based on prompt characteristics
- **Fallback Strategy**: Retry with different provider if primary fails
- **Cost Tracking**: Per-provider usage and cost monitoring
- **Rate Limiting**: Unified rate limit handling across providers
- **Prompt Caching**: Provider-specific caching strategies
- **Model Comparison**: Side-by-side testing across providers
- **Provider Health**: Monitor and display provider availability status

### Related ADRs

- **ADR-0015: Gemini Provider Integration** - Documents custom client implementation for Gemini
- **ADR-0016: Local Provider Integration** - Documents Docker Model Runner integration pattern

### References

- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [Agent Framework Multi-Provider Support](https://github.com/microsoft/agent-framework/tree/main/python/packages)
- [BaseChatClient Interface](https://github.com/microsoft/agent-framework/blob/main/python/packages/agent-framework/agent_framework/core/chat_client.py)
