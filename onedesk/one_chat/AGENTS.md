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
