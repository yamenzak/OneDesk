# One's AI: AICenter, the agents and OneChat — the plan

12 November 2026 · Yamen · written in [the live doc](https://claude.ai/artifact/PmpZyP9WkXpZ9p1JnyVfp8); this copy is the one the code is held to.

## The decision

One OneAI that knows everything is replaced by a team: one agent per module, each the virtual employee of its department, under a master agent people talk to first. AICenter becomes the place they live, OneChat the place people talk to them, and the agents talk to each other instead of through Intake.

The single OneAI turned out dumber, slower and easier to lose than a person, because every question carried the whole of One into one context and every answer had to be checked. A module's agent carries only its own module, its own records and its own procedures, so it can be trained deeply, judged on a narrow job and trusted with more. Donna (Build with Hussain) shows the shape works on ERPNext: one narrow job, learned end to end, turned into a script and a written procedure, then scheduled.

## What we keep from OneAI and Intake

Most of what OneAI is made of stays; what goes is the one loop that tries to be everything. OneAI today is about 120 tools, 300 module actions across 20 modules' `agent.py`, cards that wait for a person, a credits hold on every call and a search index per workspace. Intake is `one_ai/reading/`: it reads every mail and file, decides what each is, and makes drafts for several modules from inside one folder.

| Part today | Becomes |
| --- | --- |
| Each module's `agent.py` tools (`one_ai_reads`, `one_ai_suggests`) and `NOT_FOR_AI` | That module's agent's tools, unchanged in shape |
| AI Proposal cards, checked when written and again when applied | The Draft and Ask First levels: the same card, shown in OneChat and on the record |
| Reading Action with undo and attribution (`act.py`) | Every agent write, so any agent action can be undone |
| Credits hold and settle, the gateway, the model tiers, `jobs.py` prompts | Kept as they are; each agent's run is metered the same way |
| Search index, Identifier table, `facts.py` checks, `audit.py` | Shared services every agent calls |
| The chat loop (`chat.py`, `run.ask`) guessing tool groups from words | Replaced by Una routing to one agent with only its own tools |
| Intake's planners for money and plans (`reading/money.py`, `plans.py`) | Moved to the modules that own them: OneBook's agent makes invoices, OneProject's makes tasks |
| Intake's reading and sorting of mail and files | OneMail's and OneCloud's agents, which then hand each item on |
| The Documents page (Waiting, Done) | Each agent's queue in OneChat and AICenter |
| Briefs kept in hidden fields | Kept as fields; agents comment only when something happens that a person should know |

One decision from before is worth keeping: briefs went into a field rather than comments because forty invoices would be forty comments. So an agent comments on an event ("the supplier's bank details changed"), never on every pass, and the rolling summary stays a field.

## The agents

Each module that a workspace turns on brings one agent, its virtual employee for that department, and **Una** stands above them as the one people talk to first. Una knows who does what, plans a job that spans departments and hands each part to the right agent; she is not an expert in any module and never does a module's work herself.

What each agent has:

- **A face and a name.** A DiceBear voxel-bot, animated, seeded by the module so it never changes, and a role name people can say: OneBook's accountant, OneHR's people officer, OneMail's receptionist.
- **Its module, deeply.** The module's Help and AGENTS.md, its record types and their rules, read from the code as Donna learned ERPNext by reading it, so it does not guess an API or a field.
- **Its tools.** The module's actions, which today are OneAI's cards in each module's `agent.py`, become that agent's tools and no one else's.
- **Its procedures.** What it learned to do, written as a procedure and, once proven, a script it runs the same way every time (Donna's lesson: a script, not a prompt, for anything that must repeat).
- **Its memory.** What it learned about this workspace: the supplier who always invoices by mail, the approver for travel, the way this company names projects. Shown in AICenter, editable, forgettable.
- **Its routines.** Work it does on a schedule: the morning reconciliation, the weekly payroll check, the month-end close list.

What it writes goes where people already look: a **comment on the record** it touched or noticed ("Matched to the bank line of 4 Nov; the supplier's VAT number was missing, I added it from their last invoice"), and a short daily note in its department's channel in OneChat. There are no separate summaries to find.

**Agents delegate to each other instead of Intake.** OneMail's receptionist reads an incoming invoice, hands it to OneBook's accountant with the attachment, and the accountant makes the draft and comments on it. OneCloud's agent does the same with an uploaded file. Each hand-off is a message between agents that people can open, so nothing happens in a hidden queue.

## Trust and permissions

An agent is a real user of the workspace with only its department's roles, and it may do only what both it and the person who asked may do. Work it does on its own schedule runs on its own roles alone, inside the limits AICenter sets.

Its roles are its app's User roles and, where those cannot reach what the agent is for, a role of its own that the manifest names in `agent_roles`: never a manager's role nor one that runs the workspace, never one a person holds (migrate takes it off anybody else, and the agents' check fails if a person has it). OneMail's receptionist holds OneMail Receptionist, which reads Communication and the record types OneMail links mail to (frappe opens a linked mail only to whoever reads its record); people read their mail through the mailboxes they hold, and the receptionist holds none, so OneMail's permission hook lets it open only the mail of a mailbox OneAI reads and no other Communication.

Every action an agent has carries one of three levels, set per module in AICenter:

| Level | What happens | Default for |
| --- | --- | --- |
| Do it | The agent does it and comments on what it did | Reading, searching, summaries, comments, tags |
| Draft | The agent prepares it, a person submits it | Creating invoices, orders, entries, mails |
| Ask first | The agent stops and asks the named approver | Submitting, cancelling, paying, anything sent outside the company |

A level only moves up by a person's choice, one action at a time, once the agent's record on that action is good (AICenter shows how many it did and how many were corrected). Some things no agent ever does: delete records, change roles or settings, give credits, or pay without a person's approval.

Who may talk to which agent follows AccessCenter: a person reaches the agents of the modules they may open. Una talks to everyone but hands a job only to agents that person may reach. Everything an agent does is in the record's activity under its own name, linked to the conversation or routine that caused it, and versions keep what it changed.

## How they run

The agents' thinking runs on Cloudflare's Agents SDK, one Durable Object per agent per workspace, and everything they touch stays in the workspace, reached through tools as OneAI reaches it today. [Project Think](https://blog.cloudflare.com/project-think/) (April 2026) gives each agent durable runs that survive restarts, its own small database for memory and sessions, schedules that wake it without a person, and sub-agents it calls like functions; [Agents SDK 0.17](https://developers.cloudflare.com/changelog/post/2026-06-26-agents-sdk-v0.17.0/) (June 2026) adds sub-agents that run in the background and report progress. An agent asleep costs nothing.

Why not inside the workspace: a long job in a Frappe worker holds that worker for the whole run and dies with a restart, which is how OneAI's heaviest job came to cost 243 seconds an hour on the admin site. Why not OpenClaw or Hermes: they are one always-on server per agent, which does not scale to an agent per module per workspace.

**Procedures and scripts, the way Donna learned:**

1. A person shows the agent one case in OneChat ("process this invoice") and checks each step.
2. The agent writes what it did as a **procedure**: steps in plain words, kept as a record in the workspace, shown in AICenter.
3. For work that must come out the same every time, it writes a **script**. Where it can, it builds it as an automation in AutomationCenter, from safe blocks; what blocks cannot express is code the workspace runs, so it stays off until OneGuard has read it and a second model has passed it.
4. A person approves it and, if they want, schedules it. From then on the agent runs the script and only thinks about the cases it doesn't cover, and those it asks about.

Models follow the work: learning a new job uses the strongest model, a routine that runs a proven script uses a cheaper one, through OneAdmin's gateway and metered in credits like everything else.

One thing this moves: an agent's memory and conversations are stored at Cloudflare, not only passed through it. That is a privacy change to put to the agreements, with notice.

## AICenter

AICenter becomes the agents' office: one tab per module for that module's agent, and One's tab for Una and every agent together. It takes OneAI's place on the foot of every module, and it is where an administrator decides how far each agent may go.

A module's tab holds its agent:

- **Who it is:** face, name, what it does, which roles it has.
- **What it may do:** every action with its level (Do it, Draft, Ask First), and its record on each: done, corrected, refused. Today's manual switches per module move here.
- **What it learned:** its procedures and scripts, each with an on switch and its schedule, and its memory of this workspace, which a person can edit or tell it to forget.
- **What it did:** its activity, each item linked to the record and the conversation, with Undo.
- **What it costs:** credits this month, against a limit the administrator sets.

One's tab holds Una and the whole team: who reports what, the workspace's rules that bind every agent (who approves payments, what never leaves the company), the total spend and limit, and the switch that turns agents off.

**The mark.** OneAI's logo moves to AICenter, refined to feel more magical: the same shape, a slow shimmer through it while an agent is working and still at rest, so movement always means something is happening.

## OneChat

OneChat is one place to talk to the team, to the agents and to people outside, built in Vue on frappe-ui and drawn the way Slack and Gameplan draw it. OneAI's panel is replaced by a conversation with Una or a module's agent, docked where the panel was; the small inline panels become a one-line "Ask OneBook" popover that answers in place.

| Part | What it is |
| --- | --- |
| Channels and direct messages | The team, by department or project, with threads, mentions, reactions and files from OneCloud |
| Agents | Each agent is a member: talk to it alone, or mention it in a channel ("@OneBook, why is this unpaid?"). Its cards (Draft, Ask First) appear in the conversation with Approve and Change |
| Department channels | Each agent's daily note and its questions land in its department's channel, where the people who own that work read them |
| Rooms with the outside world | A chat widget for the company's website or portal opens a room; an agent answers first, a person joins or takes over, and the room can be forwarded |
| Preset replies and automations | Saved replies, and rules ("when a room opens after hours, OneCRM's agent answers and makes a lead"), from one AutomationCenter shared with OneMail's rules |

What we take from where: the chat experience from Hugging Face's [Chat UI](https://github.com/huggingface/chat-ui) (streamed answers, the agent's steps shown as it works, files in and out), but not its code, which is SvelteKit; the data model and realtime from Frappe's [Raven](https://github.com/The-Commit-Company/raven) as reference; threads and quiet reading from Gameplan; channels, mentions and huddles from Slack and Discord. Realtime is frappe's socket.io, which One already runs.

**AutomationCenter** is a new centre under One and the safe way to automate: a node builder like n8n, where each block writes only its own part of the server script, so an automation is predictable, always safe and needs no review. It powers OneMail's rules (which move into it first), OneChat's, and any app's; it works with AICenter (an agent can be a block, or draft an automation) and entirely without AI too. It replaces most of what OneStudio's server scripts were for; deeper customisation becomes paid work, in OneStudio's own arc later.

## OneCredit

The currency is called **OneCredit**, and an amount of it is plain credits: "OneCredit balance: 1,250 credits", "This run used 4 credits". A brand name for the currency and a plain word for the count reads the way Robux or Apple's Gift Card balance does, and it avoids "OneCredits", which reads as a plural of a name. A new name was considered (Sparks, Units, Ones) and none beat it: Ones collides with the product, and the others say nothing about One.

**The mark:** One's logo with the rim in gold instead of the colour gradient, and the 1 crossed by two short strokes, as the euro sign is crossed, so it reads as money at a glance. It appears beside every amount, on the top-up button and in the price list.

## Build order and decisions

Start with one real job end to end, Donna's job: an invoice arrives by mail, OneMail's agent hands it to OneBook's, and a draft Purchase Invoice is waiting for a person. Everything after that is built on what that job proves.

1. **The foundation and the first two agents.** Agent users, levels, tools from `agent.py`, the runtime on Cloudflare; OneMail hands invoices to OneBook. *Gate: 50 real invoices, at most 2 corrected.*
2. **AICenter and OneChat.** The agents' office; channels, messages, and agents with their cards in the conversation. *Gate: a week on OneChat instead of OneAI's panel.*
3. **An agent for every module.** Module by module; Intake and OneAI's chat retire once their last job has moved. *Gate: no job is left that only the Documents page does.*
4. **The outside world.** Rooms and the website widget, AutomationCenter, OneCredit's name and mark.
5. **The setup agent, with the next arc.** Helps a new company set One up and tunes it to how they work.

Each gate is a measure on real use, not a feature list; a step that misses its gate is fixed before the next starts.

**Decided 12 Nov 2026:**

- [x] The master agent is **Una**.
- [x] The agents run on Cloudflare; the privacy clause says their memory and conversations are stored there, recorded without a new revision since no workspace has agreed yet.
- [x] Every agent starts cautious: reading and comments Do it, every write Draft, paying, submitting and anything leaving the company Ask First; raised one action at a time.
- [x] The currency is **OneCredit**, its amounts plain credits.
- [x] OneChat is ours, in Vue on frappe-ui, with Raven as a reference.

**Decided 13 Nov 2026 (P8.1):**

- [x] **The account now calls a workspace, for the agents only.** Until now every call went from a workspace to OneAdmin, and nothing outside a workspace could start anything in it; that kept a workspace's records reachable only by the people signed in to it. An agent thinks on Cloudflare but every tool it uses is in the workspace, so the Worker must call in. It does so on one path, `one_ai/agents/api.py tool`, and nowhere else: each call carries a token signed with the workspace's own secret (made from the Worker's and the workspace's slug, so no list of secrets is kept anywhere), naming the workspace, the agent and the one tool, over the exact body, for at most two minutes, used once. The tool runs as the agent's user, whose roles are its app's User roles alone, and every write goes through the agents' door. A stolen token opens one call of one tool for one minute; a stolen Worker secret opens agents' tools, never a person's session or a setting. The account's other services still never call a workspace.
- [x] An agent is a user per app with a manifest's `agent`, `<app>@agents.one.invalid`, turned off so it never signs in and takes no seat, made on every migrate with exactly its app's User roles.
- [x] Levels sit in each app's `agent.py` as `LEVELS`, for every call `REACH` names and every tool `TOOLS` lists; what is not declared is Ask First. Draft makes a new record as a draft; any other change at Draft is a card, since there is nothing to draft.
- [x] One Durable Object class, `ModuleAgent`, with an instance per agent per workspace named `{workspace}.{app}`; what an agent does is the Worker's `JOBS`, the receptionist's and the accountant's first. (14 Nov, P8.3: `JOBS` is gone; the wake names the tool and each answer the steps after it, so the Worker's one job runs any agent, and each agent's work is declared in its agent.py.)
- [x] The privacy clause `oneai-agents` and Cloudflare's Durable Objects as a subprocessor, recorded as a new hash: nobody has agreed yet.
