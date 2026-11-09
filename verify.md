# verify.md

Assumptions this code makes that have **not been run yet**. Check each one and mark it
`[x]` with a date, or fix the code. Docs were read on 2026-11-09.

## Claude Agent SDK (`agent.py`, `tools/__init__.py`)

- [ ] `pip install claude-agent-sdk` bundles the Claude Code CLI (no separate install). Check: `pip install -e .` then a first run without installing `claude`.
- [ ] `ANTHROPIC_API_KEY` from `.env` reaches the SDK subprocess (dotenv sets `os.environ`; Python `env=` is merged on top of it).
- [ ] `tools=[...]` limits the built-in tools the model sees, so there is no `Bash` in either mode. Check: ask the agent to run `ls` and confirm it says it can't.
- [ ] `permission_mode="dontAsk"` denies anything not in `allowed_tools` without prompting. Check: in investigate mode, ask it to edit a file; it must refuse or fail.
- [ ] `Read(/**)` and `Edit(/**)` match only paths inside the working directory (single leading `/`), and the `Edit` rule also covers `Write`. Check: ask it to read `~/.ssh/config`; it must be denied.
- [ ] `Grep` and `Glob` inside the working directory run without an allow rule (file reads inside working dirs need no approval).
- [ ] `setting_sources=[]` loads no user/project/local settings (needs SDK > 0.1.59).
- [ ] MCP tools are named `mcp__<server key>__<tool name>`, where the server key is the pack `NAME`.
- [ ] `SdkMcpTool.name` holds the tool name (used to build `allowed_tools`).
- [ ] The `{"type": "preset", "preset": "claude_code", "append": ...}` system prompt keeps Claude Code's tool guidance and adds ours.
- [ ] `env={"ENABLE_TOOL_SEARCH": "false"}` loads all 8 tool definitions upfront (no ToolSearch step, which `tools=[...]` might hide).
- [ ] Returning `{"content": [...], "is_error": True}` from a handler marks the call as failed.
- [ ] A failed single-shot `query()` raises a `ClaudeSDKError` subclass (`ResultError`, SDK >= 0.2.140), caught in `cli.py`.
- [ ] `claude-opus-5-5` is accepted as `model`.

## GitHub (`workspace.py`, `tools/github.py`)

- [ ] git over HTTPS accepts the header `AUTHORIZATION: basic base64("x-access-token:<token>")` for classic and fine-grained personal tokens (the header `actions/checkout` uses).
- [ ] `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY_0` / `GIT_CONFIG_VALUE_0` set that header without writing it to `.git/config` (git >= 2.31). Check: `cat ~/.cache/incident-agent/<owner>/<name>/.git/config` has no token.
- [ ] `GET /repos/{repo}` returns `default_branch`; `GET /repos/{repo}/commits` takes `since`, `sha`, `path`, `per_page` (max 100).
- [ ] `POST /repos/{repo}/pulls` with `title`, `head`, `base`, `body` returns `html_url`. Check: a `--fix` run on a test repo opens a PR.
- [ ] Each run resets the clone to `origin/<base>` (`reset --hard`, `clean -fd`): edits left in the cache are discarded by design.
- [ ] Commits use the user's git identity, or `incident-agent` when `user.email` is not set.
- [ ] A relative `--repo` like `foo/bar` that is not a local directory is treated as a GitHub repo.

## PagerDuty (`tools/pagerduty.py`)

- [ ] Auth headers: `Authorization: Token token=<key>` and `Accept: application/vnd.pagerduty+json;version=2`.
- [ ] `GET /incidents` takes `since`, `until`, `limit` (max 100), `sort_by=created_at:desc`, `statuses[]`, `service_ids[]`.
- [ ] httpx sends list params as repeated `statuses[]=a&statuses[]=b`. *Untested.*
- [ ] `GET /incidents/{id}` accepts an incident ID or number.
- [ ] `GET /incidents/{id}/alerts` returns `body.details` by default. *Only seen in a docs example.*
- [ ] `GET /incidents/{id}/log_entries?is_overview=true&limit=100` and `/notes` work; limits and sort order unconfirmed (code sorts newest-first itself).
- [ ] EU accounts use `https://api.eu.pagerduty.com`.

## Sentry (`tools/sentry.py`)

- [ ] `GET /api/0/organizations/{org}/issues/` takes `query`, `statsPeriod`, `limit` (max 100).
- [ ] `GET /api/0/organizations/{org}/issues/{id}/` and `.../issues/{id}/events/latest/` work with a Bearer token.
- [ ] Latest event: `entries[]` has `exception` (frames with `filename`, `function`, `lineNo`, `inApp`, `context` as `[line, text]` pairs) and `breadcrumbs`; `tags` is `[{key, value}]`.
- [ ] Frames are ordered oldest call first, crash site last (we keep the last 20 in-app frames). *Not confirmed in docs.*
- [ ] `GET /api/0/organizations/{org}/shortids/{short_id}/` returns `groupId`.
- [ ] Issue URLs contain `/issues/{id}`. *Not confirmed in docs.*

## Elasticsearch (`tools/elasticsearch.py`)

- [ ] `POST /{index}/_search` with `bool.filter` (`range` on the timestamp field + `query_string`), `sort` with `unmapped_type`, `_source` list, `track_total_hits: true`; reads `hits.total.value`.
- [ ] `now-60m` date math works in the `range` filter; explicit `start`/`end` use `strict_date_optional_time`.
- [ ] terms aggregation returns `buckets[].key/doc_count` and `sum_other_doc_count`.
- [ ] `GET /{index}/_mapping` returns `{index: {mappings: {properties}}}`; multi-fields sit under `fields`.
- [ ] API key auth is `Authorization: ApiKey <key>`; httpx `auth=(user, password)` sends basic auth. *Basic auth untested.*
- [ ] A query of `*` is skipped (time filter only) rather than sent as `query_string`.
- [ ] A mistyped index returns an error (no `ignore_unavailable`), which the tool reports as `HTTP 404`.

## First run

1. `cp sample.env .env`, fill in one integration, run `incident-agent "List the 5 most recent incidents" --repo .`
2. Confirm tool calls print as `> mcp__...` and the run ends with `[success]`.
3. Try a bad token: the tool should return an `HTTP 401 ...` error, not crash the run.
4. On a throwaway GitHub repo: `incident-agent "Add a comment to the README" --repo you/test --fix` must open a PR.
