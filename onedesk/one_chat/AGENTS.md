# OneChat

What OneChat is, how it works and why; for agents, OneAI and us. What is
known to be wrong is `SCRATCHPAD.md`, and the Help people read is `help/`.

One place to talk to the team and to the agents (docs/ARC-AI.md, OneChat):
channels by department or project, direct messages between two people, and
a conversation with each agent. OneAI's side panel is one of these
conversations, docked where the panel always was.

## Conversations

A **Chat Channel** is one conversation, of one of three types:

- **Channel**: several people, private or not. One that is not private is
  listed by Browse Channels and anybody may join it; reading it still takes
  joining.
- **Direct**: two people. `direct_key` (the two users, sorted) keeps it one
  per pair.
- **Agent**: one person and one agent (`agent`: an app's id, or `una`). A
  person has as many as they like; the panel lists them as its
  conversations.

Its members are a child table, **Chat Channel Member**: a person (`user`), or
an agent (`agent`, with the agent's user where it has one; Una has none).
`last_read` is when the person last opened it, which makes the unread count.

## Who reads what

Members alone, an administrator's role neither: `channels.has_permission`
and `channels.query` for Chat Channel, `message_permission` and
`message_query` for Chat Message, all in hooks.py. Nothing in `api.py` reads
a conversation without `channels.opened`, which refuses a non-member. Only
whoever wrote a message passes `write` on it. A file attached to a message
is a File attached to the Chat Channel, so frappe opens it to whoever reads
the conversation; one picked from OneCloud is checked first
(`messages.readable_files`): nobody shares what they cannot open.

## Messages

A **Chat Message** has its `channel`, its `sender` (a user; an agent writes
as its own user, Una as nobody, with `agent` saying who), its `text`, its
`thread` (the message it replies to: one level, as Slack's), and
`replies`/`last_reply_on` on the first message of a thread. `mentions` is a
child table (**Chat Mention**: a user or an agent), `files` another (**Chat
File**, a Link to File), and `reactions` JSON, `{emoji: [users]}`, as
Raven keeps its summary on the message. `action` names the Reading Action an
agent's card is; `asks`, `ai_chat` and `parts` are the agent's answer (below).

`messages.post` writes every message, brings the conversation's
`last_message_on` and the thread's count up to date, and tells everybody
live (`live`).

## Live

`frappe.publish_realtime(..., doctype="Chat Channel", docname=...)` sends a
new message (`one_chat_message`) and a changed one (`one_chat_changed`:
reactions, a card answered) to the conversation's room, which frappe's
socket.io lets only somebody passing `has_permission` join (doc_subscribe).
Each member but the sender also hears `one_chat_unread` in their own room,
which refreshes their list. The island joins a room through the kit's
`listenTo`, counted, so a conversation and its thread open together do not
leave the room for each other. Raven was the reference for this and the data
model; none of its code is used.

## Mentions and notifications

`agents.mentioned` reads @handles from the text, longest first, in the order
they are said: a person by their full name, among the conversation's people
only; an agent by its handle (Una, or its app's name), among the agents the
sender reaches. `messages.told` (pure) decides who is told: the people
mentioned, and in a direct conversation the other person; never the sender,
never anybody outside. They are `notifications.py`'s two types, through the
hub (`one/notify.py`).

## How an agent answers

An agent is asked by writing in an Agent conversation, or by mentioning it in
a channel (the first agent mentioned answers, in a thread under the
message). `answers.ask` puts the message, with where the person was and who
answers, on the conversation's transcript, an **AI Chat** for each person
and conversation or thread (`answers.held`, `transcript.py`), which the
asking message names (`ai_chat`, `asks`), and queues `answers.answer`. That
runs in the background as the person who asked: the agent answers with its
own tools, at its levels (`one_ai/agents/talk.py`, one_ai/AGENTS.md, How an
agent answers), and `answers.posted` posts what it said since the last
question as its message, with what it looked up and suggested in `parts`.
Una answers for herself and hands a department's work to its agent. Each
step is told to the asker's browser (`one_ai_run`), and `panel.progress`
answers a browser that missed one.

Who may talk to whom: Una to everybody, an app's agent to whoever holds one
of its app's roles (`agents.reaches`), as docs/ARC-AI.md says. An agent's
face is DiceBear's bottts, seeded by its id, drawn on this server
(`one/avatars.py`) and kept in the cache.

## Cards

The door (`one_ai/agents/door.py`) writes a Reading Action for an agent's
action. On its insert (`cards.posted`, a doc_event), a Draft that was made
(level Done) or an Ask First waiting (Proposed) is posted into the person's
latest conversation with that agent, or a new one. The card is the Reading
Action read as it stands (`cards.card`). **Approve** and **Dismiss** are
`reading/act.py settle`, the door's own approval, which checks who may decide
and that they may do it themselves; **Change** edits the plain values the
card proposes (`cards.changed`, pure) under the same rule, before it is
approved. Nothing in OneChat writes a record.

Once the auditor has had its say on a document, `one_ai/reading/tell.py
waiting` runs the `one_ai_waiting` hook, and `cards.waiting` posts a card for
each of its Reading Actions that waits on a person (`act.WAITS`) and has none
yet: what OneAI's own reading proposed comes from Una, and a Done the auditor
doubts (audit Wrong) from whoever did it. A doubted card has **Keep**
(`act.keep`, the audit becomes Kept) and **Undo** (`act.undo_one`). This is
what OneAI's Documents page did; a person's queue is their conversations with
the agents, and read and unread are each conversation's.

## Rooms and the website

A **Room** is a Chat Channel of its own kind: a conversation with somebody
outside the workspace, a website visitor, that people and agents work in
together. It is built on channels rather than beside them (docs/ARC-AI.md,
Rooms with the outside world), because everything a room needs a channel
already has: members, threads, live updates, unread, notifications, cards,
an agent's answer. What it adds is who it is with (`visitor_name`,
`visitor_email`), the page they wrote from, `desk`, the channel that
answers it, `closed`, and the record it is about (`reference_doctype`,
`reference_name`, set when an automation makes a lead or an issue from it).

Who reads a room: its members, who are the desk's people when it opened,
and anybody in its desk later (`channels.readers`, in has_permission,
query, message_permission and message_query), so somebody who joins the
channel reads its rooms. A room is answered like a channel: what is written
in the room is what the visitor reads, and a thread is the team's note. An
agent mentioned in a room answers in a thread, as in a channel, since it
answers with the asker's tools (answers.posted). **Forward** hands a room to
another channel the reader is in, whose people join it; **Close Chat** ends
it for the visitor. Choosing the channel that answers website chats
(`website`, one at a time) is an administrator's: it puts a chat on the
workspace's public website.

`widget.py` is the visitor's side, guest calls each limited per network
address (frappe's rate_limit): `offered` (whether there is a chat, the
workspace's name and the channel's description), `start` (a room, the
first message, the room's people told by Website Chat), `send` and `said`.
The visitor has no account: `start` answers a random key, the browser keeps
it (`public/js/one_chat/widget.js`, drawn with the DOM, every word a text
node) and only its sha256 is kept, on the room, so the key opens that room
and nothing here can give it back. `said` answers the words of the room's
messages, never a thread, a card, what an agent looked up or a file, and a
person by their first name. A visitor's message is from `Guest`
(`channels.VISITOR`), drawn with the visitor's name; it starts the desk's
automations like a person's. The widget is on every website page but
sign-in, the portal and the desk, and never for somebody signed in to the
desk.

## Automations

A channel's automations are AutomationCenter's (one/AGENTS.md, automation/),
with OneChat's own blocks in `blocks.py`: the trigger `one_chat.posted`,
"When a message is posted", whose place (`scope`) is a Chat Channel of kind
Channel, so AutomationCenter lists them by channel as it lists OneMail's by
mailbox. What people automate in a team chat was surveyed from Slack's
Workflow Builder, Discord's AutoMod and Teams' keyword flows: a reply to
words they watch for, a message passed to another channel, somebody told, a
ticket or a task made, a bot answering. So the Ifs ask the message's Text,
who it is From, In a Thread, Has File, After Hours and On a Holiday
(`one/automation/hours.py`, which any trigger may use), and the actions are
Reply, Post in a Channel, Tell Someone, Create a Record (a Task or an Issue,
linked in the message's thread) and Let an Agent Answer; OneAI's Hand to an
Agent is offered here as on every trigger.

`automations.py` keeps them (the trigger's `keeps`): a member of the channel
who holds Make Channels changes them (`manages`), every member reads them
(`allowed`, `query`), and nobody asks for one, so `decide` refuses.
A room's messages run its desk's automations (`scope_of`), which can ask
From a Visitor, Starts a Website Chat and Website Page, and Forward the
Chat; Create a Record makes a lead of the visitor, never two for one
address, and makes it the room's record. `api.send` and `widget` call
`fire`, which queues `run` after the message is saved: the
engine walks the channel's automations on `facts_of` the message. Only a
person's message starts one: a message an automation posts carries its
`automation` (drawn as a badge with its title) and an agent's its `agent`,
and neither fires, so no automation answers itself. Each action acts as
whoever made the automation, and only while they are still in the channel
(and in the other channel, for Post in a Channel).

Let an Agent Answer runs `talk.ask` with no tools and one round
(`answered`): the agent is told who it is, the automation's instruction and
the thread, words only, and answers in the thread as itself; in a room it
answers the visitor from the room's conversation without its threads, and
stops once somebody of the team has written there (`taken_over`). With no tools it
can say only what the instruction and the conversation say, never what a
record holds, so an automation cannot turn its owner's reach into a
channel's. It answers at most `ANSWERS_A_CONVERSATION` times a day in one
conversation for one automation, and not at all while OneAI or the agent is
off or the owner may no longer talk to it.

## The panel

`public/js/one_ai/panel/Panel.vue` reads and writes through `panel.py`: its
list is the reader's Agent conversations, a conversation opens from its
messages (each drawn as the panel always drew a turn, from `parts`), and
Send is `api.send` on that conversation. The agent is the one of the app the
page belongs to, when the reader reaches it, else Una (`agents.for_page`).
The small inline asks (`onedesk.oneai.quick`) are one line, "Ask {app}", that
answers under itself with the call they always made.

## Connections

- **From OneAI**: An agent answers with its own tools (one_ai/agents/talk.py), the panel is a conversation here, and an agent's Draft and Ask First land as cards in its conversation with the person asked.
- **From OneCloud**: A file is added to a message from OneCloud or the computer.
- **To One**: A mention and a direct message are told on the bell, and by email or push.

## Under the hood

- `manifest.py`, `access.py` (one role, OneChat User, given to everybody),
  `channels.py` (members and permissions), `messages.py` (writing, live,
  mentions, reactions), `agents.py` (Una and the app agents as members),
  `answers.py` (asking an agent and posting its answer), `transcript.py`
  (what the agent is sent of a conversation), `cards.py` (the door's
  cards), `api.py` (the island's calls), `panel.py` (the panel's calls),
  `trust.py`.
- `frontend/src/chat/`: `OneChat.vue` (the frame), `ChannelList.vue`,
  `Conversation.vue` (a conversation or a thread), `Message.vue`,
  `AgentCard.vue`, `Composer.vue`.
- `patches/roles.py` makes the role before the doctypes sync;
  `patches/conversations.py` turns each AI Chat into an Agent conversation
  with Una, once.
