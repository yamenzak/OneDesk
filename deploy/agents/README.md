# One's agents

Each app's agent (docs/ARC-AI.md) runs here, on Cloudflare's Agents SDK: one
Durable Object of the class `ModuleAgent` per agent per workspace, named
`{workspace}.{app}` (`one-4dl-dev.one_book`). An agent asleep costs nothing.
Everything it reads and writes stays in the workspace: it works only through
the workspace's tools, as the agent's own user there.

## How it is reached

- **A workspace wakes an agent** with `POST /agents/agent/{workspace}.{app}`,
  the body an event (`{"kind": "mail", "message": ..., "host": ...}`) and a
  token for the agents' way in `x-one-agent-token`
  (`onedesk/one_ai/agents/connect.py`, `wake`). The agent answers 202 and does
  the work as a scheduled task, so a restart does not lose it.
- **An agent calls the workspace back** with `POST
  https://{host}/api/method/onedesk.one_ai.agents.api.tool`, the body
  `{"tool": ..., "args": {...}}` and a token for the workspace's way. A tool is
  one its app's `agent.py` lists in `TOOLS`.
- **An agent hands work to another** by calling its Durable Object
  (`handOn`, then `receive`); each hand-off is also a comment on the record in
  the workspace, so people can read it.

What each agent does is `JOBS` in `worker.ts`: OneMail's receptionist looks at
a mail that arrived (`incoming`), hands each invoice on (`hand_on`) to
OneBook's accountant, which drafts the Purchase Invoice
(`draft_purchase_invoice`).

## The token

`{payload}.{signature}`: the payload is base64url JSON
`{aud, ws, agent, tool, for, sum, iat, exp, jti}`, the signature hex
HMAC-SHA256 of the payload with the workspace's secret. `aud` is the way
(`workspace` or `agents`), `ws` the workspace's slug, `sum` the SHA-256 of the
body, `for` the person who asked when one did. A token lasts two minutes at
most and is used once: the workspace keeps each `jti` in redis, and the
Durable Object in its own SQLite, until it lapses.

The workspace's secret is HMAC-SHA256 of `agents:{workspace}` with the
Worker's `ONE_SECRET`. OneAdmin, which holds the same secret as
`agents_secret`, gives each workspace its own (`proxy.agents_config`); no
list of secrets is kept.

## Deploying

Set Up Cloudflare deploys it (`one_admin/setup.py`, `agents`) with wrangler,
from `worker.ts`, `token.ts`, `package.json` and `tsconfig.json`, and keeps
its address as `agents_url`. Locally: `npm install`, `npx tsc --noEmit -p .`,
`node --test token.test.ts`.
