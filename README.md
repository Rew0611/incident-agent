# incident-agent

A coding agent that investigates production issues with **PagerDuty**, **Sentry** and **Elasticsearch**, traces them to your code on **GitHub**, and opens a pull request with the fix. Built on the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview).

## Setup

```bash
git clone https://github.com/Rew0611/incident-agent && cd incident-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp sample.env .env   # add ANTHROPIC_API_KEY and the integrations you use
```

## Use

```bash
incident-agent "Why is PagerDuty incident Q1ABC2D firing?" --repo acme/checkout
incident-agent "Fix Sentry issue CHECKOUT-1A2" --repo acme/checkout --fix   # opens a PR
incident-agent "Fix Sentry issue CHECKOUT-1A2" --repo ~/code/checkout --fix # edits local files
```

`--repo` is a GitHub repo (`owner/name`) or a local path. GitHub repos are cloned into `~/.cache/incident-agent`. Read-only by default; with `--fix` the agent edits the code and, for GitHub repos, the changes go to a new branch and a pull request for you to review. The agent itself has no shell or git; it only reads and edits files in the repo. An integration is enabled once its values in `.env` are set.

## Layout

```
incident_agent/
  cli.py        command line
  agent.py      tool grants per mode, streaming output
  workspace.py  GitHub clone and pull request
  prompts.py    system prompt
  tools/        one file per integration: NAME, REQUIRED_ENV, CONTEXT, TOOLS
```

To add an integration, create `tools/<name>.py` with those four names and list it in `tools/__init__.py`.
