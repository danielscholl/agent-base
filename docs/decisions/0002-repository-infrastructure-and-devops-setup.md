---
status: accepted
contact: danielscholl
date: 2025-11-07
deciders: danielscholl
consulted:
informed:
---

# Title: Repository Infrastructure and DevOps Setup

## Context and Problem Statement

We need to establish a robust DevOps infrastructure for the agent-template project that ensures code quality, automates releases, and maintains security. The infrastructure must support continuous integration, automated testing, security scanning, and streamlined release management. We need to decide on CI/CD platform, release automation strategy, security tooling, and code quality standards.

## Decision Drivers

- **Code Quality**: Enforce formatting, linting, type checking, and test coverage
- **Automation**: Minimize manual processes for releases and testing
- **Security**: Proactive vulnerability scanning and dependency reviews
- **Developer Experience**: Fast feedback loops, clear error messages
- **Cost**: Prefer free/open-source solutions for public repositories
- **Maintainability**: Simple configurations that are easy to understand and modify

## Considered Options

1. **GitHub Actions + release-please + comprehensive quality checks**
2. **GitLab CI + manual releases + basic quality checks**
3. **Jenkins + semantic-release + custom quality checks**

## Decision Outcome

Chosen option: **"GitHub Actions + release-please + comprehensive quality checks"**

This provides the best integration with GitHub, excellent automation capabilities, zero cost for public repositories, and comprehensive tooling support.

### Infrastructure Components

**CI/CD Platform**: GitHub Actions
- Native GitHub integration
- Free for public repositories
- Large marketplace of actions
- Matrix testing for multiple Python versions

**Release Automation**: release-please by Google
- Automatic version bumping from conventional commits
- Changelog generation
- Release PR creation and management
- uv.lock synchronization

**Code Quality Stack**:
- **Black**: Code formatting (100 char line length)
- **Ruff**: Fast Python linting and import sorting
- **MyPy**: Static type checking
- **PyTest**: Testing framework with 85% coverage minimum
- **pytest-cov**: Coverage reporting

**Security Tools**:
- **CodeQL**: Security vulnerability scanning
- **Dependabot**: Automated dependency updates
- **dependency-review-action**: PR dependency analysis
- **SBOM generation**: Software Bill of Materials using CycloneDX

### Consequences

**Good:**
- Fully automated release process (commit → changelog → release)
- Comprehensive quality checks catch issues early
- Zero-cost infrastructure for public repository
- Security scanning happens automatically
- Clear feedback on PRs via GitHub UI
- Consistent code style enforced by CI

**Neutral:**
- Requires learning conventional commits format
- GitHub Actions YAML can be verbose
- Release-please has opinionated changelog format

**Bad:**
- Locked into GitHub ecosystem
- Some quality checks can be slow (~3-5 minutes)
- Matrix testing increases CI time (but catches Python version issues)

## Pros and Cons of the Options

### Option 1: GitHub Actions + release-please + comprehensive quality checks

**Pros:**
- Free for public repositories
- Native GitHub integration (no external accounts)
- release-please automates entire release cycle
- Large action marketplace (codecov, codeql, etc.)
- Matrix testing for Python 3.12 and 3.13
- Comprehensive quality checks (black, ruff, mypy, pytest)
- Built-in security scanning (CodeQL, Dependabot)

**Cons:**
- GitHub Actions YAML can be verbose
- Limited to 2000 minutes/month on free tier (sufficient for small projects)
- Vendor lock-in to GitHub

### Option 2: GitLab CI + manual releases + basic quality checks

**Pros:**
- Self-hosted option available
- Integrated CI/CD and container registry
- Free tier includes 400 minutes/month

**Cons:**
- Manual release process (no release-please equivalent)
- Requires separate account/service
- Less comprehensive action marketplace
- More complex setup for matrix testing
- Smaller community for Python projects

### Option 3: Jenkins + semantic-release + custom quality checks

**Pros:**
- Complete control and customization
- Self-hosted, no vendor lock-in
- Powerful plugin ecosystem

**Cons:**
- Requires infrastructure management
- Complex setup and maintenance
- No free hosted option
- Steeper learning curve
- More operational overhead

## Implementation Details

### GitHub Workflows

**CI Workflow** (`.github/workflows/ci.yml`):
```yaml
- Matrix testing: Python 3.12, 3.13
- Quality checks: black, ruff, mypy (continue-on-error)
- Testing: pytest with 85% coverage requirement
- Coverage upload: Codecov for visualization
- Summary generation: Shows all quality check results
```

**Release Workflow** (`.github/workflows/release.yml`):
```yaml
- release-please: Creates/updates release PR
- uv.lock sync: Ensures lock file is up-to-date
- Package building: Creates distribution artifacts
- GitHub Release: Uploads artifacts automatically
```

**Security Workflow** (`.github/workflows/security.yml`):
```yaml
- Dependency review: Blocks PRs with vulnerable dependencies
- SBOM generation: Creates software bill of materials
- CodeQL: Scans for security vulnerabilities
- Weekly schedule: Catches new CVEs
```

### Dependabot Configuration

```yaml
- Python dependencies: Weekly updates, grouped by dev/prod
- GitHub Actions: Weekly updates for workflows
- Open PR limits: 5 for Python, 3 for Actions
- Scheduled: Monday mornings to batch updates
```

### Coverage Targets

- **Unit tests**: Target 100% for business logic
- **Integration tests**: Cover happy paths and major errors
- **Overall minimum**: 85% (enforced by CI)
- **Exclusions**: Display logic (hard to test, Phase 3), test files

### Conventional Commits

Format: `<type>(<scope>): <description>`

**Types and version bumps:**
- `feat:` → Minor version (0.x.0)
- `fix:` → Patch version (0.0.x)
- `feat!:` or `BREAKING CHANGE:` → Major version (x.0.0)
- `docs:`, `style:`, `refactor:`, `test:`, `chore:`, `ci:` → No version bump

### Release Process

1. Developer commits with conventional commit format
2. release-please analyzes commits, calculates version
3. release-please creates/updates release PR
4. Merge release PR triggers:
   - GitHub Release creation
   - Changelog update
   - Package build and artifact upload
   - Version tag

## Quality Standards

### Code Formatting
- **Tool**: Black with 100 character line length
- **Enforcement**: CI fails if not formatted
- **Auto-fix**: `uv run black src/ tests/`

### Linting
- **Tool**: Ruff (fastest Python linter)
- **Rules**: pycodestyle, pyflakes, isort, flake8-bugbear, comprehensions, pyupgrade
- **Enforcement**: CI fails on linting errors
- **Auto-fix**: `uv run ruff check --fix src/ tests/`

### Type Checking
- **Tool**: MyPy
- **Configuration**: Check untyped defs, strict equality, warn on unused configs
- **Enforcement**: CI fails on type errors
- **Coverage**: Required for public APIs, recommended for all code

### Testing
- **Framework**: pytest with pytest-asyncio and pytest-cov
- **Coverage**: 85% minimum, enforced by CI
- **Timeout**: 10 minutes per test run
- **Markers**: `@pytest.mark.integration` for integration tests

### Security
- **CodeQL**: Weekly security scans
- **Dependabot**: Weekly dependency updates
- **Dependency Review**: Block PRs with vulnerable deps
- **SBOM**: Generate on every run, retain 90 days

## Branch Protection

Recommended settings for `main` branch:
- Require PR reviews (1+ approver)
- Require status checks to pass (CI workflow)
- Require branches to be up to date
- No force pushes
- No deletions
- Include administrators

## Cost Analysis

**Free tier (public repository):**
- GitHub Actions: 2000 minutes/month
- Estimated usage: ~10 minutes per PR × ~20 PRs = 200 minutes/month
- CodeQL: Free for public repositories
- Dependabot: Free
- Codecov: Free for open source

**Total cost**: $0/month for typical usage

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [release-please Documentation](https://github.com/googleapis/release-please)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Black Code Style](https://black.readthedocs.io/)
- [Ruff Linter](https://docs.astral.sh/ruff/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [CodeQL](https://codeql.github.com/)
- [Dependabot](https://docs.github.com/en/code-security/dependabot)

## Related Decisions

- ADR-0001: Module and Package Naming Conventions (package structure)
- ADR-0008: Testing Strategy and Coverage Targets (detailed testing approach)
- Future ADRs for specific tooling configurations as needs evolve
