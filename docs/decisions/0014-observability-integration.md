---
status: accepted
contact: danielscholl
date: 2025-11-10
deciders: danielscholl
---

# Observability Integration with OpenTelemetry

## Context and Problem Statement

Agent Base needs comprehensive observability to monitor agent performance, track token usage, debug issues, and gain insights into agent behavior in production environments. Without proper instrumentation, it's difficult to:

- Monitor agent performance and response times in production
- Track token usage and costs across conversations
- Debug issues and understand agent behavior
- Analyze tool execution patterns and failures
- Gain insights into LLM provider interactions

How can we implement production-grade observability that is standards-compliant, vendor-neutral, and non-intrusive?

## Decision Drivers

- **Standards Compliance**: Use OpenTelemetry (CNCF standard) for vendor-neutral telemetry
- **Microsoft Alignment**: Follow Microsoft Agent Framework patterns and best practices
- **Non-Intrusive Design**: Observability must be optional with zero overhead when disabled
- **Multiple Backends**: Support Azure Application Insights, OTLP endpoints, and console output
- **GenAI Conventions**: Follow OpenTelemetry semantic conventions for GenAI applications
- **Security First**: Sensitive data (prompts/responses) only in dev environments, default disabled
- **Minimal Dependencies**: Leverage existing agent-framework transitive dependencies
- **Developer Experience**: Easy to setup and use with clear documentation

## Considered Options

1. **Custom Telemetry System** - Build proprietary telemetry from scratch
2. **Azure Application Insights Only** - Use Azure-specific SDK exclusively
3. **OpenTelemetry with Microsoft Patterns** - Standards-based approach following Microsoft Agent Framework
4. **Prometheus/Grafana Stack** - Focus on metrics-only observability
5. **Logging-Based Observability** - Rely solely on structured logging

## Decision Outcome

Chosen option: **"OpenTelemetry with Microsoft Patterns"**, because:

- **Standards-Based**: OpenTelemetry is CNCF graduated project, industry standard
- **Vendor-Neutral**: Works with Application Insights, Jaeger, Prometheus, Aspire Dashboard, etc.
- **Framework Alignment**: Follows Microsoft Agent Framework's observability patterns
- **Comprehensive**: Supports traces, metrics, and logs in single solution
- **Future-Proof**: OpenTelemetry is actively developed with strong ecosystem
- **Cost-Effective**: Leverages existing dependencies from agent-framework package

### Implementation Details

**Architecture:**

1. **Observability Module** (`src/agent/observability.py`):
   - `ObservabilitySettings`: Pydantic settings class for configuration
   - `setup_observability()`: Main setup function with singleton pattern
   - `get_tracer()` / `get_meter()`: Helper functions for accessing telemetry APIs
   - `OtelAttr`: Enum with GenAI semantic convention attributes
   - `capture_exception()`: Helper for error tracking

2. **Configuration Integration** (`src/agent/config.py`):
   - Added observability fields to `AgentConfig`
   - Environment variable loading for OTEL settings
   - Backward compatible (observability disabled by default)

3. **Middleware Instrumentation** (`src/agent/middleware.py`):
   - Enhanced `agent_observability_middleware` with OpenTelemetry spans
   - Enhanced `logging_function_middleware` with tool execution spans
   - Conditional instrumentation (only when `enable_otel=True`)
   - Metrics for duration and token usage

4. **Exporter Support**:
   - **OTLP**: For Aspire Dashboard, Jaeger, Prometheus, etc.
   - **Azure Monitor**: For Application Insights
   - **Console**: For development and debugging
   - Multiple exporters simultaneously

**Configuration:**

```python
# Environment variables
ENABLE_OTEL=true                                    # Enable observability
ENABLE_SENSITIVE_DATA=false                         # Capture prompts/responses (dev only!)
OTLP_ENDPOINT=http://localhost:4317                 # OTLP endpoint
APPLICATIONINSIGHTS_CONNECTION_STRING=xxx           # Azure App Insights

# Code setup
from agent.observability import setup_observability

setup_observability(
    otlp_endpoint="http://localhost:4317",
    appinsights_connection_string="InstrumentationKey=xxx"
)
```

**Telemetry Attributes (GenAI Semantic Conventions):**

- Operation: `gen_ai.operation.name`, `gen_ai.system`
- Model: `gen_ai.request.model`, `gen_ai.response.model`
- Tokens: `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`
- Agent: `agent.name`, `agent.instructions`
- Tools: `tool.name`, `tool.description`, `tool.parameters`, `tool.result`
- Errors: `error.type`, `error.message`, `error.stack_trace`

### Positive Consequences

- **Comprehensive Visibility**: Full observability into agent operations, tool executions, and LLM interactions
- **Production Ready**: Proven patterns from Microsoft Agent Framework
- **Flexible Backends**: Can use local Aspire Dashboard for dev, App Insights for prod
- **Standards Compliant**: Follows OpenTelemetry GenAI semantic conventions
- **Zero Overhead**: No performance impact when observability is disabled
- **Security Conscious**: Sensitive data capture is opt-in and clearly documented
- **Easy Setup**: Single function call to initialize observability
- **Good Developer Experience**: Examples, documentation, and clear configuration

### Negative Consequences

- **Learning Curve**: Developers need to understand OpenTelemetry concepts
- **Configuration Complexity**: Multiple exporters and options can be overwhelming
- **Dependency Size**: OpenTelemetry SDK adds ~5MB to package size (already in agent-framework)
- **Potential Overhead**: When enabled, adds 1-5% performance overhead (per Microsoft benchmarks)
- **Data Volume**: Can generate significant telemetry data in high-throughput scenarios
- **Breaking Change Risk**: Future OpenTelemetry API changes may require updates

### Neutral Consequences

- **Optional Azure Monitor Package**: Users need to install `azure-monitor-opentelemetry-exporter` for App Insights
- **Manual Setup Required**: Developers must call `setup_observability()` in their code
- **Environment-Based Config**: Relies on environment variables for configuration
- **Singleton Pattern**: Only one observability setup per process

## Validation

### Manual Testing

1. **Console Output**:
   ```bash
   ENABLE_OTEL=true python examples/observability_example.py
   ```
   Expected: Telemetry printed to console

2. **Aspire Dashboard**:
   ```bash
   # Terminal 1: Start Aspire
   docker run --rm -it -p 18888:18888 -p 4317:18889 mcr.microsoft.com/dotnet/aspire-dashboard:latest

   # Terminal 2: Run agent
   ENABLE_OTEL=true OTLP_ENDPOINT=http://localhost:4317 python examples/observability_example.py
   ```
   Expected: Traces visible in dashboard at http://localhost:18888

3. **Application Insights**:
   ```bash
   ENABLE_OTEL=true APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=xxx" python examples/observability_example.py
   ```
   Expected: Telemetry in Azure Portal > Transaction search

### Automated Testing

- Unit tests for `ObservabilitySettings` loading
- Unit tests for `setup_observability()` with different configurations
- Unit tests for exporter creation functions
- Unit tests for `get_tracer()` and `get_meter()` helpers
- Integration tests for agent execution with telemetry
- Integration tests for tool execution spans
- Integration tests for error tracking
- Coverage target: >85%

### Acceptance Criteria

All criteria from spec must be met:

- ✅ OpenTelemetry dependencies verified
- ✅ `ObservabilitySettings` class loads from environment
- ✅ `setup_observability()` creates providers for traces, logs, and metrics
- ✅ Support for OTLP endpoint exporters
- ✅ Support for Azure Application Insights exporters
- ✅ Support for console exporters (fallback)
- ✅ `get_tracer()` and `get_meter()` helper functions
- ✅ Agent operations create spans with proper attributes
- ✅ Tool executions create child spans
- ✅ Token usage metrics recorded
- ✅ Operation duration metrics recorded
- ✅ Errors and exceptions tracked
- ✅ Sensitive data capture can be toggled
- ✅ Observability can be disabled (default state)
- ✅ Documentation in `.env.example`
- ✅ Usage example demonstrates all major features
- ✅ ADR documents implementation decisions

## Links

- [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/otel/)
- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/)
- [Azure Monitor OpenTelemetry](https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-enable)
- [Aspire Dashboard](https://learn.microsoft.com/en-us/dotnet/aspire/fundamentals/dashboard)
- Related ADRs:
  - [ADR-0005: Event Bus Pattern](./0005-event-bus-pattern-for-loose-coupling.md)
  - [ADR-0012: Middleware Integration Strategy](./0012-middleware-integration-strategy.md)

## Notes

### Performance Considerations

- **Disabled**: Zero overhead, no-op tracer and meter
- **Enabled**: 1-5% overhead (per Microsoft Agent Framework benchmarks)
- **Batch Processors**: Exporters use batch processing to minimize I/O
- **Async Export**: Telemetry export is asynchronous to avoid blocking
- **Histogram Buckets**: Optimized for GenAI workloads (tokens 0-100k, duration 0-60s)

### Security Considerations

- **Default Secure**: Sensitive data capture disabled by default
- **Clear Warnings**: Documentation warns against enabling in production
- **Environment-Based**: Configuration via environment variables (no secrets in code)
- **Truncation**: Tool results truncated to 1000 chars to avoid excessive data

### Future Enhancements

- Support for additional APM vendors (New Relic, Datadog, Dynatrace)
- Custom span processors for advanced filtering
- Distributed tracing across multiple agents
- Performance optimization for high-throughput scenarios
- Automatic sampling configuration
- Context propagation for async operations
- Integration with VS Code AI Toolkit
- Grafana dashboard templates
- Alerting rules for Azure Monitor

### Dependencies

This feature depends on:

- Event Bus (ADR-0005) - For telemetry event emission
- Middleware (ADR-0012) - For instrumentation pattern
- Configuration (config.py) - For settings management
- agent-framework>=1.0.0b251007 - Provides OpenTelemetry dependencies

### Migration Path

For existing applications:

1. Update dependencies (already have agent-framework)
2. Add observability config to `.env`
3. Call `setup_observability()` at application startup
4. Enable via `ENABLE_OTEL=true`
5. No code changes required to existing tools or agent logic

Zero breaking changes - completely opt-in.
