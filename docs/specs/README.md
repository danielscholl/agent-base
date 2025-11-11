# Specifications

## Purpose

Specifications are **planning documents** that guide feature development and capability implementation. They help think through requirements, approaches, and design before coding begins.

## What Specs Are

- **Planning tools** - Help organize thoughts before implementation
- **Implementation guides** - Provide direction during development
- **Conversation starters** - Document initial design intent

## What Specs Are NOT

- **Reference documentation** - Use architecture.md, ADRs, and code comments instead
- **Authoritative truth** - Implementation often diverges as bugs get fixed and requirements evolve
- **Maintained docs** - Not updated to reflect all implementation changes

## How to Use Specs

**Before implementation:**
- Write spec to think through approach
- Consider alternatives and tradeoffs
- Identify key requirements and edge cases

**During implementation:**
- Use as general guide
- Expect to deviate as you discover issues
- Don't treat as rigid contract

**After implementation:**
- Capture architectural decisions in ADRs (see docs/decisions/)
- Update architecture.md if patterns changed
- Leave spec as historical record of original thinking
- **Do not** maintain spec to match final code

## When to Create a Spec

Create a spec when:
- Planning a non-trivial feature (multi-file changes)
- Exploring design alternatives
- Need to document requirements before coding
- Want to think through edge cases

Skip specs for:
- Simple bug fixes
- Minor enhancements
- Well-understood patterns

## Reference Documentation Hierarchy

For current, authoritative information, refer to:

1. **Code** - Source of truth
2. **ADRs** (docs/decisions/) - Architectural decisions with rationale
3. **architecture.md** - Current system architecture
4. **CONTRIBUTING.md** - Development patterns and conventions
5. **Specs** (docs/specs/) - Historical planning documents

---

**Remember**: Specs help you think before you build. They're not documentation to maintain afterward.
