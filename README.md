# incident-agent

A coding agent that investigates production issues with **PagerDuty**, **Sentry** and **Elasticsearch**, traces them to your code, and proposes or applies a fix. Built on the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview).

## Setup

```bash
git clone https://github.com/Rew0611/incident-agent && cd incident-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp sample.env .env   # add ANTHROPIC_API_KEY and the integrations you use
```

## Use

```bash
incident-agent "Why is PagerDuty incident Q1ABC2D firing?" --repo ~/code/my-service
incident-agent "Fix Sentry issue MY-SERVICE-1A2" --repo ~/code/my-service --fix
```

Read-only by default. `--fix` lets it edit files in `--repo`; it has no shell, so it never runs commands or pushes. An integration is enabled once its values in `.env` are set.

## Layout

```
incident_agent/
  cli.py      command line
  agent.py    tool grants per mode, streaming output
  prompts.py  system prompt
  tools/      one file per integration: NAME, REQUIRED_ENV, CONTEXT, TOOLS
```

To add an integration, create `tools/<name>.py` with those four names and list it in `tools/__init__.py`.
