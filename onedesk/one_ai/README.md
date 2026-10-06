# OneAI

OneAI is the assistant in every part of One. Ask it about your work, or how
something in One works, in your own words and language. It answers from your
own records and from One's guides.

OneAI never changes anything by itself. When you ask it to do something, it
suggests the change on a card. Nothing happens until you approve it.

## Opening OneAI

The round OneAI button in the corner opens the OneAI panel on any page. It
opens on **What would you like to do?**, with a few suggestions for that page.
It only offers what you could do there yourself.

- Type your question in the message box.
- **Attach a file** adds a file to your question, such as a receipt or a CV.
  A card made from it, such as an expense claim, keeps the file.
- **New conversation** starts again. The arrow at the top left lists **Your
  conversations**.
- After its first answer, OneAI names the conversation. Click the name to
  change it.
- The panel shows how many credits the conversation has used.

## Answers

OneAI reads your records as you. It can't read anything you couldn't open
yourself.

- The answer comes first. Below it are the records OneAI read, one as a card
  and several as a list. **Show more** shows the rest, and **Open List** opens
  them in their own list.
- A question about how One works is answered from the products' guides, with
  the section named. If the guides don't cover it, OneAI says so.
- **Knowledge**, under OneAI in the sidebar, holds notes administrators wrote
  for everyone, such as a policy or a glossary. OneAI reads them too.

## Cards

A card shows the record and each field OneAI would set. **See the changes**
lists them.

- **Approve** makes the change as you, with your permissions.
- **Refuse** leaves everything as it was.
- If the record changed after the card was made, the card is **Out of date**
  and changes nothing.
- On an open form, an approved card puts the change into the form. Each
  changed field shows what it was until you save.

**Suggestions**, under OneAI in the sidebar, lists your cards as **Waiting for
you**, **Done**, **Refused** or **Out of date**. A card's own page has
**Apply** and **Refuse**. Home counts the cards waiting for you.

## Writing in a field

A text field, such as a description or a note, has the OneAI mark beside its
label. Click it to **Write with OneAI**.

- An empty field offers **Write a first draft**.
- A field with text offers **Improve it**, **Make it shorter** and **Fix
  spelling and grammar**.
- You can also say what to write in your own words.

The text goes into the form, next to anything you haven't saved. Save as
usual. While the field still says what OneAI wrote, the mark is in full colour
(**Written by OneAI**). Once you change the text, it turns grey again.

On a settings page, a field you may not know has a small mark beside its
label. **Ask OneAI about this** explains the field and suggests a value on a
card.

The mail window has more, listed in OneMail's guide.

## What OneAI remembers

OneAI keeps short facts about you and your work when you ask it to, or when
you tell it something lasting. The answer then shows **Remembered**, with
**Undo**. Only you see them. Settings › **What OneAI Remembers** lists them to
change or delete.

## Choosing the model

The pill under the message box shows which model answers. **Automatic** uses
the model the workspace set for chat. Only administrators can choose another,
unless an administrator turns on **People Choose the Model** for the Chat
action. Your choice applies only to your own conversations.

Administrators set each action's model and extra instructions under OneAI ›
**Actions**. One's guide covers it under OneAI Actions, for the Workspace.

## Credits

Every answer uses OneAI credits. The plan gives some each month, and more can
be bought under Workspace › **Plan and Credits**. When the workspace has none
left, OneAI can't answer until credits are added.

**Credits**, under OneAI in the sidebar, shows what was used by model, action,
person or day. Only administrators see it.

## Who sees what

- Your conversations, memories and cards are yours alone.
- Everyone can read **Knowledge**. Only administrators change it.
- **Actions** and **Credits** are for administrators.

## Connections

- **From OneAdmin**: OneAdmin runs every OneAI answer on the model the workspace chose, or the default, and charges it to the workspace's credits. With too few credits, OneAI can't answer.
- **To One**: Home counts the cards waiting for you. **Actions**, **Knowledge**, **Credits**, **Conversations** and **Suggestions** are under OneAI in One's sidebar, and **What OneAI Remembers** is in Settings.
- **To OneIntake**: Each document, scan and photo that arrives is read with OneAI. Fields filled on a record show the OneAI mark.
- **To OneHR**: Applicants are screened, interviews prepared, interview recordings written out and grievances sorted with OneAI.
- **To OneMail**: The mail window has **Write with OneAI**, and a reply OneAI drafts opens there to edit and send.
- **To OneStudio**: Every extension is reviewed by OneAI before it can be turned on, and mended when it runs into errors.
- **To OneLegal**: The Subprocessors list names Cloudflare and Google, which run OneAI's models, and what they receive. The Privacy Policy says OneAI reads only what you can open.

## Under the hood

`docs/ONEAI.md` is the long form: the gateway, the credits, the actions and
why a model cannot write.

- `chat.py`: a conversation (`AI Chat`) and the panel's calls (`start`, `say`,
  `answer`, `rename`, `suggestions`, `cards`). The page travels as a pointer,
  never as the record's values.
- `run.py`: asks the account to run an action (`proxy.ai_run` on OneAdmin),
  with the workspace's model and extra instructions. `once` is a single call
  for other modules (OneIntake, OneHR's hiring, OneStudio's review and mend).
  `apply` and `refuse` settle a card. `set_action`, `reset_action` and
  `try_it` serve OneAI Actions.
- `tools.py`, `schema.py`, `groups.py`: the tools. A read runs as the session
  user. A create, edit or delete writes an `AI Proposal`. A tool's schema is
  read off its signature. `groups.py` picks the tools a request is given, and
  `more_tools` lets the model ask for another group.
- `proposals.py`: the card. Permissions are checked when it is written and
  again when it is applied, as an ordinary insert, save or delete. A card
  whose record moved past its `modified` is Stale.
- `touch.py`, `doctype/ai_touch`: writing in a field, and the mark. `AI Touch`
  keeps what was written, and the mark shows while the field still says it.
  OneIntake's `act.py` calls `wrote` for the fields it fills.
- `memory.py`: `about_record` (what the form's sidebar knows), `AI Memory`,
  `AI Knowledge`, and search over the reader's past conversations.
- `guide.py`: answers "how do I" questions from every module's README, above
  `## Under the hood`.
- `suggest.py`: what the panel offers on a page, from each module's
  `one_ai_suggestions`, only to somebody who holds the verb.
- `kind.py`: a doctype as a card, a tool and OneIntake need to know it, and
  whether a record of it is ready to be made.
- `files.py`: a file dropped on the panel, kept as an attachment on the
  `AI Chat`. Only the newest turn's files are sent whole.
- `instructions.py`: an action's instruction is the account's. It is emptied
  on a workspace after every migrate.
- `logos.py`: the model makers' logos, cached.
- `heads.py`: the head of an `AI Proposal` (its state, its sentence, Apply and
  Refuse) and of an `AI Action Setting`.
- `legal.py`: the subprocessors and the privacy clause OneAI adds to the
  agreements.
- `report/ai_credits`: the Credits report, from `proxy.ai_usage`, with the
  person read from the conversation.
- `custom/file.json`: `ai_generated` (Made by OneAI) on a File OneAI made.
- `evals.py`: the test bench. It sends real requests, runs on demand, is
  charged, and never runs in the test suite.
- `public/js/oneai.js`, `public/js/oneai/`: the panel (`Panel.vue`), a card
  (`Record.vue`), the records read (`Found.vue`) and the field marks.
- `hooks.py`: each module declares what OneAI reads (`one_ai_reads`),
  suggests (`one_ai_suggests`) and offers on a page (`one_ai_suggestions`),
  and what it is told about the page (`one_ai_page`), the reader
  (`one_ai_reader`) and the workspace (`one_ai_workspace`).
