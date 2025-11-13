# Changelog

## [0.2.1](https://github.com/danielscholl/agent-base/compare/agent-template-v0.2.0...agent-template-v0.2.1) (2025-11-13)


### Features

* add GitHub Models provider integration ([f0b8e64](https://github.com/danielscholl/agent-base/commit/f0b8e64fd467e7b1319e90daebbfdcd0344d978d))
* **cli:** add telemetry guards, perf timing, and history rotation ([f935c0c](https://github.com/danielscholl/agent-base/commit/f935c0c30dfb650a02c8d7c7d87a0a7ef28a0404))
* **config:** add auto-setup for local docker model runner ([399d453](https://github.com/danielscholl/agent-base/commit/399d453291e37407d4ef6dd0033dd023de386c01))
* **config:** add progressive minimal config JSON and loading ([f1ed62f](https://github.com/danielscholl/agent-base/commit/f1ed62f283dd105f89028816e7ecc449d1ccf213))
* **config:** comprehensive configuration system improvements ([ed8a5f6](https://github.com/danielscholl/agent-base/commit/ed8a5f66956ebe0ce6c6cbbe9c68340153fcf7a3))
* **config:** enable local provider by default ([086836d](https://github.com/danielscholl/agent-base/commit/086836de492b46821cdf95b7f08632aef3c67168))
* **config:** enable local provider by default and add validation ([32b4704](https://github.com/danielscholl/agent-base/commit/32b4704a690708c1adfdfe1fea751291e15b830b))
* **config:** file-based configuration system ([4bcea4c](https://github.com/danielscholl/agent-base/commit/4bcea4c77c83547eaee9b525dd9d7a1224782d67))
* **config:** implement model_dump_json_minimal and minimal saves ([f1ed62f](https://github.com/danielscholl/agent-base/commit/f1ed62f283dd105f89028816e7ecc449d1ccf213))
* **config:** introduce file-based configuration with CLI and schema ([e90a72a](https://github.com/danielscholl/agent-base/commit/e90a72a50222a88397ed1e6c3b0e51210c4042fd))
* **config:** introduce timeout constants and api key masking ([14df3eb](https://github.com/danielscholl/agent-base/commit/14df3eb34ff4bc80915c9f3af3c7a7c9a011399f))
* **docker/mem0:** switch mem0 deployment to qdrant ([0e7ee62](https://github.com/danielscholl/agent-base/commit/0e7ee6246055e87cf1abfeac7c08c774c575442b))
* enhance mem0 integration with sensitive data scrubbing and health checks ([b52ba0f](https://github.com/danielscholl/agent-base/commit/b52ba0f9444f916499e82ddb0b586ca5c630925e))
* **github:** add GitHub Models provider ([45453fa](https://github.com/danielscholl/agent-base/commit/45453fab37312188c130f9f3d9c68cc61a629657))
* **github:** adopt OpenAI-compatible API for GitHub provider ([ca8293a](https://github.com/danielscholl/agent-base/commit/ca8293afca2635134f541b4e47831185ee9a2e0a))
* **github:** adopt OpenAI-compatible API for GitHub provider ([42f0cdb](https://github.com/danielscholl/agent-base/commit/42f0cdb656eebe771c6ca6640bedfbc842dc7838))
* **mem0:** add mem0 endpoint check and client factory ([96b460c](https://github.com/danielscholl/agent-base/commit/96b460cf7a81c856b09cb53dc1e51a916415417b))
* **mem0:** add mem0 health checks and deployment hints in CLI ([4edd082](https://github.com/danielscholl/agent-base/commit/4edd082b6bbd31249cd1275a5e99ff1299f44fb1))
* **mem0:** add mem0 semantic memory management ([1228d79](https://github.com/danielscholl/agent-base/commit/1228d790c64d98bddb8c44cec3d9f10ea75a914c))
* **mem0:** implement HTTP health check for mem0 endpoint ([73dbbb4](https://github.com/danielscholl/agent-base/commit/73dbbb4cacaad7fa0ffa74a8ce4c9e37131ceb21))
* **mem0:** integrate mem0 memory backend for cloud/local modes ([69e9079](https://github.com/danielscholl/agent-base/commit/69e907939d5adeef7eed9e97b219a01128ac916f))
* **mem0:** integrate mem0 semantic memory with non-blocking IO ([4edd082](https://github.com/danielscholl/agent-base/commit/4edd082b6bbd31249cd1275a5e99ff1299f44fb1))
* **mem0:** switch to ephemeral storage in docker-compose ([0ce295f](https://github.com/danielscholl/agent-base/commit/0ce295fa1dc84db031a707898d688fb90741a648))
* **mem0:** unify mem0 memory backend creation via Memory.from_config ([cd9c7d0](https://github.com/danielscholl/agent-base/commit/cd9c7d0e00db5f979bf7c4197355d73ffde0eaac))
* **memory:** add Mem0Store semantic memory backend ([5897f9b](https://github.com/danielscholl/agent-base/commit/5897f9b0a544dfe5654db9521cf5e9a9ffe4d487))
* **memory:** enhance mem0 implementation with security and robustness improvements ([3616fa3](https://github.com/danielscholl/agent-base/commit/3616fa35f3ab34d6e66b34fce05218b96935e3ae))
* **memory:** integrate Mem0-based in-process memory store ([dd59093](https://github.com/danielscholl/agent-base/commit/dd59093a7ae01f2db74dd01bdf5e91f836609f2d))
* **memory:** introduce mem0 semantic memory scaffolding and config ([8f46280](https://github.com/danielscholl/agent-base/commit/8f46280a0c12b4a307d0eee4e0739fac9d35db34))


### Bug Fixes

* **mem0:** require OPENAI_API_KEY for local LLM and use gpt-4o-mini ([3c1b841](https://github.com/danielscholl/agent-base/commit/3c1b8410004408e6649479f6ce7fc4e927fc635f))


### Code Refactoring

* **config:** disable default providers by default and tidy output ([981d10f](https://github.com/danielscholl/agent-base/commit/981d10f70c79fc10aa6b6e756c7ef529810e3dd0))
* **config:** standardize env key messaging and precedence docs ([f2aada9](https://github.com/danielscholl/agent-base/commit/f2aada939fd2a7e4324b40662b87ca31c899e68f))
* **config:** tidy imports and improve messaging in config flow ([fd254c7](https://github.com/danielscholl/agent-base/commit/fd254c7a7aabcfa433155d141c6400904778ed6f))
* **mem0:** relax mem0 validation to allow api key only ([89b7559](https://github.com/danielscholl/agent-base/commit/89b7559de8caf57590734a25b0d80552242e965a))
* **mem0:** standardize utc usage and clean up messages ([c18f997](https://github.com/danielscholl/agent-base/commit/c18f9970822fb984c97579427e36009ccd32574f))
* **memory:** conditionally export Mem0Store when available ([7298e0e](https://github.com/danielscholl/agent-base/commit/7298e0e38ba2245ea84eb87e60bcd3c1fd31b0e8))


### Tests

* **cli:** clear git branch cache in toolbar tests for determinism ([41cbd3a](https://github.com/danielscholl/agent-base/commit/41cbd3a23a854d79329e6f4172b5f3ac0b6cba79))
* **config:** add tests for minimal config and provider connectivity optimization ([f1ed62f](https://github.com/danielscholl/agent-base/commit/f1ed62f283dd105f89028816e7ecc449d1ccf213))
* **config:** prevent dotenv loading in tests to avoid env file ([41cbd3a](https://github.com/danielscholl/agent-base/commit/41cbd3a23a854d79329e6f4172b5f3ac0b6cba79))
* **config:** update integration test to expect default local provider enabled ([8464e09](https://github.com/danielscholl/agent-base/commit/8464e09f9859cf65a108ceac349ddbfcc64f8c46))
* **mem0:** update mem0 store tests to expect filters usage ([4edd082](https://github.com/danielscholl/agent-base/commit/4edd082b6bbd31249cd1275a5e99ff1299f44fb1))
* **tests:** stabilize tests with env and cache resets ([41cbd3a](https://github.com/danielscholl/agent-base/commit/41cbd3a23a854d79329e6f4172b5f3ac0b6cba79))


### Continuous Integration

* enable CodeQL and CI on release-please branches ([00adccc](https://github.com/danielscholl/agent-base/commit/00adccca783f366c168fdac1f755f441b7657712))
* **workflows:** extend trigger branches for release-please patterns ([bb06dbb](https://github.com/danielscholl/agent-base/commit/bb06dbb29c05f295317b478c2df91ccb8c4defe8))


### Miscellaneous

* **config:** set default providers.enabled to [] ([3f32145](https://github.com/danielscholl/agent-base/commit/3f3214546bd640689b7003221e384b63b34b4bd9))
* **contributing:** remove legacy .env.example and update docs ([6d90810](https://github.com/danielscholl/agent-base/commit/6d90810471ee162ec9be3eba25fb39d09a293723))
* **deps:** update uv.lock for azure-ai-inference dependency ([47c3ce6](https://github.com/danielscholl/agent-base/commit/47c3ce67a722ec8ce03bfe8a79566a9b3c62586d))
* **memory:** note Mem0Store is optional if mem0ai is unavailable ([76d6c7d](https://github.com/danielscholl/agent-base/commit/76d6c7dd4ede67a11774a7d2cd16741445d75203))
* **pyproject:** extend omit list to exclude config_commands.py and editor.py ([45a50ef](https://github.com/danielscholl/agent-base/commit/45a50ef2ad890468b4583b37810e65068791a2c3))

## [0.2.0](https://github.com/danielscholl/agent-base/compare/agent-template-v0.1.0...agent-template-v0.2.0) (2025-11-11)


### ⚠ BREAKING CHANGES

* **foundation:** Requirements.md restructured to v3.0 separating foundation requirements (complete) from vision/future capabilities. This marks the v1.0.0 MVP release of agent-base as production-ready infrastructure for building agents.

### Features

* Add Google Gemini provider support ([e28d5cc](https://github.com/danielscholl/agent-base/commit/e28d5cc4978ac7032acdb5ef4b2e8659cf9e6043))
* add local docker provider support and UI improvements ([fa56c41](https://github.com/danielscholl/agent-base/commit/fa56c4177a5f1f30df0f11e597cb01cb878358ee))
* **agent:** add core agent with toolsets and CLI ([7b3dde7](https://github.com/danielscholl/agent-base/commit/7b3dde7fbaee402e06c4297959d47f748318c7db))
* **agent:** add visualization and session persistence for agent ([d4f19fb](https://github.com/danielscholl/agent-base/commit/d4f19fbd21638176d9fb84b67e35ddf1a3eb090e))
* **agent:** implement four-tier system prompt loading with env override ([a8f5884](https://github.com/danielscholl/agent-base/commit/a8f5884ed9a8f34e499d4f256e19aab0eec68dc6))
* **agent:** normalize provider responses in run and run_stream ([f57e963](https://github.com/danielscholl/agent-base/commit/f57e9636f764e8c3e3c1ea1e6dc3c7fd3bdf45a9))
* **cli:** add Local and Gemini providers to test matrix ([2c93ddb](https://github.com/danielscholl/agent-base/commit/2c93ddb56c1cbd326ccb757a8b68c20027c13fc1))
* **cli:** add persistent bottom toolbar status bar ([58ea5ae](https://github.com/danielscholl/agent-base/commit/58ea5aec4fc0fa5f43b26c31a4c39ef935fd4a9f))
* **cli:** add provider connectivity health checks ([b2cc9dd](https://github.com/danielscholl/agent-base/commit/b2cc9dd7d8d1e16333b27efa00a829afb3de5d50))
* **cli:** add quiet mode for prompt response output ([72213e3](https://github.com/danielscholl/agent-base/commit/72213e3d6ab03b1da509a8b0cfe933735d99d49e))
* **cli:** implement provider and model overrides via CLI ([0f12626](https://github.com/danielscholl/agent-base/commit/0f12626232ce21c470ce95c36484ec811623489c))
* **cli:** streamline single-prompt output and remove quiet flag ([6c45c18](https://github.com/danielscholl/agent-base/commit/6c45c18658113ef6a17bb950ae1b097fe21c21c2))
* **config:** default llm provider to local ([06b9859](https://github.com/danielscholl/agent-base/commit/06b98592a9121a6f52ebdae5e4db23333c08671b))
* **config:** enable memory by default for conversation memory ([30cf9c0](https://github.com/danielscholl/agent-base/commit/30cf9c0043b6c5c8f8899206fa06dc7f05bddd93))
* **gemini:** add DEFAULT_GEMINI_MODEL as default ([1f35f4c](https://github.com/danielscholl/agent-base/commit/1f35f4c22898ed9a1986cd1cea71acca7a3e50c9))
* **gemini:** add google Gemini provider integration ([144790c](https://github.com/danielscholl/agent-base/commit/144790c191798a7a855cbf818b953c3bf18feecf))
* **local:** add local docker provider for docker models ([49d776a](https://github.com/danielscholl/agent-base/commit/49d776a88393bb24fe06df70accf9f36dcdda8f3))
* **local:** implement local Docker model provider with ai/phi4 ([6f758ff](https://github.com/danielscholl/agent-base/commit/6f758ffac6ce00e62ffe99192bb67212487fe19c))
* **logging:** enhance logging suppression for Azure connectivity tes… ([750c49f](https://github.com/danielscholl/agent-base/commit/750c49f8d11f3cb2499ce1bd73d94588d63d5b06))
* **logging:** enhance logging suppression for Azure connectivity tests and add unit tests ([7c0dab8](https://github.com/danielscholl/agent-base/commit/7c0dab8f4ac99bd303aa914c23bfc170a6555ce8))
* **memory:** enable conversation memory by default ([4458175](https://github.com/danielscholl/agent-base/commit/4458175df771afeb7ca29a55008ac1f938076937))
* **memory:** implement in-memory memory management and context provider ([b9738dd](https://github.com/danielscholl/agent-base/commit/b9738ddf7e98a8fbf241e0e4404b070629b56cd1))
* **observability:** implement auto-detection for telemetry endpoint availability ([2cfce8c](https://github.com/danielscholl/agent-base/commit/2cfce8cfe1a4ef3d965151cd418107010ef3e00f))
* **otel:** implement OpenTelemetry observability integration ([5487a7e](https://github.com/danielscholl/agent-base/commit/5487a7e94eaf05b808ee6c46fe52915300560d76))
* **provider:** add multi-provider LLM support (openai/anthropic/azure) ([46cca5d](https://github.com/danielscholl/agent-base/commit/46cca5df549f69b51802b4d9c458c593aae7308b))
* **purge:** granular purge of sessions, memory, logs, and metadata ([8db1a9d](https://github.com/danielscholl/agent-base/commit/8db1a9d2abd08009a503e36ae25dc529b3550c22))
* **session:** implement per-session logging for CLI ([a37935e](https://github.com/danielscholl/agent-base/commit/a37935ec98609eb2d860dd6e2326882eec46acbc))
* **system-prompt:** implement three-tier configurable system prompt loading ([4b4a6ea](https://github.com/danielscholl/agent-base/commit/4b4a6ea45e68f077b2281afada4c3e14b66136e7))
* **telemetry:** add local observability dashboard support ([203ce17](https://github.com/danielscholl/agent-base/commit/203ce1742b29bff14c969a716d62c8e69546011c))
* **tests:** introduce comprehensive test framework and llm scaffolding ([2d4063f](https://github.com/danielscholl/agent-base/commit/2d4063fa838558c683a4052aa314ec1c5ed67414))


### Bug Fixes

* **agent:** improve system prompt loading ([fef817b](https://github.com/danielscholl/agent-base/commit/fef817b7ef20047eeb6f576f0b9b4e5708bea029))
* **agent:** pass middleware as a list to chat_client ([99263c3](https://github.com/danielscholl/agent-base/commit/99263c3486b19ba65eb7c13012af47e188f4318f))
* **cli:** avoid extra newline before first prompt in chat mode ([84f92c7](https://github.com/danielscholl/agent-base/commit/84f92c7a6e21914a295816f3ce76a46c8eb4bda2))
* **cli:** correct non-empty directory checks in purge ([f286610](https://github.com/danielscholl/agent-base/commit/f286610e77664913aceb65738e1f394630024e4e))
* **cli:** disable Rich auto-highlighting for Python version and platform ([7093950](https://github.com/danielscholl/agent-base/commit/7093950e053cdf0e1d228d12e9d66f7b851f575e))
* **cli:** enhance telemetry command feedback based on ENABLE_OTEL environment variable ([2cfce8c](https://github.com/danielscholl/agent-base/commit/2cfce8cfe1a4ef3d965151cd418107010ef3e00f))
* **cli:** improve agent --check display and logging ([2b0a843](https://github.com/danielscholl/agent-base/commit/2b0a843587f2ce7c0d9cec1aa72c75ae993e4ca8))
* **cli:** suppress middleware ERROR logs during provider connectivity tests ([1651dbf](https://github.com/danielscholl/agent-base/commit/1651dbf40117a5d8a30ea52d996c84db7bddd0c2))
* **cli:** update purge command output messages for clarity ([2cfce8c](https://github.com/danielscholl/agent-base/commit/2cfce8cfe1a4ef3d965151cd418107010ef3e00f))
* **config:** update Azure OpenAI API version to 2025-03-01-preview ([05f473c](https://github.com/danielscholl/agent-base/commit/05f473cb6491050bce70912337709442d3198d25))
* **config:** update Azure OpenAI API version to 2025-03-01-preview ([7616983](https://github.com/danielscholl/agent-base/commit/76169838aa978d4b8f2421fe64c93fee6007bf8a))
* resolve CodeQL security issues ([331b0c3](https://github.com/danielscholl/agent-base/commit/331b0c37c618aa6c3d47e9b1469b3f891623819f))


### Documentation

* add archon docs, adr templates, and foundation spec ([19eabb3](https://github.com/danielscholl/agent-base/commit/19eabb31c7155bd393b39658d23e34425ba5055d))
* add copilot-instructions.md with guidelines ([3d3eb43](https://github.com/danielscholl/agent-base/commit/3d3eb43dc750b699796283b42e3e74931af0c1eb))
* add GitHub Copilot instructions and setup workflow ([95e5eb8](https://github.com/danielscholl/agent-base/commit/95e5eb8f2a9d5071755c78094714b26df524f7b6))
* add interactive specs for phase 3 ([3a0b39d](https://github.com/danielscholl/agent-base/commit/3a0b39d3efed3d640d35c629e6b43dc3a23c3547))
* add uv tool upgrade command to README ([518efe2](https://github.com/danielscholl/agent-base/commit/518efe25edc80df214637b997b49e751227efb2b))
* **contrib:** overhaul contributing guidelines ([f913e9c](https://github.com/danielscholl/agent-base/commit/f913e9ce4c25600d9c4eb76a44d9d6f4e95b016e))
* **foundation:** restructure documentation for v1.0.0 foundation platform ([f315220](https://github.com/danielscholl/agent-base/commit/f315220d3c0869de8e5ad44fc999b20c66566ad1))
* **README:** enhance LLM providers section with clearer formatting a… ([e6b1df4](https://github.com/danielscholl/agent-base/commit/e6b1df4461166c599d11ab5020f6510bb57d2642))
* **README:** enhance LLM providers section with clearer formatting and prerequisites ([4674f79](https://github.com/danielscholl/agent-base/commit/4674f7990ff1853d98858d30f5e42aaae735282e))
* **readmes:** update contributing and tests readmes with uv run guidance ([3cf019c](https://github.com/danielscholl/agent-base/commit/3cf019cf4f7860f67480bae5946d2e0e825b4ee7))
* **readme:** update provider list and restructure LLM section ([3aa0f0f](https://github.com/danielscholl/agent-base/commit/3aa0f0f8e420c9fd9e630f0294e1df3cb118db86))
* **readme:** update wording to enterprise-grade features ([901e362](https://github.com/danielscholl/agent-base/commit/901e362b60ff8b150223ab4d6a7006fdf8ae2f61))
* remove redundant alias text from --config help ([acc850a](https://github.com/danielscholl/agent-base/commit/acc850a4a99cc7312b80efc436af970808165e71))
* **tests/llm:** update azure endpoint and deployment examples ([adccede](https://github.com/danielscholl/agent-base/commit/adcceded1096042624b4512d6bfbd576fb3fe2c5))
* update env.sample and readme to reflect local phi4 setup ([b1bb7ef](https://github.com/danielscholl/agent-base/commit/b1bb7ef43e9471d7bd756543e02ee6ae77ddd110))
* use 'agent' command in user docs, keep 'uv run agent' for contributors ([1e9ea14](https://github.com/danielscholl/agent-base/commit/1e9ea147d182673f1ece438a7513995a99713d2c))
* **validator:** rewrite docs to describe self-discovering tests ([2356717](https://github.com/danielscholl/agent-base/commit/235671707e8fbd7bfc35bf71c6ace5e1cf299bba))


### Code Refactoring

* **agent:** rename azure_ai_foundry to foundry across codebase ([db413f4](https://github.com/danielscholl/agent-base/commit/db413f4ae82098d36fdaa31b3f02d1b1f7ab9c7e))
* apply broad style and typing cleanup across codebase ([d1a64e7](https://github.com/danielscholl/agent-base/commit/d1a64e72952e34fdf46a150cf99239e1b1b33016))
* **cli:** modularize CLI into a package with dedicated modules ([e6a7933](https://github.com/danielscholl/agent-base/commit/e6a7933512c2a4199a132753af5877f4bc502b3e))
* **cli:** simplify prompt output by always printing response ([eccf54f](https://github.com/danielscholl/agent-base/commit/eccf54f3e8b2686ebafda7f6e801e56c432410d4))
* **config:** track explicit setting of ENABLE_OTEL in configuration ([2cfce8c](https://github.com/danielscholl/agent-base/commit/2cfce8cfe1a4ef3d965151cd418107010ef3e00f))
* **gemini:** adjust gemini chat client to keyword-only args ([500c5bb](https://github.com/danielscholl/agent-base/commit/500c5bb24ef560a6f699a7a0437d088127f3052b))
* **gemini:** extract call_id mapping to function name into helper ([0b1bd82](https://github.com/danielscholl/agent-base/commit/0b1bd821beeec28aa70ac4e59b3d6203ff88f51f))
* **gemini:** reuse _build_call_id_mapping in options prep ([0b1bd82](https://github.com/danielscholl/agent-base/commit/0b1bd821beeec28aa70ac4e59b3d6203ff88f51f))
* **tests:** update agent validation config path and references ([7af251d](https://github.com/danielscholl/agent-base/commit/7af251d334869abb79ba4a97c1a10c0b3db6a09e))
* tighten error handling and add logger usage across modules ([611a670](https://github.com/danielscholl/agent-base/commit/611a670372093421bc1c7d93423650bac116e1a2))


### Tests

* **cli:** update status bar tests to expect string output ([362df23](https://github.com/danielscholl/agent-base/commit/362df235e6cb14ca19c9bab1ba31f2765cfd35ce))
* **cli:** use OSError instead of Exception in git exception test ([6394881](https://github.com/danielscholl/agent-base/commit/6394881868a3675a1c24ededaed65b851a576cb9))
* **conftest:** add requests import in conftest ([1a621c9](https://github.com/danielscholl/agent-base/commit/1a621c91644aea16cebc27b36a2099ece684b666))
* **conftest:** use gpt-5-mini as default azure_model_deployment ([532c086](https://github.com/danielscholl/agent-base/commit/532c08671030a4297c3d8d57cb619ce8c57b621b))
* **core:** add tests for agent response handling and system prompt fallback ([6651d5f](https://github.com/danielscholl/agent-base/commit/6651d5f462e64f0967475e42dae85d6e31fb03ea))
* **display:** remove lingering tasks cleanup in test_display_tree ([d9fd3eb](https://github.com/danielscholl/agent-base/commit/d9fd3ebd96fd47dc9063f2033a4cd033ab89d748))
* **gemini:** add tests for function result mapping in chat client ([5d38385](https://github.com/danielscholl/agent-base/commit/5d38385cce87aa71fa07970732da5e17f64976e9))
* **llm:** adjust error checks across llm tests ([a903f0c](https://github.com/danielscholl/agent-base/commit/a903f0c2f9d898bc679a4ebe88366700544b9fdf))
* **llm:** remove multi-turn conversation context tests ([857de77](https://github.com/danielscholl/agent-base/commit/857de77178b038a4ad8655b1acca1a044601ef5d))
* **middleware:** add tests for pydantic and non-dict args ([a6b72a0](https://github.com/danielscholl/agent-base/commit/a6b72a0933bb35baaa400bcde6fb83b17813e661))
* **persistence:** add tests for ThreadPersistence metadata handling ([4b01ae8](https://github.com/danielscholl/agent-base/commit/4b01ae8063cc983235159b08f2a691e41fc1e820))
* **tests:** add span context and memory persistence tests ([b501678](https://github.com/danielscholl/agent-base/commit/b501678626d215246d90665f7acb0b403a1119d1))
* **tests:** strip ANSI codes in test outputs and adjust checks ([4af0fc6](https://github.com/danielscholl/agent-base/commit/4af0fc6732d61bfa13d53a950b66e18fb5d1cef8))
* **validation:** streamline validation tests and CLI checks ([b9b4991](https://github.com/danielscholl/agent-base/commit/b9b4991158dc5e587cccdb2e353252d8481095c6))


### Continuous Integration

* **codeql:** configure CodeQL analysis with dedicated config ([b555b9b](https://github.com/danielscholl/agent-base/commit/b555b9b17f5160e23c179b9ce64a01e389ffacda))
* **copilot:** add copilot setup steps workflow ([3d3eb43](https://github.com/danielscholl/agent-base/commit/3d3eb43dc750b699796283b42e3e74931af0c1eb))
* **security:** add pull_request_target trigger for bot PRs ([6ffc653](https://github.com/danielscholl/agent-base/commit/6ffc653875f9f2baccd1180e8ee5c2ff7322f7a7))
* **security:** adjust workflow permissions and sbom naming ([d4c2ecc](https://github.com/danielscholl/agent-base/commit/d4c2ecce9a713c7dcef1971ab569cddc2b5d72a6))
* **security:** simplify pr workflow checkout and sbom naming ([1410853](https://github.com/danielscholl/agent-base/commit/14108539b4d2eb731f1fbe5ffdedf5b3bca65c70))
* **security:** update workflow for PR target handling ([0097e2e](https://github.com/danielscholl/agent-base/commit/0097e2e1cf892335c067da04318c8962a7be7466))
* **workflows:** enable parallel pytest runs in ci.yml ([d524045](https://github.com/danielscholl/agent-base/commit/d524045aeef024388e2076c1670b390907322b91))


### Miscellaneous

* **anthropic:** switch default model to claude-haiku-4-5-20251001 ([4426851](https://github.com/danielscholl/agent-base/commit/4426851a817cf4397b10d1fa38ca37499126c3b2))
* **claude:** remove deprecated claude command docs ([5a0add7](https://github.com/danielscholl/agent-base/commit/5a0add787de7d04a2d05943a03d9312db76ac70d))
* **conftest:** note default gpt-5-codex for azure deployment ([c1c7753](https://github.com/danielscholl/agent-base/commit/c1c7753f93928e1faba318fc6dd4f52e6cff3532))
* **deps:** bump the python-dev group with 3 updates ([1d0ccda](https://github.com/danielscholl/agent-base/commit/1d0ccdad4a110cf447f8a25317b8b99cd521e9d4))
* **deps:** bump the python-dev group with 3 updates ([596515a](https://github.com/danielscholl/agent-base/commit/596515a4a3705d6a04d92912f3cd3d765fe873ce))
* **deps:** bump the python-prod group with 2 updates ([2d9d233](https://github.com/danielscholl/agent-base/commit/2d9d23391cf017a35aa1bbb3835a2e71d96076bc))
* **deps:** bump the python-prod group with 2 updates ([57e90e7](https://github.com/danielscholl/agent-base/commit/57e90e7a5fddd46ea7ce7e6e45c58f2866ccc632))
* **deps:** configure Dependabot to use uv package manager ([dfa42c1](https://github.com/danielscholl/agent-base/commit/dfa42c137b6ad8ee8b7903bd38113a319727e2f9))
* **lockfile:** add uv.lock ([333c7b7](https://github.com/danielscholl/agent-base/commit/333c7b7a250a7fcf3bbbc3788223fc6a59146b70))
* **project:** rename repository to agent-base and update metadata ([08d8ab3](https://github.com/danielscholl/agent-base/commit/08d8ab3705ced94a9db2988ef36c6d23d7c1d08d))
