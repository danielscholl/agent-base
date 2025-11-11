# Architectural Decision Records (ADRs)

An Architectural Decision (AD) is a justified software design choice that addresses a functional or non-functional requirement that is architecturally significant. An Architectural Decision Record (ADR) captures a single AD and its rationale.

For more information [see](https://adr.github.io/)

## How are we using ADRs to track technical decisions?

1. Copy `docs/decisions/adr-template.md` to `docs/decisions/NNNN-title-with-dashes.md`, where NNNN indicates the next number in sequence.
    1. Check for existing PR's to make sure you use the correct sequence number.
    2. There is also a short form template `docs/decisions/adr-short-template.md`
2. Edit `NNNN-title-with-dashes.md`.
    1. Status must initially be `proposed`
    2. List of `deciders` must include the github ids of the people who will sign off on the decision.
    3. You should list the names or github ids of all partners who were consulted as part of the decision.
    4. Keep the list of `deciders` short. You can also list people who were `consulted` or `informed` about the decision.
3. For each option list the good, neutral and bad aspects of each considered alternative.
    1. Detailed investigations can be included in the `More Information` section inline or as links to external documents.
4. Share your PR with the deciders and other interested parties.
   1. Deciders must be listed as required reviewers.
   2. The status must be updated to `accepted` once a decision is agreed and the date must also be updated.
   3. Approval of the decision is captured using PR approval.
5. Decisions can be changed later and superseded by a new ADR. In this case it is useful to record any negative outcomes in the original ADR.

## ADR Process for This Project

During implementation of the agent-template specification, create ADRs for:

- Architecture patterns (tool registration, dependency injection, event bus)
- Technology choices (framework selection, library decisions)
- Design patterns (component interaction, abstraction layers)
- API designs (public interfaces, method signatures, response formats)
- Naming conventions (class names, module structure, terminology)
- Testing strategies (test organization, mocking patterns, coverage targets)
- Performance trade-offs (caching strategies, optimization choices)
- Security decisions (authentication methods, data handling)
- UI/UX patterns (display formats, interaction models)

**Rule of thumb**: If the decision could be made differently and the alternative would be reasonable, document it with an ADR.

## Templates

- **Full Template**: `adr-template.md` - Comprehensive template with all sections
- **Short Template**: `adr-short-template.md` - Simplified template for smaller decisions

## ADR Index

### Foundation & Architecture
- [ADR-0001: Module and Package Naming Conventions](./0001-module-and-package-naming-conventions.md)
- [ADR-0002: Repository Infrastructure and DevOps Setup](./0002-repository-infrastructure-and-devops-setup.md)
- [ADR-0004: Custom Exception Hierarchy Design](./0004-custom-exception-hierarchy-design.md)
- [ADR-0005: Event Bus Pattern for Loose Coupling](./0005-event-bus-pattern-for-loose-coupling.md)

### LLM Provider Strategy
- [ADR-0003: Multi-Provider LLM Architecture Strategy](./0003-multi-provider-llm-architecture.md) ⭐ _Overall provider strategy_
  - [ADR-0015: Gemini Provider Integration](./0015-gemini-provider-integration.md) - Custom client implementation
  - [ADR-0016: Local Provider Integration](./0016-local-provider-integration.md) - Docker Model Runner integration

### Tools & Components
- [ADR-0006: Class-Based Toolset Architecture](./0006-class-based-toolset-architecture.md)
- [ADR-0007: Tool Response Format](./0007-tool-response-format.md)
- [ADR-0012: Middleware Integration Strategy](./0012-middleware-integration-strategy.md)
- [ADR-0013: Memory Architecture](./0013-memory-architecture.md)

### User Interface & Experience
- [ADR-0009: CLI Framework Selection](./0009-cli-framework-selection.md)
- [ADR-0010: Display Output Format](./0010-display-output-format.md)
- [ADR-0011: Session Management Architecture](./0011-session-management-architecture.md)

### Quality & Operations
- [ADR-0008: Testing Strategy and Coverage Targets](./0008-testing-strategy-and-coverage-targets.md)
- [ADR-0014: Observability Integration](./0014-observability-integration.md)

