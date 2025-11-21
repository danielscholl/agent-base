# Changelog

## [0.3.0](https://github.com/danielscholl/agent-base/compare/agent-template-v0.2.9...agent-template-v0.3.0) (2025-11-21)


### ⚠ BREAKING CHANGES

* This release marks the 1.0.0 MVP milestone with consolidated configuration architecture. Removed .env.example in favor of comprehensive configuration documentation at docs/design/configuration.md. The codebase is production-ready with 85%+ test coverage, comprehensive documentation, and clear migration paths for future releases.

### Features

* **cli:** enhance error handling in interactive mode ([3dca36d](https://github.com/danielscholl/agent-base/commit/3dca36d44fd41eaa493f7567b113cd9c1f4e697f))
* **config:** add load_config_with_env to merge env vars into file config ([02bd160](https://github.com/danielscholl/agent-base/commit/02bd160a23181eb68d7fbc61a162b100b4fc2931))
* **config:** add system_prompt_file support across settings ([f4ad3b8](https://github.com/danielscholl/agent-base/commit/f4ad3b8021cf15873e248e54d504b26ccd088c1f))
* **config:** merge environment overrides into loaded settings ([4ccaff6](https://github.com/danielscholl/agent-base/commit/4ccaff6bc529cbc0f8d6d45819a51920f9c9d24b))
* **config:** support LOCAL_MODEL env var for local provider ([e5882c8](https://github.com/danielscholl/agent-base/commit/e5882c8d1ed44cbe2f1d51e9de2dcd7c9ee3fc07))
* **error:** implement provider error handling and messaging ([36762a1](https://github.com/danielscholl/agent-base/commit/36762a121d2e64c7231c91e047c72ba5d7efc84f))


### Bug Fixes

* **middleware:** replace AgentConfig.from_env() with load_config() ([422afbc](https://github.com/danielscholl/agent-base/commit/422afbca7b44e2be1f69f4c36d72c320c886c0b6))
* **middleware:** replace second AgentConfig reference with load_config() ([092efee](https://github.com/danielscholl/agent-base/commit/092efee6df7a58fe15b072d02cb8cd4c2340fa26))
* **tests:** rewrite integration LLM fixtures for new API ([73a9365](https://github.com/danielscholl/agent-base/commit/73a9365d062a59ea247a48307bc98a00320ef744))
* **tests:** rewrite test_memory_config.py for new API ([04a9cf9](https://github.com/danielscholl/agent-base/commit/04a9cf9e1ebc70178ce7c88428f9f7cf5bc45cf0))
* **tests:** rewrite test_memory_integration.py for new API ([de130ab](https://github.com/danielscholl/agent-base/commit/de130ab01a1412dc818b7517304611e571a27bd5))
* **tests:** update custom_prompt_config fixture references ([9bfbba1](https://github.com/danielscholl/agent-base/commit/9bfbba11764076cfe470f6b9603da89d48a73d0c))
* update Agent instantiation and add missing compatibility properties ([a9bef2f](https://github.com/danielscholl/agent-base/commit/a9bef2fc0230a11dcd0d2b5c8eb0787d244f2fa9))


### Code Refactoring

* **agent:** convert mem0 storage path to Path and add CONFIG_ERROR ([16e760e](https://github.com/danielscholl/agent-base/commit/16e760ed58634d0ce1b9c91aaf913870d3536e2d))
* **agent:** defer load_config import to runtime in health and session ([16e760e](https://github.com/danielscholl/agent-base/commit/16e760ed58634d0ce1b9c91aaf913870d3536e2d))
* **agent:** lazy-load config and normalize paths ([16e760e](https://github.com/danielscholl/agent-base/commit/16e760ed58634d0ce1b9c91aaf913870d3536e2d))
* align test builder with AgentSettings ([e265682](https://github.com/danielscholl/agent-base/commit/e26568287e50f97c114cc46f2e85482a8afa4b90))
* **config:** lazily import load_config to break circular imports ([a9428ea](https://github.com/danielscholl/agent-base/commit/a9428ea08e11dca7ab613558a9de7d1c90cb2579))
* **config:** migrate to AgentSettings across codebase ([33110d6](https://github.com/danielscholl/agent-base/commit/33110d66944af7e124fa0b0b50943d2a941e92fe))
* **tests:** migrate integration tests to AgentSettings API ([a0abd67](https://github.com/danielscholl/agent-base/commit/a0abd67bf2e68b6edf4fd91d8ba17439dbcf72a5))
* **tests:** switch observability setup tests to use load_config ([8264635](https://github.com/danielscholl/agent-base/commit/8264635a4653e8474ee5cd1a412a7796a0d7cd84))
* **tests:** switch tests to AgentSettings() and load_config ([5ebdadb](https://github.com/danielscholl/agent-base/commit/5ebdadbd522cf8f86ba843c5a9b3c9e9a5270f16))


### Tests

* **cli:** add config_from_env helper to apply env overrides in CLI arg tests ([cdf2c46](https://github.com/danielscholl/agent-base/commit/cdf2c46083c65bcceb70e12e877dc10455d48862))
* **config:** update get_model_display_name expectations to include prefixes ([0315ddd](https://github.com/danielscholl/agent-base/commit/0315ddde49be49c3e0f10a8e20d359d847cecc02))
* **config:** update tests to expect dict of env overrides ([43bf43b](https://github.com/danielscholl/agent-base/commit/43bf43befa39a127cc473f692c8e18f2c90320d8))
* **middleware:** mock load_config to supply provider settings ([5f63a5d](https://github.com/danielscholl/agent-base/commit/5f63a5d17c12a774a17deb03dbcfd279d21c4279))
* **middleware:** update trace logger tests to mock provider structure ([e0183f1](https://github.com/danielscholl/agent-base/commit/e0183f17e2e6a3f33bccfa5760f9a9673416c003))
* **test_integ:** update integration tests to use provider config API ([04bd944](https://github.com/danielscholl/agent-base/commit/04bd944b90d7fe3745f92983bc11dbf15bd725b8))
* **tests:** align AgentSettings tests with new provider layout ([3dca36d](https://github.com/danielscholl/agent-base/commit/3dca36d44fd41eaa493f7567b113cd9c1f4e697f))
* **tests:** mock config loading in agent and middleware tests ([7917623](https://github.com/danielscholl/agent-base/commit/7917623c597200120bbca9a9bf70570e689fd473))
* **tests:** update memory tests to use new nested provider config ([3dca36d](https://github.com/danielscholl/agent-base/commit/3dca36d44fd41eaa493f7567b113cd9c1f4e697f))


### Miscellaneous

* **config:** remove legacy configuration module ([5bc1356](https://github.com/danielscholl/agent-base/commit/5bc1356fadd6ae7b607ce60555f701400c84e5ab))
* prepare codebase for 1.0.0 MVP release ([0db170a](https://github.com/danielscholl/agent-base/commit/0db170a10204ab998bdf0df23ed9bc7ac37c7ffc))

## [0.2.9](https://github.com/danielscholl/agent-base/compare/agent-template-v0.2.8...agent-template-v0.2.9) (2025-11-21)


### Features

* add structured triggers to skills ([9e72a88](https://github.com/danielscholl/agent-base/commit/9e72a8806b6b2049c4966618ed6bbf9f81aa2bf3))
* **cli:** log error details when settings can't be loaded ([f92be71](https://github.com/danielscholl/agent-base/commit/f92be71ed819e9b5abcc93357c907f91dcf24a82))
* **docs:** represent triggers as dicts in documentation index ([f92be71](https://github.com/danielscholl/agent-base/commit/f92be71ed819e9b5abcc93357c907f91dcf24a82))
* **skills:** add progressive skill docs and dynamic context provider ([a8881a1](https://github.com/danielscholl/agent-base/commit/a8881a1adb0eb37c6616d42cd663f58f2b05de64))
* **skills:** implement explicit triggers for skill matching ([f92be71](https://github.com/danielscholl/agent-base/commit/f92be71ed819e9b5abcc93357c907f91dcf24a82))
* **skills:** implement progressive disclosure for skill documentation ([ca290d9](https://github.com/danielscholl/agent-base/commit/ca290d93b2112f43848802230b415733889a79a8))
* **skills:** implement three-state bundled skill enablement ([72a85c0](https://github.com/danielscholl/agent-base/commit/72a85c01ed76b270c467f5029a78e57e0a13887e))
* **tools:** implement two-tier tool docstring optimization ([27ededb](https://github.com/danielscholl/agent-base/commit/27ededb51de5131240a62c9cd786675cdbcfa3b7))
* **tools:** implement two-tier tool docstring optimization ADR-0017 ([146f8c4](https://github.com/danielscholl/agent-base/commit/146f8c4800d1fc95dda49aa766caa346b42a6960))
* **tools:** introduce token-aware tool metadata and listings ([c35d8d8](https://github.com/danielscholl/agent-base/commit/c35d8d8a064227c971a96715b913cacb5308d6ef))
* **trace:** extend llm trace logging with system_instructions ([23a49e4](https://github.com/danielscholl/agent-base/commit/23a49e456125354de29e181a73889d8ae9ea736e))
* **trace:** implement trace-level LLM logging with token analysis ([13ee547](https://github.com/danielscholl/agent-base/commit/13ee547ce2e12bcc08721e1ed10d0a033208a9b1))
* **trace:** implement trace-level LLM request/response logging ([275bcf9](https://github.com/danielscholl/agent-base/commit/275bcf9fb9c0b3e6255a2a9a0f5a19a722afd9cb))
* **triggers:** add structured triggers for skills and tests ([16e04e7](https://github.com/danielscholl/agent-base/commit/16e04e796afa6620503e0f3391ecd1a333279722))


### Bug Fixes

* **logging:** enable trace logging via log_level ([81baeed](https://github.com/danielscholl/agent-base/commit/81baeed494a826757d211a049df44b2d04f4e87d))
* **logging:** json dump for trace entries uses ensure_ascii=False ([81baeed](https://github.com/danielscholl/agent-base/commit/81baeed494a826757d211a049df44b2d04f4e87d))
* **middleware:** ensure trace log JSON serialization with default=str ([6aac27c](https://github.com/danielscholl/agent-base/commit/6aac27c7e93fc01b45bb3c3ed5f86ea98ed4db80))


### Documentation

* **skills:** document progressive disclosure and skills architecture ([ad7cd95](https://github.com/danielscholl/agent-base/commit/ad7cd95861b56e9c0e8da05ccd3f4f9b9a79dc11))
* **triggers:** add spec for structured skill triggers ([aeefdbe](https://github.com/danielscholl/agent-base/commit/aeefdbe599d79306fc91fe2de79e5cf638776990))


### Code Refactoring

* **agent:** extract model from config in middleware ([4405e66](https://github.com/danielscholl/agent-base/commit/4405e663a97e553effdefe900216b441b290458f))
* **middleware:** add type hints for trace logger and guard config ([2c9f84a](https://github.com/danielscholl/agent-base/commit/2c9f84a571332156d1da4c96d19f430d5aa72fb0))
* **middleware:** fix TYPE_CHECKING imports and forward refs ([6bf76b9](https://github.com/danielscholl/agent-base/commit/6bf76b902751d256450eebe944b3687c3d5ea682))
* **skills:** improve typing and imports in skills loading ([9d9ee55](https://github.com/danielscholl/agent-base/commit/9d9ee55c05f680a7f9b2177e7f83cdefa8b4abfd))


### Tests

* **middleware:** add tests for trace logging middleware ([81b36ad](https://github.com/danielscholl/agent-base/commit/81b36adbb96221d6669523f4694ebaeb477d5da0))
* **middleware:** update anthropic_model to deterministic value in tests ([81baeed](https://github.com/danielscholl/agent-base/commit/81baeed494a826757d211a049df44b2d04f4e87d))
* **middleware:** update trace logging tests to reflect new message API ([5c6b0cb](https://github.com/danielscholl/agent-base/commit/5c6b0cb378c3f5c4e67a9f46d204f751a22221cd))


### Miscellaneous

* remove model token count comments across tool modules ([de183be](https://github.com/danielscholl/agent-base/commit/de183beb0d0d5cec4b8d3254bc9b6cfcae32a38f))

## [0.2.8](https://github.com/danielscholl/agent-base/compare/agent-template-v0.2.7...agent-template-v0.2.8) (2025-11-20)


### Bug Fixes

* read version from package metadata instead of hardcoding ([dd1a54c](https://github.com/danielscholl/agent-base/commit/dd1a54c4feefca384c83fab72337e5c7cae7d6cc))
* read version from package metadata instead of hardcoding ([86fc680](https://github.com/danielscholl/agent-base/commit/86fc680a5323280fd75aa8c8e43742c43fa162a0))
* **skills:** remove Pydantic warning by renaming json parameter ([155cc01](https://github.com/danielscholl/agent-base/commit/155cc0133a2ce27838b95212803eb8391534ed5d))
* **skills:** remove Pydantic warning by renaming json parameter ([936f5b8](https://github.com/danielscholl/agent-base/commit/936f5b829c54fb0fb6288740cd86fcee4ea391ae))
* **skills:** resolve Windows file handle cleanup issue during skill installation ([9db5a2b](https://github.com/danielscholl/agent-base/commit/9db5a2b6bcae4aa68dcbc3322f7b5836e37cca50))
* **skills:** resolve Windows file handle cleanup issue during skill installation ([b3202d6](https://github.com/danielscholl/agent-base/commit/b3202d69454af78d9ee5dd453842701aab68e95a))
* use PackageNotFoundError instead of catching all exceptions ([5c382e0](https://github.com/danielscholl/agent-base/commit/5c382e0daae43182e0f7b1795831fbce6f211377))

## [0.2.7](https://github.com/danielscholl/agent-base/compare/agent-template-v0.2.6...agent-template-v0.2.7) (2025-11-20)


### Features

* add skill management commands for listing, installing, updating, removing, enabling, and disabling skills ([941ff21](https://github.com/danielscholl/agent-base/commit/941ff21680eee8cef3f9a497a60facb2cae99c15))
* **agent:** adopt package-based bundled skills detection ([7fbaa5f](https://github.com/danielscholl/agent-base/commit/7fbaa5f8b2be459f9a1f88e62e4bce133fdc90cc))
* **agent:** expose skill instruction token counts in agent ([1067d48](https://github.com/danielscholl/agent-base/commit/1067d482e941247688a58819a6e4d4c2a1b0e041))
* **agent:** extend skill loader return to include skill_instructions ([f732f71](https://github.com/danielscholl/agent-base/commit/f732f71ce5f99c997e6c1a6c0a4c148c37aefe8a))
* **agent:** implement AGENT_SKILLS env var for skill config ([871e317](https://github.com/danielscholl/agent-base/commit/871e317386cc71eb4f9bfd5f85ae2d08d9a55e68))
* **agent:** include bundled skills in package distribution ([bd9458b](https://github.com/danielscholl/agent-base/commit/bd9458b24fe46226948bf54f843a681e7a4bb293))
* **agent:** initialize skill_instructions in Agent ([f732f71](https://github.com/danielscholl/agent-base/commit/f732f71ce5f99c997e6c1a6c0a4c148c37aefe8a))
* **agent:** treat empty AGENT_SKILLS as disabled in legacy config ([f732f71](https://github.com/danielscholl/agent-base/commit/f732f71ce5f99c997e6c1a6c0a4c148c37aefe8a))
* **cli:** overhaul skill management with interactive UI ([1067d48](https://github.com/danielscholl/agent-base/commit/1067d482e941247688a58819a6e4d4c2a1b0e041))
* enhance tool configuration display to include core toolsets and skills ([941ff21](https://github.com/danielscholl/agent-base/commit/941ff21680eee8cef3f9a497a60facb2cae99c15))
* **filesystem:** add sandboxed filesystem toolset for Agent ([df72ddb](https://github.com/danielscholl/agent-base/commit/df72ddb54cf25e7c6e32d96515e2c052303385ac))
* **filesystem:** add sandboxed filesystem toolset with workspace configuration ([2f7877f](https://github.com/danielscholl/agent-base/commit/2f7877f47082026e166cb824ddf369dd67ee40f5))
* **filesystem:** harden path resolution and symlink checks ([6ae9089](https://github.com/danielscholl/agent-base/commit/6ae9089bcff858b3241fc81fd1b6d5d3fde82ae7))
* Progressive Disclosure Skill Architecture ([dc6254a](https://github.com/danielscholl/agent-base/commit/dc6254a0f673c7d1640c96580eba59e720ca8212))
* skills configuration optimization with plugin system ([907d4d4](https://github.com/danielscholl/agent-base/commit/907d4d47c99d7bbfdde439cd60260272e668654b))
* **skills:** add full skill system with loader and registry ([97c644e](https://github.com/danielscholl/agent-base/commit/97c644e94255d44f36a3bb9b0053125c12fcbec8))
* **skills:** Add marketplace structure support and fix update feature ([57d5d92](https://github.com/danielscholl/agent-base/commit/57d5d92d20e0dd70bd1f480583d6a817aa26362f))
* **skills:** support marketplace structure for skill installation ([b444b6a](https://github.com/danielscholl/agent-base/commit/b444b6adf018cb7a59dc9e4ccb507e72de62e416))
* **tokens:** add TOKENS_PER_WORD_ESTIMATE constant ([79f99af](https://github.com/danielscholl/agent-base/commit/79f99af92548ffd4a5a4ef8dc94f62456a7b800c))
* **utils:** add token counting utilities and integrate token tracking ([1067d48](https://github.com/danielscholl/agent-base/commit/1067d482e941247688a58819a6e4d4c2a1b0e041))
* **web-access:** add web-access skill with fetch and search scripts ([9cb1e1b](https://github.com/danielscholl/agent-base/commit/9cb1e1b13ded08b1a89f8b9fbd699f38897ed3c8))
* **web-access:** add web-access skill with fetch and search scripts ([944744e](https://github.com/danielscholl/agent-base/commit/944744e52a7138edf38148e31cbeb2194d034d09))


### Bug Fixes

* **filesystem:** fix glob pattern matching in search_text ([5cd9e47](https://github.com/danielscholl/agent-base/commit/5cd9e47d517c624e25f37c6d8a6b5208042b8079))
* **filesystem:** resolve mypy type errors and update agent tests ([a9cd86b](https://github.com/danielscholl/agent-base/commit/a9cd86b229be5430d55e627eab201e2af3007d9e))
* **skills:** gracefully handle None SHAs in update logging ([9a907d8](https://github.com/danielscholl/agent-base/commit/9a907d8784e43f5beb11d69a33fc4e000730796b))
* **skills:** require skills path to be a directory during marketplace scan ([25cebcb](https://github.com/danielscholl/agent-base/commit/25cebcb3f8c9859cee4b99fc0474ea5e5c99247c))
* **skills:** use entry.name for reinstall to preserve original casing ([25cebcb](https://github.com/danielscholl/agent-base/commit/25cebcb3f8c9859cee4b99fc0474ea5e5c99247c))


### Documentation

* **hello-ext:** update language example to use language code es ([dea75f8](https://github.com/danielscholl/agent-base/commit/dea75f8ead1f368161025f7918975bd30588c2e3))
* **README:** clarify skills description and their functionality ([8a1c990](https://github.com/danielscholl/agent-base/commit/8a1c990fea1fe376da1355f679975591bcf88e88))
* **readme:** simplify skills usage section ([2af7d3b](https://github.com/danielscholl/agent-base/commit/2af7d3ba2fedf015c3fcb142d13a68281c107341))
* **skills:** update skill management docs and examples ([003bab3](https://github.com/danielscholl/agent-base/commit/003bab32ad8d32c9257defb6128de62c42b42de4))


### Code Refactoring

* **agent/config:** replace TYPE_CHECKING import with pass ([0bef7d0](https://github.com/danielscholl/agent-base/commit/0bef7d04d1ee2ff45c0d54c135d5a52a9a8ddafd))
* **cli:** enhance skill display format and improve path retrieval logic ([78170fe](https://github.com/danielscholl/agent-base/commit/78170fef676355a7b253b28d8cc8f35ddf107951))
* **cli:** remove interactive skill_main_menu ([30e0a9f](https://github.com/danielscholl/agent-base/commit/30e0a9fed2569f090ed00744150e1f5fc962d1e6))
* **cli:** rename skill list to show and update documentation ([3c62ce6](https://github.com/danielscholl/agent-base/commit/3c62ce615c530fef83e43dcf7cf1e67fb7dcb705))
* **cli:** rename skill list to show and update references ([becfda5](https://github.com/danielscholl/agent-base/commit/becfda5d335573c34306256a69497d92c3de18e5))
* **config:** remove AGENT_SKILLS env var handling ([6e40d06](https://github.com/danielscholl/agent-base/commit/6e40d060a4d50807cf19c862a67efb0ff221f07d))
* improve exception handling in bundled skills detection ([7d01d06](https://github.com/danielscholl/agent-base/commit/7d01d06c07c4ee3c6b4def2bf65578342415781a))
* **kalshi-markets:** modernize type hints across scripts and registry ([62a0196](https://github.com/danielscholl/agent-base/commit/62a01962d7992ab32d5338b3acecf38422f82b4b))
* **legacy:** add typing and path handling for core_skills_dir ([7e465e0](https://github.com/danielscholl/agent-base/commit/7e465e037b7d8179889c8a3c85bce702f8bcfc98))
* restructure skill loading to support single-skill and monorepo installations ([941ff21](https://github.com/danielscholl/agent-base/commit/941ff21680eee8cef3f9a497a60facb2cae99c15))
* **skill:** add _MockConfig as empty config for SkillLoader ([2af7d3b](https://github.com/danielscholl/agent-base/commit/2af7d3ba2fedf015c3fcb142d13a68281c107341))
* **skills:** migrate to settings.skills config ([df7289a](https://github.com/danielscholl/agent-base/commit/df7289a4d5c883e07da9b2561e11724a538ea190))
* **tests:** add type hints and fix test import path ([e3bb887](https://github.com/danielscholl/agent-base/commit/e3bb88732ca43897173c0a758eff799336894442))
* update AgentConfig and SkillsConfig to streamline skill management ([941ff21](https://github.com/danielscholl/agent-base/commit/941ff21680eee8cef3f9a497a60facb2cae99c15))


### Tests

* **loader:** expand unit tests for SkillLoader behaviors ([4b50c2b](https://github.com/danielscholl/agent-base/commit/4b50c2bfe99300894654848563aa18b459590f72))
* **skills:** update tests for unordered installs and casing ([25cebcb](https://github.com/danielscholl/agent-base/commit/25cebcb3f8c9859cee4b99fc0474ea5e5c99247c))
* **skills:** use str(config.core_skills_dir) in assertion ([1640ccd](https://github.com/danielscholl/agent-base/commit/1640ccd58e6ca2fddf62a7fdc3d1a29c1f5eab54))


### Build System

* **deps:** add types-pyyaml type stubs for PyYAML ([5f0270c](https://github.com/danielscholl/agent-base/commit/5f0270c9c17518a93c3379a63535d8c13f578e3f))
* **pyproject:** omit tokens.py and skill_commands.py from packaging ([2af7d3b](https://github.com/danielscholl/agent-base/commit/2af7d3ba2fedf015c3fcb142d13a68281c107341))

## [0.2.6](https://github.com/danielscholl/agent-base/compare/agent-template-v0.2.5...agent-template-v0.2.6) (2025-11-15)


### Features

* **cli:** derive mem0 package source from uv-receipt.toml ([d98c4f7](https://github.com/danielscholl/agent-base/commit/d98c4f72cf30e05a4a7d41bbbb2eae486f9f4c3b))
* **config:** automatic mem0 dependency installation for uv tool environments ([aedc5b5](https://github.com/danielscholl/agent-base/commit/aedc5b5bbb133b0f9fd46e25aba472ff334770d4))
* **config:** enhance mem0 dependencies install with cross-OS uv tool ([8ac9b24](https://github.com/danielscholl/agent-base/commit/8ac9b2461caf42f1a4ccbfa5f0a84e7df2d9e185))
* **config:** implement mem0 dependency install path for uv tool ([4e68022](https://github.com/danielscholl/agent-base/commit/4e680220d23095bf173c34112026efc0059cd49b))

## [0.2.5](https://github.com/danielscholl/agent-base/compare/agent-template-v0.2.4...agent-template-v0.2.5) (2025-11-14)


### Features

* **telemetry:** auto-detect otlp endpoint to enable observability ([d3a4aa0](https://github.com/danielscholl/agent-base/commit/d3a4aa06d9eb0e5318219764a5020f8ce6f8fc43))


### Bug Fixes

* **telemetry:** restore auto-detection and fix observability initialization ([fba0e41](https://github.com/danielscholl/agent-base/commit/fba0e41f69af44e44e31d5b6425706e660c48b0b))
* **tests:** address copilot review feedback ([e417750](https://github.com/danielscholl/agent-base/commit/e417750eab04d118f14b07d7b8c5c5cb6a195378))

## [0.2.4](https://github.com/danielscholl/agent-base/compare/agent-template-v0.2.3...agent-template-v0.2.4) (2025-11-14)


### Features

* **config/providers:** introduce registry-based provider setup ([0851c11](https://github.com/danielscholl/agent-base/commit/0851c11f42897fef977b39218ce602d0d172c54b))
* **health:** extract health check into dedicated module ([790d69a](https://github.com/danielscholl/agent-base/commit/790d69a7eaa579b7d0477acc353b65453083346a))
* **mem0:** enhance mem0 integration with dependency checks and embedding model configuration ([8aa6ff9](https://github.com/danielscholl/agent-base/commit/8aa6ff918ad70974f54500a7ecef5da06de2ffe5))
* **mem0:** refine local health check and add provider embedding mappings ([29b5da3](https://github.com/danielscholl/agent-base/commit/29b5da31943f6d34861486f4f64d2a8f37be319e))


### Bug Fixes

* **health:** remove duplicate import of get_storage_path ([69d45b0](https://github.com/danielscholl/agent-base/commit/69d45b0b1eafa718cd4856bd85d80063d49c55df))
* **mem0:** fix memory persistence and improve dependency management ([1aacc75](https://github.com/danielscholl/agent-base/commit/1aacc75e0b56ce298d2cca0a2a5438cb1f6019dc))
* **providers:** address CodeQL and Copilot review comments ([ede0db1](https://github.com/danielscholl/agent-base/commit/ede0db137938874c3e8b2d1de16eb0b90c8bb2ae))
* **providers:** use modern type union syntax (X | Y) ([0de189a](https://github.com/danielscholl/agent-base/commit/0de189abd3b6c0510100724ef194f3f3999e54ba))


### Code Refactoring

* **cli:** add set_model_span_attributes and centralized _execute_query ([d365a8a](https://github.com/danielscholl/agent-base/commit/d365a8a19dda48ba2393d73be2f457f3465e1dc4))
* **cli:** extract health check to dedicated module ([655fc3c](https://github.com/danielscholl/agent-base/commit/655fc3c1f2ba480e5c69184ae1e7eb1fd22d270b))
* **cli:** extract interactive and execution modes ([8145c83](https://github.com/danielscholl/agent-base/commit/8145c83a2c5b9887e84081fd23986a51ad69e1d4))
* **cli:** extract single-prompt and chat logic into modules ([9d0e97c](https://github.com/danielscholl/agent-base/commit/9d0e97c120251040b3f27bdfdba79b5221b4e97c))
* **cli:** move telemetry helpers to utils and add shared execution ([d365a8a](https://github.com/danielscholl/agent-base/commit/d365a8a19dda48ba2393d73be2f457f3465e1dc4))
* **cli:** remove in-file _hide_connection_string helper implementations ([d365a8a](https://github.com/danielscholl/agent-base/commit/d365a8a19dda48ba2393d73be2f457f3465e1dc4))
* **cli:** standardize imports and typing ([2c3e1a4](https://github.com/danielscholl/agent-base/commit/2c3e1a47d9294f42455cf219c6810dfbfb2f2b85))
* **config:** eliminate 353 lines with provider registry pattern ([60f430b](https://github.com/danielscholl/agent-base/commit/60f430b0d8e0fbc2edf0c937a34563af3502ce8d))
* **mem0:** add _create_embedder_config and get_embedding_model helpers ([dbbbea4](https://github.com/danielscholl/agent-base/commit/dbbbea44c7e32b3a67dc4132d6f6b187ad394eae))
* **mem0:** centralize embedding model selection and embedder config ([dbbbea4](https://github.com/danielscholl/agent-base/commit/dbbbea44c7e32b3a67dc4132d6f6b187ad394eae))
* **mem0:** use get_embedding_model in health check and embedder setup ([dbbbea4](https://github.com/danielscholl/agent-base/commit/dbbbea44c7e32b3a67dc4132d6f6b187ad394eae))


### Continuous Integration

* **workflow:** install dev and mem0 extras ([484d1c2](https://github.com/danielscholl/agent-base/commit/484d1c2319107681470602fb41f133f0f03b0981))


### Miscellaneous

* **config:** add type: ignore for mem0 import ([81ed90f](https://github.com/danielscholl/agent-base/commit/81ed90f3c84845f7bee3508a9ffe620a01ac7bef))
* **coverage:** exclude extracted CLI modules from coverage ([ebef494](https://github.com/danielscholl/agent-base/commit/ebef4946c627159a6859f6e8a224ea038a4acdc0))

## [0.2.3](https://github.com/danielscholl/agent-base/compare/agent-template-v0.2.2...agent-template-v0.2.3) (2025-11-14)


### Bug Fixes

* **config:** provider flag and menu display improvements ([33c6d2b](https://github.com/danielscholl/agent-base/commit/33c6d2b4b918178012d9ab50f60e68cd73e3d2f7))
* **config:** trigger release for provider flag fix ([c659b40](https://github.com/danielscholl/agent-base/commit/c659b40236fb404692c5e6ec4bd9ade10e934d2a))

## [0.2.2](https://github.com/danielscholl/agent-base/compare/agent-template-v0.2.1...agent-template-v0.2.2) (2025-11-14)


### Bug Fixes

* **github:** update GitHub Models API endpoint and add enterprise support ([9641136](https://github.com/danielscholl/agent-base/commit/9641136f04504f5ccd2bf522cf1dff6c60691542))
* **github:** Update GitHub Models API endpoint and add enterprise support ([c3e4807](https://github.com/danielscholl/agent-base/commit/c3e4807fd44f2b75877bcdd653966908aceedcae))
* **mem0:** match GitHubChatClient URL construction for enterprise orgs ([0f33fd6](https://github.com/danielscholl/agent-base/commit/0f33fd6bf2c62513cfd9a99f8f899d46cd7424bc))
* **tests:** improve Windows compatibility and formatting in test files ([3b450ee](https://github.com/danielscholl/agent-base/commit/3b450eead4612622a0cf01dded9e2526ea2fbccc))
* **tests:** resolve Windows test failures and enable passing tests ([e6ef556](https://github.com/danielscholl/agent-base/commit/e6ef5569c1f4467629f2c5e30da3d138338adb3b))


### Documentation

* add GitHub Models to README provider list ([20237f1](https://github.com/danielscholl/agent-base/commit/20237f1ac37b347926185eb3870bb74e83d21bad))
* **copilot:** add guidance for working with copilot coding agent ([b46f84f](https://github.com/danielscholl/agent-base/commit/b46f84f3cea1181dfb2947de22bebcc23c3d1da0))
* **copilot:** improve formatting consistency in instructions ([42f5594](https://github.com/danielscholl/agent-base/commit/42f5594e82c67ca732ccafc329f237bff92e3231))


### Code Refactoring

* **cli:** extract console encoding setup to shared utility ([aeaf330](https://github.com/danielscholl/agent-base/commit/aeaf330b16ba46c7a8fea47f08eef291645b608d))
* **cli:** extract console encoding setup to shared utility ([3727b44](https://github.com/danielscholl/agent-base/commit/3727b447b519b1132ebaa6c3f309d8aa9381bec7))
* **config:** extract GitHub org setup to helper function ([56bb6cf](https://github.com/danielscholl/agent-base/commit/56bb6cf689d77d7fe236bc7616d0df503236a0e6))
* **tests:** move os import to module level in test_mem0_utils.py ([049f7d4](https://github.com/danielscholl/agent-base/commit/049f7d4bc699c98c349172185f746f014d5e094e))
* **tests:** move os import to module level in test_mem0_utils.py ([c535ebc](https://github.com/danielscholl/agent-base/commit/c535ebcebd196473198cea75d7d27353d6b844da))
* **tests:** simplify test function signatures in test_utils.py ([d3a9904](https://github.com/danielscholl/agent-base/commit/d3a9904aba9650a1e18c0f5f92b3fe34032bfe0b))


### Tests

* fix Windows-specific test failures ([f1f3d19](https://github.com/danielscholl/agent-base/commit/f1f3d19cf4deee4044c9c4b8ca6ab7e0f811103b))

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
