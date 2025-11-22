# Feature: Mem0 Semantic Memory Enhancement

## Feature Description

The Mem0 Semantic Memory Enhancement upgrades agent-base's memory system from simple keyword-based search to intelligent vector-based semantic search with long-term context retention. This feature integrates with [mem0](https://mem0.ai), enabling the agent to:

- **Understand Context Semantically**: Search for "authentication errors" and find related conversations about "login failures" or "credential issues" through vector similarity
- **Retain Knowledge Across Sessions**: Remember user preferences, coding styles, and project-specific knowledge beyond single conversation sessions
- **Build Long-term Context**: Learn patterns and relationships across conversations, creating persistent knowledge graphs
- **Intelligent Memory Retrieval**: Surface relevant context based on semantic similarity rather than keyword matching
- **Scale Memory Storage**: Support production deployments with distributed storage and persistent knowledge bases

The enhancement follows agent-base's proven architecture patterns (MemoryManager abstraction, factory-based backend selection, graceful fallbacks) and deployment philosophy (containerized local option + cloud-hosted option, similar to telemetry). Users opt-in via configuration (`MEMORY_TYPE=mem0`) without disrupting the existing in-memory system.

## User Story

**As a** developer using agent-base for complex, multi-session projects
**I want to** enable semantic memory so the agent remembers my preferences and past solutions across sessions
**So that** I don't have to repeatedly re-explain context and the agent provides increasingly personalized assistance over time

## Problem Statement

The current in-memory storage system (`InMemoryStore`) provides basic conversation history but exhibits critical limitations that reduce agent effectiveness:

1. **No Semantic Understanding**: Uses simple keyword matching (`query.lower().split()`) that misses conceptually related content with different wording. Searching "authentication errors" won't find "login failures" even though they're semantically identical.

2. **Session-Bound Context**: Memory persists only within a single conversation. Once restarted, all learned context (user preferences, project knowledge, past solutions) is lost. Every session starts from zero.

3. **No Cross-Conversation Learning**: Cannot build long-term knowledge about users, projects, or patterns. Teaching the agent your coding style today means re-teaching it tomorrow.

4. **Linear Context Growth**: Entire memory history is injected as context (limited by `memory_history_limit=20`), creating linear scaling between conversation length and context consumption. No intelligent pruning or relevance-based retrieval.

5. **Limited Metadata Richness**: Stores only role, content, timestamp, and basic metadata—lacking entity extraction, topic modeling, and relationship mapping for intelligent retrieval.

6. **Acknowledged Technical Debt**: The codebase explicitly recognizes this gap (config.py:73-77):
   ```python
   # Memory configuration (currently redundant with thread persistence)
   # Note: Memory is currently redundant with thread persistence
   # Default to false until semantic memory (mem0) is implemented
   ```
   The abstraction layers are ready; the semantic backend needs implementation.

7. **Scalability Constraints**: In-memory storage doesn't scale for production agents handling hundreds of conversations, distributed deployments, or persistent knowledge bases across restarts.

This represents the primary gap in agent-base's architecture, as noted in quality analysis: "Memory System Maturity (6/10) - Current: Basic in-memory storage with keyword search | Planned: Semantic search (mem0 integration mentioned) | Gap: No vector search, no memory summarization, basic persistence."

## Solution Statement

Introduce a `Mem0Store` implementation that integrates the mem0 Python library directly into the agent process, providing semantic memory capabilities through local file-based storage or cloud-hosted service, reusing the agent's existing LLM configuration.

**Architecture Design**:

1. **Python Library Integration** (In-Process):
   - mem0 runs as a Python library within the agent process (not separate server)
   - **Reuses agent's existing LLM client** - no duplicate API calls
   - Two storage modes:
     - **Local**: Chroma file-based vector DB in `~/.agent/mem0_data/`
     - **Cloud**: mem0.ai managed service via API
   - Zero Docker complexity

2. **MemoryManager Implementation**:
   - New `Mem0Store` class implementing abstract `MemoryManager` interface
   - Factory function `create_memory_manager()` routes based on `config.memory_type`
   - Graceful fallback to `InMemoryStore` if mem0 unavailable
   - Zero changes to existing `Agent` or `ContextProvider` code

3. **Semantic Operations**:
   - `add()`: Store messages with automatic vector embeddings and entity extraction
   - `search()`: Semantic similarity search using vector embeddings
   - `get_recent()`: Time-weighted relevance retrieval
   - `get_all()`: Full memory export
   - `clear()`: Delete local storage or cloud namespace

4. **LLM Configuration Reuse**:
   - Extract LLM config from `AgentConfig` (OpenAI, Anthropic, Azure, etc.)
   - Pass to mem0 so it uses the **same provider and model** as the agent
   - Single LLM configuration, shared between agent and memory
   - Cost-efficient: no duplicate embedding/extraction API calls

## Relevant Files

### Existing Files to Modify

- **src/agent/config.py**
  - Add mem0-specific configuration fields:
    - Storage: `mem0_storage_path` (local Chroma DB path, default: `~/.agent/mem0_data/`)
    - Cloud: `MEM0_API_KEY`, `MEM0_ORG_ID` (for cloud mode)
    - User: `MEM0_USER_ID`, `MEM0_PROJECT_ID` (namespace isolation)
  - Update `AgentConfig.from_env()` to load environment variables
  - No validation needed (graceful fallback to InMemoryStore)

- **src/agent/memory/__init__.py** (lines 30-45)
  - Extend `create_memory_manager()` factory to route to `Mem0Store` when `config.memory_type == "mem0"`
  - Add import for new `Mem0Store` class
  - Export `Mem0Store` in `__all__`

- **src/agent/memory/manager.py** (lines 1-137)
  - Add `retrieve_for_context()` with **default implementation** (non-abstract)
  - Default composes `search()` + `get_recent()` for backward compatibility
  - Backends can override for optimized semantic retrieval
  - Defines standardized result schema across backends

- **src/agent/cli/commands.py** (lines 227-249)
  - Add `handle_memory_command()` function (similar to `handle_telemetry_command`)
  - Implement Docker container management: `start`, `stop`, `status`, `url`
  - Add operability commands for debugging:
    - `list`: Show recent memories with IDs
    - `search <query>`: Search memories interactively
    - `forget <id>`: Delete specific memory by ID
    - `export [file]`: Export memories to JSON file
  - Add help text for all memory commands to `show_help()`

- **src/agent/cli/app.py** (lines 103-126, 233-240)
  - Add `--memory` CLI option for container management
  - Add memory command handler to interactive mode command routing

- **.env.example** (end of file)
  - Add mem0 configuration section with examples for both self-hosted and cloud modes

- **pyproject.toml** (dependencies section)
  - Add to `[mem0]` optional dependency group:
    - `mem0ai>=1.0.0` - Core mem0 library
    - `chromadb>=0.5.0` - Local vector storage

### New Files to Create

- **src/agent/memory/mem0_store.py**
  - `Mem0Store` class implementing `MemoryManager` abstract base
  - Uses `mem0.Memory` Python library (in-process integration)
  - Configures mem0 to reuse agent's existing LLM client
  - Supports local storage (Chroma) and cloud storage (mem0.ai)
  - Semantic search via vector embeddings
  - Secret scrubbing (API keys, tokens, passwords)
  - User/project namespacing for isolation
  - Async operations with `asyncio.to_thread()` for non-blocking I/O

- **src/agent/memory/mem0_utils.py**
  - `extract_llm_config()`: Convert `AgentConfig` → mem0 LLM configuration
  - Supports all agent providers: OpenAI, Anthropic, Azure OpenAI, Gemini, Local
  - Maps provider-specific auth (API keys, endpoints, versions)
  - Returns mem0-compatible config dict

- **tests/unit/memory/test_mem0_store.py**
  - Unit tests for `Mem0Store` class
  - Mock `mem0.Memory` class (not HTTP responses)
  - Test semantic search operations
  - Test LLM config integration
  - Test local vs cloud mode
  - Test namespace isolation
  - Test secret scrubbing

- **tests/unit/memory/test_mem0_utils.py**
  - Tests for LLM config extraction
  - Test all provider mappings (OpenAI, Anthropic, Azure, etc.)
  - Test config validation and defaults

## Implementation Plan

### Phase 0: Quick Win - Semantic Retrieval for Context ✅ **(Implemented)**

**Objective**: Update `MemoryContextProvider` to use semantic/keyword search for context injection instead of chronological slicing. This provides immediate value EVEN with `InMemoryStore` and sets the foundation for Mem0Store.

**Why This First**:
- Low risk, high impact change
- Improves relevance for existing `InMemoryStore` users immediately
- Makes Mem0Store's semantic capabilities actually valuable when added
- No breaking changes to API or consumers

**Changes**:

1. **Add `retrieve_for_context()` to MemoryManager Interface**:
   ```python
   @abstractmethod
   async def retrieve_for_context(
       self, messages: list[dict], limit: int = 10
   ) -> dict:
       """Retrieve memories relevant for context injection.

       Args:
           messages: Current conversation messages (for extracting search context)
           limit: Maximum number of memories to retrieve

       Returns:
           Structured response with relevant memories

       Note:
           - Default implementation: chronological (last N)
           - Semantic backends: similarity-based on latest user message
       """
   ```

2. **Implement in InMemoryStore**:
   - Extract query from latest user message in `messages`
   - Call existing `search()` method with query
   - Fall back to `get_recent()` if no query extractable
   - Return top-k keyword matches

3. **Update MemoryContextProvider.invoking()**:
   - Change from `memory_manager.get_all()` + slice
   - To `memory_manager.retrieve_for_context(messages, limit=self.history_limit)`
   - Immediate relevance improvement for all backends

4. **Testing**:
   - Test InMemoryStore retrieves keyword-relevant memories
   - Test fallback to recent when no query
   - Test limit enforcement
   - Verify backward compatibility

### Phase 1: Configuration, Health Checks & CLI Infrastructure ✅ **(Implemented)**

**Objective**: Establish mem0 configuration, health checks, and Docker container management before implementing Mem0Store.

**Changes**:

1. **Configuration Setup**:
   - Add mem0 configuration fields to `AgentConfig`:
     - `mem0_host: str | None` (self-hosted endpoint)
     - `mem0_api_key: str | None` (cloud mode)
     - `mem0_org_id: str | None` (cloud mode)
     - `mem0_user_id: str | None` (user namespace, default: username)
     - `mem0_project_id: str | None` (project namespace for isolation)
   - Implement environment variable loading
   - Add validation: require either `mem0_host` OR (`mem0_api_key` + `mem0_org_id`)
   - Update `.env.example` with configuration examples

2. **Health Check Integration**:
   - Implement `check_mem0_endpoint()` in `mem0_utils.py`
   - Add memory status to `agent --check` command:
     ```
     Memory Backend: mem0 (semantic search enabled)
     Endpoint: http://localhost:8000 ✓ reachable
     Namespace: user=alice, project=agent-base
     ```
   - Display warnings if mem0 configured but unreachable

3. **CLI Commands**:
   - Implement `handle_memory_command()` with actions:
     - `start`: Launch Docker Compose stack (Postgres + mem0)
     - `stop`: Shutdown containers
     - `status`: Show running state + health
     - `url`: Display endpoint and configuration
   - Add `/memory` command routing in interactive mode
   - Add `--memory` flag for non-interactive mode
   - Update help documentation

4. **Docker Compose (PRIMARY)**:
   - Create `docker/mem0/docker-compose.yml`:
     - PostgreSQL 15 with pgvector extension
     - mem0 server with proper dependencies
     - Health checks for both services
     - Volume mounts for persistence
     - Environment variable configuration
   - Add `.dockerignore` if needed
   - Document quickstart docker run as best-effort alternative

5. **Testing**:
   - Unit tests for config loading and validation
   - Unit tests for `check_mem0_endpoint()` (mocked)
   - Integration tests for Docker Compose lifecycle

### Phase 2: Mem0Store Implementation ✅ **(Implemented)**

**Objective**: Implement `Mem0Store` class with semantic memory capabilities, async operations, namespacing, and safety gates.

**Changes**:

1. **Mem0Store Class**:
   - Implement all `MemoryManager` methods:
     - `add()`: Store with vector embeddings + entity extraction
     - `search()`: Semantic similarity search
     - `get_all()`: Retrieve all memories for namespace
     - `get_recent()`: Time-sorted recent memories
     - `clear()`: Namespace-aware deletion
     - `retrieve_for_context()`: Semantic retrieval for context injection
   - Use `httpx.AsyncClient` for non-blocking I/O
   - Implement proper async/await patterns throughout

2. **Namespacing (First-Class)**:
   - User-level isolation via `mem0_user_id`
   - Project-level isolation via `mem0_project_id`
   - Namespace format: `{user_id}:{project_id}` or fallback to `{user_id}` only
   - All operations scoped to namespace
   - Tests verify cross-namespace isolation

3. **Safety Gates**:
   - Support `metadata: {save: false}` to prevent storage
   - Filter out messages with `save: false` before calling mem0 API
   - Log when messages are filtered for visibility
   - Document pattern for preventing secret storage:
     ```python
     # Don't save API keys or secrets
     await memory.add([{
         "role": "user",
         "content": "My API key is sk-...",
         "metadata": {"save": false}  # ← Prevents storage
     }])
     ```

4. **Connection Management**:
   - ✅ Factory function `get_mem0_client()` routes self-hosted vs cloud
   - ✅ Non-blocking I/O via `asyncio.to_thread()` wrapping sync client
   - ✅ Clear error messages for misconfiguration
   - ✅ Graceful degradation with logging
   - ⏳ Connection pooling via httpx.AsyncClient (future enhancement)
   - ⏳ Retry logic with exponential backoff (future enhancement)

5. **Error Handling**:
   - Catch mem0 connection errors, network timeouts
   - Return structured error responses (not exceptions)
   - Log warnings with actionable messages
   - Fallback handled at factory level (not in Mem0Store itself)

6. **Factory Integration**:
   - Update `create_memory_manager()`:
     ```python
     if config.memory_type == "mem0":
         try:
             return Mem0Store(config)
         except Exception as e:
             logger.warning(f"Mem0Store init failed: {e}. Falling back to InMemoryStore.")
             return InMemoryStore(config)
     else:
         return InMemoryStore(config)
     ```
   - Add explicit logging for backend selection

7. **Testing**:
   - Unit tests with mocked mem0 client (no real API calls)
   - Test all CRUD operations
   - Test namespace isolation (alice vs bob)
   - Test safety gates (`save: false` filtered)
   - Test async operations
   - Test error handling and graceful degradation
   - Integration tests with real Docker stack

### Phase 3: Polish & Production Readiness

**Objective**: Add observability, context bloat prevention, guardrails, and finalize for production.

**Implementation Status**:
- ✅ Memory Filter Guardrails (secret scrubbing)
- ⏳ Observability Integration (future)
- ⏳ Context Bloat Prevention (partially complete)
- ⏳ Performance Benchmarks (future)
- ⏳ Documentation (in progress)

**Changes**:

1. **Observability Integration** *(Future enhancement)*:
   - Add OpenTelemetry spans around memory operations:
     - `memory.add` span with count attribute
     - `memory.search` span with query + result count
     - `memory.retrieve_for_context` span
   - Track latency metrics (target: <100ms add, <200ms search)
   - Log slow operations (> 500ms) as warnings

2. **Context Bloat Prevention** *(Partially complete)*:
   - ✅ Cap `retrieve_for_context()` to configurable limit (default: 10)
   - ⏳ Deduplicate by semantic similarity (avoid near-duplicates)
   - ⏳ Prefer concise snippets over full messages when possible
   - ⏳ Add `max_context_tokens` configuration (future: token-aware limiting)

3. **Memory Filter Guardrails** ✅ **(Implemented)**:
   - ✅ Pattern-based filters for common secrets:
     - API keys (sk_*, pk_*, api_key=)
     - Bearer tokens
     - Passwords in plaintext
   - ✅ Auto-redaction with `[REDACTED]` before storage
   - ✅ Logged warnings when secrets detected
   - ✅ Override with `metadata: {force_save: true}` (use cautiously)
   - ⏳ Configurable via `MEMORY_FILTER_PATTERNS` env var (future)

4. **Performance Benchmarks**:
   - Create `tests/performance/test_memory_performance.py`
   - Benchmark `add()` with 100 messages: target <10ms avg
   - Benchmark `search()` with 1000 memories: target <200ms
   - Benchmark `retrieve_for_context()`: target <150ms
   - Memory overhead test: <50MB for 1000 memories

5. **Documentation**:
   - Add "Semantic Memory" section to `docs/design/usage.md`:
     - Benefits explanation
     - Setup guide for Docker Compose
     - Configuration examples (self-hosted + cloud)
     - Safety gates documentation
     - Troubleshooting guide
   - Update `README.md` features list
   - Create ADR (Architecture Decision Record):
     - Why mem0 over alternatives
     - Why Docker Compose as primary
     - Why `retrieve_for_context()` API design
     - Safety gate rationale

6. **Validation**:
   - Run full test suite (unit + integration)
   - Run performance benchmarks
   - Manual end-to-end testing
   - Security review of namespace isolation
   - Review all validation commands pass

## Step by Step Tasks

**Note**: Execute tasks in order top-to-bottom. Each phase builds on the previous.

---

## Phase 0 Tasks: Quick Win - Semantic Retrieval

### Task 0.1: Add `retrieve_for_context()` to MemoryManager

- Open `src/agent/memory/manager.py`
- Add abstract method after existing methods (around line 105):
  ```python
  @abstractmethod
  async def retrieve_for_context(
      self, messages: list[dict], limit: int = 10
  ) -> dict:
      """Retrieve memories relevant for context injection.

      Implementations can use different strategies:
      - Chronological: Return last N messages (simple)
      - Keyword-based: Search for relevant keywords from current message
      - Semantic: Vector similarity to current message (Mem0Store)

      Args:
          messages: Current conversation messages (list of dicts with role/content)
          limit: Maximum number of memories to retrieve

      Returns:
          Structured response dict with relevant memories
      """
      pass
  ```
- Run mypy to verify abstract method signature

### Task 0.2: Implement `retrieve_for_context()` in InMemoryStore

- Open `src/agent/memory/store.py`
- Add method after `clear()` (around line 171):
  ```python
  async def retrieve_for_context(
      self, messages: list[dict], limit: int = 10
  ) -> dict:
      """Retrieve keyword-relevant memories for context.

      Strategy: Extract query from latest user message and search.
      If no query available, fall back to most recent memories.
      """
      # Extract query from latest user message
      query = None
      for msg in reversed(messages):
          if isinstance(msg, dict) and msg.get("role") == "user":
              query = msg.get("content", "").strip()
              break

      # Search if we have a query, otherwise get recent
      if query:
          return await self.search(query, limit=limit)
      else:
          return await self.get_recent(limit=limit)
  ```
- Verify implementation calls existing methods

### Task 0.3: Update MemoryContextProvider to Use retrieve_for_context()

- Open `src/agent/memory/context_provider.py`
- Replace `invoking()` method (lines 45-93) with:
  ```python
  async def invoking(
      self, messages: ChatMessage | MutableSequence[ChatMessage], **kwargs: Any
  ) -> Context:
      """Inject relevant memories before agent invocation."""
      try:
          # Convert ChatMessage to dict format for memory manager
          messages_dicts = []
          msg_list = messages if isinstance(messages, MutableSequence) else [messages]
          for msg in msg_list:
              text = self._get_message_text(msg)
              if text:
                  messages_dicts.append({
                      "role": str(getattr(msg, "role", "user")),
                      "content": text
                  })

          # Retrieve relevant memories using new method
          result = await self.memory_manager.retrieve_for_context(
              messages_dicts, limit=self.history_limit
          )

          if result.get("success") and result["result"]:
              memories = result["result"]
              logger.debug(f"Injecting {len(memories)} relevant memories into context")

              # Build context from relevant memories
              context_parts = ["Previous conversation history:"]
              for mem in memories:
                  role = mem.get("role", "unknown")
                  content = mem.get("content", "")
                  context_parts.append(f"{role}: {content}")

              context_text = "\n".join(context_parts)
              return Context(instructions=context_text)
          else:
              logger.debug("No relevant memories to inject")
              return Context()

      except Exception as e:
          logger.error(f"Error retrieving memories for context: {e}", exc_info=True)
          return Context()
  ```

### Task 0.4: Test retrieve_for_context() Implementation

- Open `tests/unit/memory/test_memory_store.py`
- Add test after existing tests (around line 200):
  ```python
  @pytest.mark.asyncio
  async def test_retrieve_for_context_with_query(self, memory_store, sample_messages):
      """Test retrieve_for_context extracts query and searches."""
      await memory_store.add(sample_messages)

      # Messages with user query
      current_messages = [
          {"role": "user", "content": "Tell me about Alice"}
      ]

      result = await memory_store.retrieve_for_context(current_messages, limit=5)

      assert result["success"] is True
      # Should find messages mentioning Alice
      assert len(result["result"]) > 0
      assert any("Alice" in mem["content"] for mem in result["result"])

  @pytest.mark.asyncio
  async def test_retrieve_for_context_fallback(self, memory_store, sample_messages):
      """Test retrieve_for_context falls back to recent when no query."""
      await memory_store.add(sample_messages)

      # Empty messages - should fall back to get_recent
      result = await memory_store.retrieve_for_context([], limit=3)

      assert result["success"] is True
      assert len(result["result"]) <= 3
  ```
- Run tests: `pytest tests/unit/memory/test_memory_store.py -v -k retrieve_for_context`

### Task 0.5: Test MemoryContextProvider Integration

- Open `tests/unit/memory/test_memory_integration.py` (or create if doesn't exist)
- Add integration test:
  ```python
  @pytest.mark.asyncio
  async def test_context_provider_uses_retrieve_for_context(memory_config):
      """Verify ContextProvider calls retrieve_for_context."""
      from agent.memory import InMemoryStore, MemoryContextProvider
      from agent_framework import ChatMessage

      store = InMemoryStore(memory_config)
      provider = MemoryContextProvider(store, history_limit=5)

      # Add some memories
      await store.add([
          {"role": "user", "content": "My name is Bob"},
          {"role": "assistant", "content": "Nice to meet you, Bob"}
      ])

      # Create messages asking about the name
      current_msgs = [ChatMessage(role="user", content="What's my name?")]

      # Call invoking() and verify it retrieves relevant context
      context = await provider.invoking(current_msgs)

      assert context.instructions is not None
      assert "Bob" in context.instructions  # Should find relevant memory
  ```
- Run integration tests: `pytest tests/unit/memory/test_memory_integration.py -v`

---

## Phase 1 Tasks: Configuration & Infrastructure

### Task 1.1: Add mem0 Configuration to AgentConfig

- Open `src/agent/config.py`
- Add mem0 fields to `AgentConfig` dataclass (after line 77):
  ```python
  # Mem0 semantic memory configuration
  mem0_host: str | None = None  # Self-hosted endpoint
  mem0_api_key: str | None = None  # Cloud mode API key
  mem0_org_id: str | None = None  # Cloud mode organization ID
  mem0_user_id: str | None = None  # User namespace (default: username)
  mem0_project_id: str | None = None  # Project namespace for isolation
  ```
- Update `from_env()` method (after line 153):
  ```python
  # Mem0 configuration
  config.mem0_host = os.getenv("MEM0_HOST")
  config.mem0_api_key = os.getenv("MEM0_API_KEY")
  config.mem0_org_id = os.getenv("MEM0_ORG_ID")
  config.mem0_user_id = os.getenv("MEM0_USER_ID") or os.getenv("USER") or "default-user"
  config.mem0_project_id = os.getenv("MEM0_PROJECT_ID")
  ```
- Add validation in `validate()` method (after line 243):
  ```python
  # Validate mem0 configuration if enabled
  if self.memory_type == "mem0":
      if not self.mem0_host and not (self.mem0_api_key and self.mem0_org_id):
          raise ValueError(
              "Mem0 memory requires either:\n"
              "  - Self-hosted: MEM0_HOST environment variable\n"
              "  - Cloud: MEM0_API_KEY and MEM0_ORG_ID environment variables"
          )
  ```

### Task 1.2: Write Configuration Tests

- Open `tests/unit/memory/test_memory_config.py`
- Add tests for mem0 configuration:
  ```python
  def test_mem0_config_self_hosted(monkeypatch):
      """Test mem0 self-hosted configuration."""
      monkeypatch.setenv("MEMORY_TYPE", "mem0")
      monkeypatch.setenv("MEM0_HOST", "http://localhost:8000")
      monkeypatch.setenv("MEM0_USER_ID", "alice")

      config = AgentConfig.from_env()
      assert config.memory_type == "mem0"
      assert config.mem0_host == "http://localhost:8000"
      assert config.mem0_user_id == "alice"

      # Should validate successfully
      config.validate()  # Should not raise

  def test_mem0_config_cloud(monkeypatch):
      """Test mem0 cloud configuration."""
      monkeypatch.setenv("MEMORY_TYPE", "mem0")
      monkeypatch.setenv("MEM0_API_KEY", "test-key")
      monkeypatch.setenv("MEM0_ORG_ID", "test-org")

      config = AgentConfig.from_env()
      config.validate()  # Should not raise

  def test_mem0_config_validation_fails(monkeypatch):
      """Test mem0 validation fails when misconfigured."""
      monkeypatch.setenv("MEMORY_TYPE", "mem0")
      # No MEM0_HOST or MEM0_API_KEY set

      config = AgentConfig.from_env()

      with pytest.raises(ValueError, match="Mem0 memory requires"):
          config.validate()
  ```
- Run: `pytest tests/unit/memory/test_memory_config.py -v`

### Task 2: Update .env.example with Mem0 Configuration

- Add new section "Memory Configuration (Mem0)" with:
  - Documentation for both self-hosted and cloud modes
  - Example: `MEMORY_TYPE=mem0` to enable semantic memory
  - Example: `MEM0_HOST=http://localhost:8000` for self-hosted
  - Example: `MEM0_API_KEY=your-api-key` for cloud mode
  - Example: `MEM0_ORG_ID=your-org-id` for cloud mode
  - Example: `MEM0_USER_ID=default-user` for namespacing
  - Comment explaining when to use each mode
  - Link to mem0 documentation

### Task 3: Install mem0ai Python Package

- Run: `uv add mem0ai` to add dependency
- Run: `uv add httpx` (if not already present) for health checks
- Verify package installation
- Check for any dependency conflicts

### Task 4: Implement Mem0 Utility Functions

- Create `src/agent/memory/mem0_utils.py` with:
  - `check_mem0_endpoint(endpoint: str | None = None, timeout: float = 0.02) -> bool`:
    - Similar to `check_telemetry_endpoint()` in observability.py
    - Default endpoint: `http://localhost:8000`
    - Fast socket connection test for auto-detection
  - `get_mem0_client(config: AgentConfig) -> MemoryClient`:
    - Factory for mem0 client instances
    - Route to self-hosted (`MemoryClient(host=config.mem0_host)`) or cloud (`MemoryClient(api_key=config.mem0_api_key, org_id=config.mem0_org_id)`)
    - Connection pooling and retry logic
    - Raise clear errors for misconfiguration
- Write tests in `tests/unit/memory/test_mem0_utils.py`:
  - Mock socket connections for `check_mem0_endpoint()`
  - Test client factory routing (self-hosted vs cloud)
  - Test error handling for missing configuration
  - Test connection timeout behavior

### Task 5: Implement Mem0Store Class

- Create `src/agent/memory/mem0_store.py` with:
  - `Mem0Store(MemoryManager)` class
  - `__init__(self, config: AgentConfig)`:
    - Call `super().__init__(config)`
    - Initialize mem0 client via `get_mem0_client(config)`
    - Set user namespace from `config.mem0_user_id` or default
  - `async def add(self, messages: list[dict]) -> dict`:
    - Validate messages (reuse validation from `InMemoryStore`)
    - For each message, call `self.client.add()` with user_id namespace
    - Extract entities and metadata via mem0's automatic processing
    - Return standardized success/error response
  - `async def search(self, query: str, limit: int = 5) -> dict`:
    - Validate query (non-empty check)
    - Call `self.client.search(query, user_id=self.user_id, limit=limit)`
    - Rank by semantic similarity score
    - Format results to match InMemoryStore format (for compatibility)
    - Return standardized response
  - `async def get_all() -> dict`:
    - Call `self.client.get_all(user_id=self.user_id)`
    - Handle pagination if dataset is large
    - Return all memories for the user namespace
  - `async def get_recent(self, limit: int = 10) -> dict`:
    - Get all memories and sort by timestamp
    - Return most recent N memories
  - `async def clear() -> dict`:
    - Call `self.client.delete_all(user_id=self.user_id)`
    - Clear all memories for user namespace
    - Return success response
  - Error handling:
    - Catch mem0 connection errors
    - Log warnings
    - Return error responses using `_create_error_response()`
- Write tests in `tests/unit/memory/test_mem0_store.py`:
  - Mock mem0 client responses
  - Test all CRUD operations (add, search, get_all, get_recent, clear)
  - Test error handling (connection failures, invalid inputs)
  - Test user namespace isolation
  - Test semantic search result formatting

### Task 6: Update Memory Factory Function

- Modify `src/agent/memory/__init__.py`:
  - Import `Mem0Store` from `agent.memory.mem0_store`
  - Add `Mem0Store` to `__all__` exports
  - Update `create_memory_manager()` function:
    ```python
    if config.memory_type == "mem0":
        try:
            return Mem0Store(config)
        except Exception as e:
            logger.warning(f"Failed to initialize Mem0Store: {e}. Falling back to InMemoryStore.")
            return InMemoryStore(config)
    else:
        return InMemoryStore(config)
    ```
  - Add logging for memory backend selection
- Write tests in `tests/unit/memory/test_memory_manager.py`:
  - Test factory routes to `Mem0Store` when `memory_type == "mem0"`
  - Test fallback to `InMemoryStore` on initialization error
  - Test default behavior (returns `InMemoryStore`)

### Task 7: Implement CLI Memory Command Handler

- Add to `src/agent/cli/commands.py`:
  - `async def handle_memory_command(user_input: str, console: Console) -> None`:
    - Parse action from user input: `start|stop|status|url|help`
    - Container name: `mem0-server`
    - Default endpoint: `http://localhost:8000`
  - **start** action:
    - Check Docker availability
    - Check if container already running
    - Run Docker command:
      ```bash
      docker run --rm -d \
        -p 8000:8000 \
        --name mem0-server \
        -e POSTGRES_HOST=localhost \
        mem0ai/mem0:latest
      ```
    - Wait for startup (3 seconds)
    - Display success message with endpoint URL
    - Check if `MEMORY_TYPE=mem0` is set, provide setup instructions
  - **stop** action:
    - Run `docker stop mem0-server`
    - Display success or "not running" message
  - **status** action:
    - Check if container running via `docker ps --filter name=mem0-server`
    - Display status, uptime, and endpoint URL
  - **url** action:
    - Display endpoint URL and current configuration
    - Show whether semantic memory is enabled
  - **help** action:
    - Display available memory commands
- Update `show_help()` function:
  - Add `/memory` command to help output
  - Document available actions
- Write integration tests in `tests/integration/test_memory_cli.py`:
  - Test container start/stop lifecycle (requires Docker)
  - Mock subprocess calls for unit tests

### Task 8: Wire Memory Command to CLI App

- Modify `src/agent/cli/app.py`:
  - Add `--memory` option to `main()` function signature:
    ```python
    memory: str = typer.Option(
        None, "--memory", help="Manage semantic memory server (start|stop|status|url)"
    )
    ```
  - Add memory command handler after telemetry check:
    ```python
    if memory:
        asyncio.run(handle_memory_command(f"/memory {memory}", console))
        return
    ```
  - In interactive mode loop (around line 233-240), add memory command routing:
    ```python
    elif user_input.startswith("/memory"):
        await handle_memory_command(user_input, console)
        continue
    ```

### Task 9: Create Integration Tests for Mem0Store

- Create `tests/integration/test_mem0_integration.py`:
  - Mark tests with `@pytest.mark.integration` and `@pytest.mark.memory`
  - Add `@pytest.mark.requires_docker` for container-dependent tests
  - Test: End-to-end semantic search workflow
    - Start mem0 container
    - Initialize `Mem0Store`
    - Add messages about "authentication errors"
    - Search for "login failures"
    - Assert semantically similar results returned
    - Clean up container
  - Test: Cross-session memory persistence
    - Add memories in first session
    - Create new `Mem0Store` instance
    - Verify memories persisted across instances
  - Test: User namespace isolation
    - Add memories for user_id="alice"
    - Add memories for user_id="bob"
    - Verify alice's search doesn't return bob's memories

### Task 10: Add Docker Compose Configuration (Optional)

- Create `docker/mem0/docker-compose.yml`:
  ```yaml
  version: '3.8'
  services:
    mem0:
      image: mem0ai/mem0:latest
      container_name: mem0-server
      ports:
        - "8000:8000"
      environment:
        - POSTGRES_HOST=postgres
        - POSTGRES_DB=mem0
        - POSTGRES_USER=mem0
        - POSTGRES_PASSWORD=mem0
      depends_on:
        - postgres
    postgres:
      image: postgres:15-alpine
      environment:
        - POSTGRES_DB=mem0
        - POSTGRES_USER=mem0
        - POSTGRES_PASSWORD=mem0
      volumes:
        - mem0_data:/var/lib/postgresql/data
  volumes:
    mem0_data:
  ```
- Document in `docs/design/usage.md` or `README.md` how to use Docker Compose as alternative

### Task 11: Update Documentation

- Add section to `docs/design/usage.md`:
  - "Semantic Memory with Mem0"
  - Explain benefits of semantic search
  - Show both deployment modes (self-hosted vs cloud)
  - Provide setup examples
  - Show example searches demonstrating semantic understanding
- Update `README.md` if needed:
  - Add mem0 to feature list
  - Add quick setup example for semantic memory
- Add ADR (Architecture Decision Record) in `docs/decisions/`:
  - Document why mem0 was chosen
  - Document dual-deployment pattern rationale
  - Document fallback strategy

### Task 12: Run Validation Commands

- Execute all validation commands to ensure zero regressions and correct implementation

## Testing Strategy

### Unit Tests

1. **Configuration Tests** (`test_memory_config.py`):
   - Mem0 config loading from environment variables
   - Validation for self-hosted mode (requires `MEM0_HOST`)
   - Validation for cloud mode (requires `MEM0_API_KEY` + `MEM0_ORG_ID`)
   - Validation failure when neither mode configured properly

2. **Utility Tests** (`test_mem0_utils.py`):
   - `check_mem0_endpoint()` with mocked socket connections
   - `get_mem0_client()` factory routing (self-hosted vs cloud)
   - Error handling for missing/invalid configuration
   - Connection timeout and retry behavior

3. **Mem0Store Tests** (`test_mem0_store.py`):
   - Mock mem0 client for all tests (no real API calls)
   - Test `add()`: message validation, entity extraction, namespace isolation
   - Test `search()`: semantic similarity ranking, result formatting, limit enforcement
   - Test `get_all()`: pagination, namespace filtering
   - Test `get_recent()`: time-based sorting, limit enforcement
   - Test `clear()`: namespace-aware deletion
   - Test error handling: connection failures, invalid inputs, API errors
   - Test graceful degradation when mem0 unavailable

4. **Factory Tests** (`test_memory_manager.py`):
   - Factory routes to `Mem0Store` when `memory_type="mem0"`
   - Factory routes to `InMemoryStore` when `memory_type="in_memory"`
   - Fallback to `InMemoryStore` when `Mem0Store` initialization fails
   - Logging verification for backend selection

### Integration Tests

1. **End-to-End Workflow** (`test_mem0_integration.py`):
   - Requires Docker and real mem0 instance
   - Full workflow: start container → add memories → search → verify results → cleanup
   - Semantic search validation: Add "authentication errors", search "login failures", assert similarity
   - Cross-session persistence: Add memories → restart client → verify persistence
   - Multi-user isolation: Verify namespace boundaries between users

2. **CLI Integration** (`test_memory_cli.py`):
   - Container lifecycle: start → status → stop
   - Error handling: Docker not available, container already running
   - Auto-detection: Verify endpoint availability after start

3. **Agent Integration** (`test_agent_with_mem0.py`):
   - Real agent conversations with mem0 backend
   - Memory context injection during conversations
   - Preference learning across sessions

### Edge Cases

1. **Connection Failures**:
   - Mem0 server not reachable during `add()` → graceful error response
   - Network timeout during `search()` → return empty results with warning
   - Container stopped mid-conversation → fallback to in-memory for current session

2. **Invalid Data**:
   - Empty messages in `add()` → return validation error
   - Empty query in `search()` → return validation error
   - Malformed API responses → log error and return empty results

3. **Namespace Collisions**:
   - Multiple users with same `user_id` → should share memories (by design)
   - No `user_id` configured → use default namespace

4. **Large Datasets**:
   - `get_all()` with 10,000+ memories → test pagination
   - `search()` with high limits → test performance and ranking

5. **Concurrent Operations**:
   - Multiple `add()` calls simultaneously → test thread safety
   - `clear()` during active `search()` → test consistency

6. **Docker Edge Cases**:
   - Docker daemon not running → clear error message
   - Container startup timeout → retry with backoff
   - Port 8000 already in use → suggest alternative port

## Acceptance Criteria

1. **Semantic Search Works**:
   - [ ] Searching "authentication errors" finds conversations about "login failures"
   - [ ] Search results ranked by semantic similarity, not keyword matches
   - [ ] Search returns relevant results within 200ms for typical datasets (<1000 memories)

2. **Cross-Session Persistence**:
   - [ ] Memories added in session 1 are retrievable in session 2 (after restart)
   - [ ] User preferences learned in session 1 are applied in session 2
   - [ ] Memory survives agent container restarts

3. **Dual Deployment Modes Work**:
   - [ ] Self-hosted mode: `agent memory start` launches Docker container successfully
   - [ ] Self-hosted mode: Agent connects to `http://localhost:8000` automatically
   - [ ] Cloud mode: Agent connects to mem0.ai with API key configuration
   - [ ] Fallback to `InMemoryStore` works when mem0 unavailable

4. **CLI Commands Functional**:
   - [ ] `/memory start` starts container and displays endpoint URL
   - [ ] `/memory stop` stops container gracefully
   - [ ] `/memory status` shows accurate running status and uptime
   - [ ] `/memory url` displays endpoint and configuration
   - [ ] `--memory` flag works in non-interactive mode

5. **Zero Regressions**:
   - [ ] All existing tests pass (run `pytest`)
   - [ ] Existing `InMemoryStore` functionality unchanged
   - [ ] Default behavior (`MEMORY_TYPE=in_memory`) unchanged
   - [ ] No breaking changes to `MemoryManager` interface
   - [ ] Agent conversations work identically with both backends

6. **Auto-Detection Works**:
   - [ ] When mem0 container running, agent auto-enables semantic memory (if `MEMORY_TYPE` not explicitly set)
   - [ ] Startup messages indicate which memory backend is active
   - [ ] Clear instructions shown for enabling semantic memory

7. **Error Handling Robust**:
   - [ ] Clear error messages when mem0 configuration invalid
   - [ ] Graceful degradation to `InMemoryStore` when mem0 fails
   - [ ] Network timeouts handled without crashing
   - [ ] Docker errors display helpful troubleshooting messages

8. **Documentation Complete**:
   - [ ] `.env.example` includes mem0 configuration examples
   - [ ] `docs/design/usage.md` explains semantic memory setup and benefits
   - [ ] Code comments explain key design decisions
   - [ ] Help text (`/memory help`) is accurate and helpful

9. **Performance Acceptable**:
   - [ ] `add()` operations complete within 100ms
   - [ ] `search()` operations complete within 200ms
   - [ ] Memory overhead < 50MB for typical usage (1000 memories)
   - [ ] Container startup completes within 10 seconds

10. **Security Considerations**:
    - [ ] API keys never logged or exposed in error messages
    - [ ] User namespaces properly isolated (no cross-user data leakage)
    - [ ] Docker container runs without elevated privileges
    - [ ] Connection strings validated before use

## Validation Commands

Execute every command to validate the feature works correctly with zero regressions:

```bash
# 1. Install dependencies and verify no conflicts
cd /Users/danielscholl/source/github/danielscholl/agent-base && uv sync

# 2. Run all unit tests (fast, no external dependencies)
cd app/server && uv run pytest tests/unit/memory/ -v -m "unit and memory"

# 3. Run memory-specific unit tests with coverage
cd app/server && uv run pytest tests/unit/memory/test_mem0_store.py tests/unit/memory/test_mem0_utils.py -v --cov=agent.memory.mem0_store --cov=agent.memory.mem0_utils --cov-report=term-missing

# 4. Run integration tests (requires Docker)
cd app/server && uv run pytest tests/integration/test_mem0_integration.py -v -m integration

# 5. Run ALL memory tests (unit + integration)
cd app/server && uv run pytest tests/unit/memory/ tests/integration/test_mem0_integration.py -v

# 6. Run full test suite to ensure zero regressions
cd app/server && uv run pytest -v

# 7. Type checking with mypy
cd app/server && uv run mypy src/agent/memory/mem0_store.py src/agent/memory/mem0_utils.py

# 8. Code quality checks
cd app/server && uv run ruff check src/agent/memory/mem0_store.py src/agent/memory/mem0_utils.py
cd app/server && uv run black --check src/agent/memory/mem0_store.py src/agent/memory/mem0_utils.py

# 9. Manual validation: Start mem0 container
agent --memory start

# 10. Manual validation: Check status
agent --memory status

# 11. Manual validation: Test semantic search interactively
MEMORY_TYPE=mem0 MEM0_HOST=http://localhost:8000 agent
# In interactive mode:
# > Tell me your name is Alice
# > exit
# Restart agent:
MEMORY_TYPE=mem0 MEM0_HOST=http://localhost:8000 agent
# > What was the name I mentioned?
# (Should remember "Alice" from previous session)

# 12. Manual validation: Test fallback to InMemoryStore
# Stop mem0 container first
agent --memory stop
# Try to use mem0 (should fallback gracefully)
MEMORY_TYPE=mem0 agent -p "Hello" --verbose
# (Should show warning and use InMemoryStore)

# 13. Manual validation: Stop container
agent --memory stop

# 14. Configuration validation
agent --check
# (Should show memory backend status)

# 15. Run quick smoke test with default backend (ensure no regressions)
agent -p "Say hello" --verbose
```

## Notes

### Dependencies Added

- **mem0ai** (>=0.1.0): Core mem0 Python SDK for semantic memory operations
- **httpx** (if not present): For health checks and HTTP client functionality

### Future Considerations

1. **Semantic Context Injection** (High Priority): Enhance `MemoryContextProvider.invoking()` to use semantic search for context retrieval instead of chronological slicing. This would inject the most RELEVANT memories based on semantic similarity to the current query, rather than just the most recent messages. Requires careful design to maintain storage-backend agnosticism.

2. **Memory Summarization**: Implement automatic summarization of long conversation threads to reduce context size while preserving key information

3. **Memory Tagging**: Add tag-based filtering and organization (e.g., `#project-alpha`, `#preferences`, `#troubleshooting`)

4. **Memory Graphs**: Expose mem0's knowledge graph capabilities for relationship visualization

5. **Hybrid Search**: Combine semantic search with keyword filtering for precision control

6. **Memory Analytics**: Dashboard for memory usage, search patterns, and knowledge growth metrics

7. **Multi-tenancy**: Project-level namespacing in addition to user-level for team collaboration

8. **Memory Import/Export**: Tools for migrating memories between instances or backing up knowledge bases

9. **Intelligent Pruning**: Automatic cleanup of low-relevance or outdated memories based on access patterns

10. **Custom Embeddings**: Support for user-provided embedding models or providers (Sentence Transformers, OpenAI, etc.)

11. **Memory Permissions**: Fine-grained access control for shared memory scenarios

### Implementation Notes

**Opt-In Philosophy**:
- Users must explicitly set `MEMORY_TYPE=mem0` or start the container to enable semantic memory
- Default behavior remains unchanged (InMemoryStore)
- Phase 0 improvements benefit ALL users automatically (no opt-in needed)

**Docker Compose as PRIMARY Deployment**:
- Mem0 requires PostgreSQL with pgvector extension for vector storage
- Single `docker run` approach won't work properly for production use
- Docker Compose file includes:
  - PostgreSQL 15 with pgvector
  - mem0 server with proper dependencies
  - Health checks for both services
  - Volume mounts for data persistence
- Quickstart `docker run` documented as best-effort alternative (limitations noted)

**Async Operations (CRITICAL)**:
- **MUST use `httpx.AsyncClient`** for all mem0 HTTP operations
- Avoid blocking the event loop with synchronous I/O
- Implement proper async/await patterns throughout Mem0Store
- Test async behavior explicitly (not just sync wrapped in async)

**Namespacing (First-Class Concern)**:
- User-level isolation via `mem0_user_id` (default: $USER or "default-user")
- Project-level isolation via `mem0_project_id` (optional, for multi-project scenarios)
- Namespace format: `"{user_id}:{project_id}"` or fallback to `"{user_id}"`
- All mem0 operations scoped to namespace to prevent data bleeding
- Tests MUST verify cross-namespace isolation (alice vs bob)

**Safety Gates**:
- Support `metadata: {save: false}` to prevent message storage
- Filter messages before sending to mem0 API
- Log filtered messages (redacted) for visibility
- Phase 3: Add pattern-based filters for common secrets (API keys, tokens, passwords)
- Document safe usage patterns in docs/design/usage.md

**Graceful Degradation**:
- If mem0 fails to initialize, fallback handled at factory level (not in Mem0Store)
- Log explicit warnings when falling back to InMemoryStore
- Clear error messages for common issues (Docker not running, endpoint unreachable, misconfiguration)
- Never crash the agent due to memory backend failure

**Context Bloat Prevention**:
- Cap `retrieve_for_context()` to k=5-10 results maximum
- Deduplicate results by semantic similarity to avoid near-duplicates
- Prefer concise snippets over full messages when possible
- Future: Implement token-aware limiting (`max_context_tokens`)

**Testing Strategy**:
- Phase 0: Unit tests for `retrieve_for_context()` (InMemoryStore, MemoryContextProvider)
- Phase 1: Config tests, health check tests (mocked), Docker Compose lifecycle tests
- Phase 2: Unit tests for Mem0Store (mocked client - FAST), integration tests (real Docker stack - SLOW)
- Phase 3: Performance benchmarks, end-to-end validation, security review

**Performance Targets**:
- `add()`: <10ms average (batch of 100 messages)
- `search()`: <200ms (with 1000 memories in store)
- `retrieve_for_context()`: <150ms (combined search + formatting)
- Memory overhead: <50MB for 1000 memories
- Health checks: <30ms timeout (keep CLI snappy)
- Log warnings for operations >500ms (slow query alert)

**Standardized Result Schema**:
Define cross-backend schema for memory results to enable debugging and ensure consistency:
```python
{
    "id": str,  # Unique memory ID
    "role": str,  # user, assistant, system, tool
    "content": str,  # Message content
    "timestamp": str,  # ISO 8601 format
    "metadata": dict,  # Arbitrary metadata
    "score": float | None,  # Optional: relevance score (for search results)
    "source": str | None,  # Optional: backend identifier (for debugging)
}
```
- InMemoryStore: Populate required fields, omit `score`/`source`
- Mem0Store: Populate all fields including `score` from semantic search
- ContextProvider: Uses only required fields for compatibility

**Message Filtering**:
- **Default behavior**: Only store `user` and `assistant` messages
- **Exclude by default**: `system`, `tool`, `thinking`, or internal messages
- **Rationale**: Reduces noise, improves relevance, prevents tool output leakage
- **Override**: Set `metadata: {force_save: true}` to store non-user/assistant messages
- **Configuration**: `MEMORY_FILTER_SYSTEM_MSGS=true` (default)
- **Example filtering logic**:
  ```python
  def should_save_message(msg: dict) -> bool:
      # Explicit opt-out
      if msg.get("metadata", {}).get("save") is False:
          return False

      # Explicit opt-in overrides filters
      if msg.get("metadata", {}).get("force_save") is True:
          return True

      # Default: only user/assistant
      return msg.get("role") in ("user", "assistant")
  ```

**Tuning Knobs (Configuration)**:
Add config knobs for precision/recall and context cost tuning:
- `MEMORY_RETRIEVAL_TOP_K`: Max results from `retrieve_for_context()` (default: 10, range: 1-50)
- `MEMORY_RETRIEVAL_MIN_SCORE`: Minimum similarity score for semantic search (default: 0.5, range: 0.0-1.0)
- `MEMORY_SNIPPET_MAX_CHARS`: Max characters per memory snippet for context (default: 500, 0=unlimited)
- `MEMORY_FILTER_SYSTEM_MSGS`: Filter out system/tool messages (default: true)
- Users can tune these based on model context window, cost sensitivity, and precision needs

**Resilience Mechanisms**:
- **Circuit Breaker**: After N consecutive failures (default: 5), stop calling mem0 for M seconds (default: 60)
  - Prevents cascade failures and reduces latency during outages
  - Logs when circuit opens/closes
  - Automatically attempts recovery after timeout
- **Fast Health Checks**: `check_mem0_endpoint()` with <30ms timeout to keep CLI responsive
- **Retry with Backoff**: Exponential backoff for transient failures (max 3 retries, 100ms → 400ms → 1.6s)
- **Timeouts**: All mem0 operations timeout after 5 seconds (configurable via `MEM0_REQUEST_TIMEOUT`)

**Telemetry Privacy**:
- **Respect `enable_sensitive_data` flag** from observability config
- When `enable_sensitive_data=false`:
  - Log counts and timings only (`memory.add count=5 duration=12ms`)
  - Strip message content from spans and logs
  - Redact queries in search spans (`query=[REDACTED]`)
- When `enable_sensitive_data=true`:
  - Include content snippets in spans (first 100 chars)
  - Log full queries for debugging
- Never log API keys or credentials regardless of flag

**Operability Commands** (Phase 3):
Add lightweight debugging commands to `/memory` CLI:
- `/memory list [limit]`: Show recent memories with IDs and previews
- `/memory search <query>`: Interactive search with relevance scores
- `/memory forget <id>`: Delete specific memory by ID
- `/memory export [file]`: Export all memories to JSON (default: stdout)
- **Rationale**: Helps users inspect and control what's being injected into context
- **Privacy**: Redact content if `enable_sensitive_data=false`

### Architectural Decisions

**Why mem0?**
- Provides vector embeddings, entity extraction, and knowledge graphs out-of-the-box
- Reduces custom implementation complexity (no need to build vector search from scratch)
- Supports both self-hosted and cloud deployment (aligns with agent-base's flexibility philosophy)
- Active development and Python SDK support
- Production-ready with proper database backing (PostgreSQL + pgvector)

**Why Docker Compose as PRIMARY?**
- Mem0 requires PostgreSQL with pgvector extension for production use
- Single container approach doesn't provide persistent vector storage
- Docker Compose ensures:
  - Proper service dependencies (DB → mem0)
  - Health checks for both services
  - Data persistence via volumes
  - Easier troubleshooting (logs for each service)
- Mirrors production deployment architecture
- Best-effort `docker run` alternative documented with clear limitations

**Why retrieve_for_context() API?**
- Provides abstraction for context retrieval strategies:
  - InMemoryStore: keyword-based search (Phase 0)
  - Mem0Store: semantic similarity search (Phase 2)
- Enables immediate value (Phase 0) without waiting for mem0 integration
- Maintains storage-backend agnosticism (no mem0-specific logic in ContextProvider)
- Future-proof for other backends (Redis, Elasticsearch, etc.)
- Clean separation: framework integration (ContextProvider) vs storage backends (MemoryManager)

**Why factory pattern?**
- Existing `create_memory_manager()` makes backend swapping transparent to consumers
- Adding mem0 requires only updating factory routing, no changes to `Agent` or call sites
- Fallback logic centralized in one place (factory, not scattered across codebase)
- Enables A/B testing of backends (easy to switch via config)

**Why graceful fallback?**
- Production agents must remain functional when optional services fail
- Falling back to `InMemoryStore` ensures conversations continue
- Clear logging notifies users of degraded functionality (not silent failure)
- Prevents cascade failures (memory backend down ≠ entire agent down)

**Why namespace by user + project?**
- User-level namespacing prevents data bleeding between users in multi-user deployments
- Project-level namespacing enables workspace isolation (e.g., different clients, different projects)
- Format `"{user_id}:{project_id}"` provides logical hierarchy
- Default `mem0_user_id` to `$USER` or `"default-user"` for single-user scenarios
- Optional `mem0_project_id` for advanced use cases

**Why async httpx.AsyncClient?**
- Agent framework is async-first architecture
- Blocking I/O would degrade performance and responsiveness
- httpx provides async interface compatible with mem0 HTTP API
- Connection pooling reduces overhead for repeated operations
- Non-blocking enables concurrent memory operations if needed

**Why safety gates (metadata: {save: false})?**
- Prevents accidental storage of sensitive data (API keys, credentials, secrets)
- User-controlled opt-out mechanism (explicit metadata flag)
- Complements pattern-based filters (defense in depth)
- Enables safe handling of tool outputs that may contain secrets
- Documented pattern encourages security-conscious development

**Why default implementation for retrieve_for_context()?**
- **Backward compatibility**: Custom backends don't break when interface adds new method
- **Sensible fallback**: Default composes `search()` + `get_recent()` for reasonable behavior
- **Opt-in optimization**: Backends can override for specialized semantic retrieval
- **DRY principle**: Shared logic in base class, specialization in subclasses
- Example: New backend can inherit default, only override `search()` for custom matching

**Why standardized result schema?**
- **Cross-backend consistency**: ContextProvider works identically with all backends
- **Debugging aid**: Optional `score` and `source` fields help diagnose relevance issues
- **Future-proof**: Schema extensible without breaking existing consumers
- **Type safety**: Clear contract for memory results across the system
- InMemoryStore can omit optional fields, Mem0Store can populate them

**Why filter system/tool messages by default?**
- **Noise reduction**: System prompts and tool outputs pollute semantic search space
- **Relevance improvement**: User-assistant conversations are the valuable signal
- **Privacy**: Tool outputs may contain sensitive data or implementation details
- **Context efficiency**: Reduces irrelevant memories injected into LLM context
- **Override available**: `metadata: {force_save: true}` for special cases

**Why tuning knobs (TOP_K, MIN_SCORE, MAX_CHARS)?**
- **Precision/recall control**: Users can tune for accuracy vs coverage
- **Context cost management**: Snippet limits reduce token usage for cost-sensitive deployments
- **Model compatibility**: Different models have different context windows (8K vs 128K)
- **Performance tuning**: Lower TOP_K = faster retrieval, higher MIN_SCORE = fewer false positives
- **Use case flexibility**: Research assistants (high recall) vs chatbots (high precision)

**Why circuit breaker?**
- **Fail-fast during outages**: Prevents repeated timeout waits when mem0 is down
- **Latency protection**: CLI stays responsive during backend failures
- **Automatic recovery**: Retries after cooldown period without manual intervention
- **Graceful degradation**: System continues with InMemoryStore fallback
- **Operational visibility**: Logs circuit state changes for monitoring

**Why fast health checks (<30ms)?**
- **CLI responsiveness**: `agent --check` should be instant, not block for seconds
- **Startup speed**: Don't delay agent initialization for health check
- **User experience**: Fast feedback loop for troubleshooting
- **Production SLAs**: Health checks shouldn't impact primary operations
- **Network tolerance**: Timeout before slow networks become problematic

**Why respect enable_sensitive_data flag?**
- **Compliance**: Some deployments prohibit logging user content (GDPR, HIPAA)
- **Existing pattern**: Observability already uses this flag consistently
- **Security**: Prevents accidental leakage of secrets in logs/traces
- **Debugging tradeoff**: Operators can enable for troubleshooting, disable for production
- **Zero config**: Works automatically with existing observability settings

**Why operability commands (list/search/forget/export)?**
- **Transparency**: Users can see what the agent "remembers" about them
- **Control**: Users can delete specific unwanted memories
- **Debugging**: Developers can inspect why irrelevant context is being injected
- **Trust**: Transparency builds user confidence in semantic memory
- **Data portability**: Export enables backup, migration, analysis

### Framework Integration Validation

**Reference**: [Microsoft Agent Framework - Memory Tutorial](https://learn.microsoft.com/en-us/agent-framework/tutorials/agents/memory?pivots=programming-language-python)

The Microsoft Agent Framework documentation demonstrates the native `ContextProvider` pattern for memory integration. **Our existing architecture already implements this pattern correctly**, validating our design approach:

**Existing Architecture (Already Correct)**:
```
Agent Framework ContextProvider (framework's abstract class)
    ↓
MemoryContextProvider (our implementation - src/agent/memory/context_provider.py)
    ↓
MemoryManager (our abstract interface - src/agent/memory/manager.py)
    ↓
InMemoryStore / Mem0Store (concrete storage backends)
```

**Key Validation Points**:

1. **Proper Framework Integration**: Our `MemoryContextProvider` correctly implements the two-phase invocation model:
   - `invoking()`: Injects memory context before LLM calls (lines 45-93)
   - `invoked()`: Stores messages after LLM responds (lines 95-151)

2. **Correct Abstraction Layer**: Mem0Store will be implemented at the `MemoryManager` level (storage backend), not the `ContextProvider` level (framework integration). This ensures:
   - Zero changes needed to `MemoryContextProvider`
   - Storage-backend agnosticism maintained
   - Clean separation of concerns

3. **Automatic Compatibility**: The existing `MemoryContextProvider` will automatically work with `Mem0Store` through the `MemoryManager` interface:
   - `memory_manager.get_all()` → will call `Mem0Store.get_all()`
   - `memory_manager.add(messages)` → will call `Mem0Store.add()`
   - `memory_manager.search(query)` → will call `Mem0Store.search()`

**Future Enhancement - Semantic Context Injection**:

Currently, `MemoryContextProvider.invoking()` retrieves ALL memories and slices the last N chronologically:
```python
all_memories = await self.memory_manager.get_all()
recent_memories = memories[-self.history_limit:]  # Last N messages
```

With semantic search capabilities, we could enhance this to retrieve the most RELEVANT memories:
```python
current_query = messages[-1].content if messages else ""
relevant_memories = await self.memory_manager.search(
    query=current_query,
    limit=self.history_limit
)  # Most semantically relevant N messages
```

**Recommendation**: Keep semantic context injection as a future enhancement (post-MVP). Initial implementation should maintain the current `get_all()` approach to avoid:
- Modifying `MemoryContextProvider` (increases scope/risk)
- Breaking storage-backend agnosticism
- Requiring mem0-specific logic in the framework integration layer

This enhancement can be added later once the basic Mem0Store implementation is validated and stable.
