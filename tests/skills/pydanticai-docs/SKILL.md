---
name: pydanticai-docs
description: Quick reference for Pydantic AI framework
---

# Pydantic AI Docs

Quick reference for building agents with Pydantic AI.

## Instructions

For detailed information, fetch the full docs at:
https://ai.pydantic.dev/llms-full.txt

## Quick Examples

**Basic Agent:**

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2')
result = agent.run_sync('Your question')
```