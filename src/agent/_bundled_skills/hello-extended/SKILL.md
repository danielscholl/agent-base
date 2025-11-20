---
name: hello-extended
description: Multi-language greetings in 6 languages. Use for non-English greetings or multiple people.
toolsets:
  - toolsets.hello:HelloExtended
---

# hello-extended

## 🎯 Triggers
**USE:** greetings in Spanish/French/German/Japanese/Chinese, multiple greetings
**SKIP:** simple English greetings (use built-in `greet_user`)

## Tools

**Direct (instant):**
- `greet_in_language(name, language)` - Culturally appropriate greeting
  Languages: Spanish (es), French (fr), German (de), Japanese (ja), Chinese (zh), English (en)
- `greet_multiple(names)` - Greet list of people

**Script (advanced):**
- `advanced_greeting.py` - Time-aware, formatted greetings
  Usage: `script_run hello-extended advanced_greeting.py --json`

## Quick Guide
- One person, specific language → `greet_in_language("Alice", "es")`
- Multiple people → `greet_multiple(["Alice", "Bob", "Charlie"])`
- Fancy formatting → `script_run hello-extended advanced_greeting.py --json`
