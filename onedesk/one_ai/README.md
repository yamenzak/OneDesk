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
- Asked for several things that belong together, such as a new customer and a
  quotation for them, or a project and its first tasks, OneAI suggests them in
  one go, a card each. A card that needs another names it ("New Customer:
  Acme, from the card above"), and approving it approves that one first.
  **Approve All** approves every card of the answer, in order.
- If approving a card does not go through, OneAI is told why and suggests it
  again, corrected.
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

Any other field OneAI filled, such as a date, an amount or a customer, shows
the same mark beside its label while it still holds what OneAI put there. A
record made from a card says **Made by OneAI** under who created it. A record
OneIntake made says so in a note at the top until somebody marks it checked.

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
unless an administrator turns on **Allow Model Choice** for the Chat
action. Your choice applies only to your own conversations.

Administrators set each action's model and extra instructions under OneAI ›
**Actions**. One's guide covers it under OneAI Actions, for the Workspace.

## Credits

Every answer uses OneAI credits. The plan gives some each month, and more can
be bought under Workspace › **Plan and Credits**. When the workspace has none
left, OneAI can't answer until credits are added.

OneAI has no notifications of its own. Its notices live where they are about:
the credits (Credits Running Low, Credits Ran Out, sent the moment OneAI is
refused, Credits Added, Credits Expiring) and OneAI Changed in One; Extension
Fixed in OneStudio; Couldn't Read in OneIntake.

**Credits**, under OneAI in the sidebar, shows what was used by model, action,
person or day. Only administrators see it.

## Who sees what

- Your conversations, memories and cards are yours alone.
- Everyone can read **Knowledge**. Only administrators change it.
- **Actions** and **Credits** are for administrators.
- An administrator can turn OneAI off for the whole workspace in **Apps**, at
  the bottom of the rail. Then nobody can ask it anything, nothing calls a
  model, and OneIntake goes off with it. Conversations and memories stay.

## Connections

- **From OneAdmin**: OneAdmin runs every OneAI answer on the model the workspace chose, or the default, and charges it to the workspace's credits. With too few credits, OneAI can't answer.
- **To One**: Home counts the cards waiting for you. **Actions**, **Knowledge**, **Credits**, **Conversations** and **Suggestions** are under OneAI in One's sidebar, and **What OneAI Remembers** is in Settings.
- **To OneIntake**: Each document, scan and photo that arrives is read with OneAI. Fields filled on a record show the OneAI mark.
- **To OneHR**: Applicants are screened, interviews prepared, interview recordings written out and grievances sorted with OneAI.
- **To OneMail**: The mail window has **Write with OneAI**, and a reply OneAI drafts opens there to edit and send.
- **To OneStudio**: Every extension is reviewed by OneAI before it can be turned on, and mended when it runs into errors.
- **To OneLegal**: The Subprocessors list names Cloudflare and Google, which run OneAI's models, and what they receive. The Privacy Policy says OneAI reads only what you can open.

## Under the hood

The files come first. After them: where the money lives, the gateway, the
catalogue, credits, how a call is billed, which model answers, and what is
deliberately not here.

- `chat.py`: a conversation (`AI Chat`) and the panel's calls (`start`, `say`,
  `answer`, `rename`, `suggestions`, `cards`). The page travels as a pointer,
  never as the record's values.

  A conversation is kept rather than held in a tab, because a chat that dies
  when the tab does is one nobody starts anything long in. `AI Chat` holds a
  title, when it was last said to, what it has cost, and the turns: the same
  turns the gateway speaks, because the conversation *is* the turns and a
  second shape beside them is a second shape to keep in step.

  **The page is a pointer, not a payload.** What travels is the route: the
  doctype, the record's id, which view. Not the record's values: the model has
  `read_record` for that, and that runs as whoever is signed in, so a pointer
  at something the reader may not see buys nothing. It also keeps a
  conversation honest over time: the context of the third message is where
  they were for the third message, not where they are now.

  What the person just dropped on the panel goes to a tool that attaches what
  it read to what it suggests, a receipt to its claim. Only this question's
  files: a receipt dropped three questions ago is not evidence for whatever is
  being asked now.

  **What earlier questions read is sent cut down.** The whole conversation is
  sent on every round, so a hundred rows read three questions ago were paid
  for again on every round of this one. `lighter` sends a few rows of each
  earlier tool answer and the start of each long text, saying how much was
  left out; what answers this question goes whole, and `_whole` puts the
  full answers back before the conversation is kept, so the panel still
  shows every row it showed.
- `run.py`: asks the account to run an action (`proxy.ai_run` on OneAdmin),
  with the workspace's model and extra instructions. `once` is a single call
  for other modules (OneIntake, OneHR's hiring, OneStudio's review and mend).
  `apply` and `refuse` settle a card. `set_action`, `reset_action` and
  `try_it` serve OneAI Actions.

  Two things travel with the call and neither is the instruction: which model
  this workspace picked, and what it asked to have added. The instruction
  itself is the account's, read from its own copy of the fixture, and there is
  nothing a workspace can send that replaces it. Everything here is one round
  trip and no decision. Whether the action exists, whether the model may
  answer it, whether there are credits: all of that is admin's, for the same
  reason a workspace cannot sign its own upload URL.

  `ask` runs one action, looking things up for the model where it asks. The
  loop is here rather than on the account, and that is the whole shape of it:
  the model is on the account and the records are here, the account never
  calls a workspace, and a tool means nothing unless it runs as whoever is
  signed in. So the workspace asks, is told what the model wants, looks it up
  with its own permissions, and asks again. A tool that refuses comes back as
  a result saying so rather than as an exception. A model told "you may not
  see that" can say so; a model told nothing at all writes something plausible
  instead.

  `pinned` is the model the person picked in the panel for this conversation.
  It wins over what the workspace chose, and goes with the conversation when
  another action takes it over: somebody who picked a model was asked by
  nobody to have it swapped for them halfway. `heard` is told each thing as it
  happens (a round starting, a tool it ran), so a panel watching a background
  run can say what it is doing rather than that it is busy.

  Within the loop:
  - The model reached for a tool that another action runs, on a model that
    does it well: Print Design lays a page out, which the chat's small model
    gets wrong. That action takes the conversation from here, asked the same
    thing again, and keeps it to the end of the run; its calls are charged to
    it.
  - A suggestion that exists to make a card ("Draft my feedback") answered
    with the draft in the chat and no card is asked for the call it was for,
    with what it just wrote. Not when it ended by asking the person something:
    that is theirs to answer, and the card comes after.
  - Measured on Gemma 4: asked for a scheduled extension with only the
    reader's own tools given, it answered "I do not have a tool for that, but
    I can write an extension with write_extension". Before saying it cannot,
    it looks at every tool there is.
  - A tool's turn holds what the tool answered, and nothing else. The
    bookkeeping sits beside it rather than inside it, because `result` is the
    only part a provider is sent, and a model handed
    `{"tool": ..., "ran": ..., "answer": [...]}` quotes the wrapper back at the
    reader as if it were the answer.
  - What a round parked is somebody's to answer, and a round that fails after
    it should not take it away. It is committed each round rather than at the
    end of the request, which on a run with five model calls in it is minutes
    off, and a transaction held open across all of them is a transaction
    holding locks across all of them.
- `tools.py`, `schema.py`, `groups.py`: the tools. A read runs as the session
  user. A create, edit or delete writes an `AI Proposal`. A tool's schema is
  read off its signature. `groups.py` picks the tools a request is given, and
  `more_tools` lets the model ask for another group.

  `tools.py` is what a model may ask for, and what it may only suggest.
  Everything a person can do here a tool can do (read a list, read a record,
  count, look at a type, create, edit, delete), and the difference between the
  first four and the last three is the whole of its design.

  **A read runs. A create, an edit or a delete becomes a card.** Nothing in
  `tools.py` writes. A write tool checks the asker's permission for the verb,
  writes an `AI Proposal` and hands back its id, and the doing happens when a
  person presses Apply. A tool that saved would be a tool that saves on a
  model's say-so, and the failure mode is not a wrong field: it is a wrong
  *record*, at the end of a chain of lookups nobody read.

  **Every tool runs as the session user.** Not as Administrator with a filter
  bolted on afterwards, and not with `ignore_permissions` anywhere: the same
  `frappe.get_list` the browser would have called, under the same permissions,
  so a model asked about somebody else's salary gets what that person would
  get, which is nothing. This is the one rule in `tools.py` with no exception
  and no override, and a tool that needs more than its caller has is a tool
  that does not ship. Reading the whole of Frappe this way is the point. The
  alternative is a hand-written tool per doctype, which is out of date the
  week somebody adds a field.

  A link filtered on a record that does not exist matches nothing, and an
  empty answer reads to a model as "there are none" ("Annual" for a leave type
  called "Annual Leave"). A read changes nothing, so the one record it plainly
  meant is used; anything less plain is said, with the values there are, and
  the model left to choose.

  `search_everywhere` is frappe's own search: the workspace's Global Search
  Settings say which types are indexed, and every hit is checked with
  `has_permission` on the record itself before it is answered, so nothing the
  reader may not open is named.

  `KEEPS` is what runs at once although it writes: only the asker's own
  memory, which no one else reads and they see and delete in the memory list.
  A card asking them to approve "Omar is our CFO", which they just said, was a
  card nobody wanted, and a line saying so in the chat was noise.

  `schema.py` is pure, and small on purpose. The alternative is a schema
  beside every function, and the failure mode of that is not an error: it is a
  model told a parameter is a string when it is a list, calling the tool
  correctly according to what it was told, and being refused. Nobody finds
  that by reading either half. So the signature is the schema. `Annotated`
  carries the description, a union with `None` or a default says a parameter
  may be left out, and `Literal` is a closed list, which is the one that
  matters most, because a model given an open string where three values are
  allowed will eventually invent a fourth.

  A Python type not in `CALLED` is refused rather than guessed at: a parameter
  whose type nobody wrote down is a parameter a model has to be told about in
  prose, and prose is the thing `schema.py` exists to avoid. `list[str]` and a
  bare `list` both become an array with `items`. Google refuses an array
  without `items` (measured: gemini-2.5-flash-lite answers 400 with
  "properties[fields].items: missing field") while OpenAI's dialect accepts
  it, so the stricter reading is the one written.

  `groups.py` decides which tools a request is given. OneAI has some 120
  tools, and a model handed all of them on every round reads every one of them
  every round and picks among them all: measured, Gemma 4 reached for
  `search_everywhere` to find an extension, and the 120 cost some 20,000
  tokens a round. So the tools are grouped, and a request is given the tools
  everybody needs (`CORE`, the `you` group and `more_tools`) and the groups it
  looks like it needs:
  - the group of the page the person is on (`MODULES`, `DOCTYPES`, `PAGES`);
  - a group whose words the request uses (`words`, in English, German and
    Arabic: a guess, and a cheap one);
  - a group the conversation already used, so a follow-up keeps its tools and
    the provider's cache keeps what it has.

  None of that is a wall. `more_tools` names every group and what it is for,
  so the model knows all One can do and asks for a group it was not given; it
  has it on the next round. A guess that misses costs a round, never an
  answer. The groups are declared in `groups.py` rather than worked out from
  module paths, because a group is what a person asks about (their mail, the
  workspace's setup), and that is not always where the code lives: `one/ai.py`
  holds both somebody's own day and the workspace's numbering.
- `proposals.py`: the card. Permissions are checked when it is written and
  again when it is applied, as an ordinary insert, save or delete. A card
  whose record moved past its `modified` is Stale.

  **A card may point at another card.** A value of `@PROP-26-000042` is the
  record that card will make: the quotation's customer, the task's project.
  `_chained` checks each pointer when the card is written (the asker's own
  card, still waiting or already approved, making the kind the field links
  to), replaces one already approved by what it made, and keeps the rest as
  `needs`. `kind.ready` then makes the needed records first inside the same
  rolled-back savepoint, so the quotation is checked against its customer.
  Approving a card approves what it needs first (`_made_first`), in the same
  request, so a failure undoes both. `apply_all` is **Approve All**: the cards
  of one answer in the order they were suggested, which is the order they
  point at each other in; a reply or a mail is left for the panel, which
  opens it. `create_records` suggests a set in one call, each record naming
  an earlier one by its own `ref`, so a chain costs one round rather than
  one per record.

  A pointer is a value rather than a link to a draft record because there is
  no draft record: nothing exists until a person approves, and a half-made
  customer left behind by a refused quotation is the failure this avoids.

  **A model cannot write.** What it can do is put a card in front of somebody
  (this record, these fields, that value), and the doing happens afterwards,
  in a request a person made by pressing Apply, down the same path they would
  have taken by hand. The split is not a formality. A tool that saves is a
  tool that saves on a model's say-so, and the failure mode is not a wrong
  field: it is a wrong *record*, at the end of a chain of lookups nobody read.
  A person between the asking and the doing also puts the diff in front of
  them while they decide.

  **Permissions are checked twice and never bypassed.** Once when the proposal
  is written, so a model cannot suggest something the asker could not do; and
  again when it is applied, as an ordinary insert, save or delete by whoever
  pressed the button. There is no `ignore_permissions` in `proposals.py` and
  there is not going to be one.

  **An edit that would overwrite somebody else's is refused.** A proposal
  carries the record's `modified` from when it was written; if the record has
  moved since, the proposal is stale and says so. Applying it anyway would be
  a model's diff quietly undoing a person's.
- `touch.py`, `doctype/ai_touch`: writing in a field, and the mark. `AI Touch`
  keeps what was written, and the mark shows while the field still says it.
  OneIntake's `act.py` calls `wrote` for the fields it fills. Every field is
  kept, not only prose (`UNMARKED` lists what is not), and compared by its
  type, so 100 and "100.0" are one value. `onload` also says when the record
  was made by an approved Create card (`ai_made`), which the form shows as
  **Made by OneAI** under Created By.
- `heal.py`: what an error tells the model to do next. A tool that fails
  answers with the server's own error, as it was sent and with its kind
  (`MandatoryError: [Quotation, new]: party_name`), because that is what a
  model reads most easily. On a line of its own under it, `What to do:` says
  what mends that kind: a missing field by its label and where to find a
  value, a record that cannot be found with the tool that finds it, a
  duplicate with the one that exists, the arguments a tool really takes, the
  nearest tools to one that does not exist. A refusal says not to try again.
  Only the software's own name is taken out of the message. The panel shows
  the person the first sentence, without the kind or the fix. In the panel, a card that fails at Approve is sent
  back as a message saying why, and the model suggests it again.

  **One path, not two.** The control beside a prose field opens the same
  panel as the launcher, pointed at that field. What comes back is an
  `AI Proposal` of kind Edit (the same card, the same Apply), so "help me
  write this" and an agentic edit are one thing to trust rather than two. The
  difference is only where Apply lands: with the form open, the text goes
  *into the form*, beside whatever the person has typed and not saved, and
  they save it the way they save anything. A server-side save there would
  either lose their edits or be refused as stale.

  **The badge is a comparison, not a flag.** `AI Touch` holds what was
  written. The form is handed the fields that still say it, and the badge
  shows while they do. A person's edit makes them differ and the badge is
  simply no longer true, without a hook on every doctype's write path, and
  without anybody having to remember to clear it. Text is compared as text:
  tags stripped and whitespace collapsed, because a Text Editor wraps what it
  is given in its own markup and would otherwise differ from what was written
  the moment it was drawn.
- `memory.py`: `about_record` (what the form's sidebar knows), `AI Memory`,
  `AI Knowledge`, and search over the reader's past conversations.

  Three kinds, kept apart because they have three different owners:
  - **the records themselves**, read live. `about_record` is everything the
    form's own sidebar knows about one record (its fields, what links to it,
    its comments, mail, changes, assignments and files) through the same
    frappe functions the sidebar calls, so it is never a copy that went stale
    and never more than the reader may open;
  - **a person's own memory** (`AI Memory`), short facts somebody told OneAI
    to keep. Private to them like their conversations, kept at once and
    quietly (it is what they just said), and seen and deleted in the memory
    list. The same fact twice is one memory, and a correction replaces what it
    corrects;
  - **the workspace's knowledge** (`AI Knowledge`), what an administrator
    wrote down for everybody: a policy, a glossary, how things are done here.

  And a fourth that is not stored at all: the reader's own past
  conversations, searched rather than summarised into anything. None of it is
  pasted into every turn. A few memories and the knowledge for the type on
  screen are; everything else is a tool the model calls, because whatever is
  sent is paid for on every message.

  Every read of AI Memory names the owner as well as relying on the doctype's
  if-owner rule: Administrator is not held by if-owner, and a memory read into
  somebody else's conversation is the one leak `memory.py` must not have.
- `guide.py`: answers "how do I" questions from every module's README, above
  `## Under the hood`.

  "How do I register my passkey?" is a question about the product rather than
  about the workspace's records, and a model answers it from what products
  like this usually do, which is how a person is told to find a button that
  is not there. Each module's `README.md` says what it does for the people
  using it, so `how_to` hands the model the sections that match and tells it
  to answer from those alone, naming the section. Everything above a README's
  `## Under the hood` heading is for the people using the module, and
  everything below it is for the people building it, so the reading stops
  there: file names and upstream faults are no help to somebody asking where
  their payslips are.

  `ranked` orders the sections first by how many of the different words a
  section holds, then by the words in its heading, then by how often they come
  up, because a long section mentions everything once, and counting mentions
  alone made the longest section the answer to every question. A section
  holding fewer than half the words is not an answer, so a question the
  documentation does not cover gets nothing rather than the nearest paragraph.
- `suggest.py`: what the panel offers on a page, from each module's
  `one_ai_suggestions`, only to somebody who holds the verb.

  Not buttons on every screen: the panel is already one press away from all
  of them, and a form carrying an AI button per feature is a form nobody
  reads. So the panel opens on "What would you like to do?" and offers the few
  things that make sense here: a receipt on an expense claim, a summary on a
  record. That includes the things OneAI does without a conversation, like
  reading an applicant's CV again: a suggestion with `run` calls that method
  on the open record, and the panel says what is happening. No OneAI button
  goes on a page.

  Each module owns its own, named in `hooks.py` under `one_ai_suggestions` as
  a dict of doctype to suggestions. A suggestion is offered only to somebody
  who holds the verb it names on that doctype, because offering to make a
  claim to a person who cannot make one is offering a refusal. A suggestion
  with `when` is for a record in one state only: "why did this job fail?" on
  a job that did not fail is a question with no answer. Labels and questions
  are `_lt`, so each is in the reader's language: the question is what the
  panel shows as theirs, and what it sends. `fill` puts the question in the
  panel's box to be finished by the reader ("Draft a reply that says: …")
  rather than asking it at once.
- `kind.py`: a doctype as a card, a tool and OneIntake need to know it, and
  whether a record of it is ready to be made.

  One place for OneAI's cards and tools and for Intake, so each reads a kind
  the same way and a new required field, a Customize change or a naming
  choice reaches all of them at once.
  - `describe` is every field a person could fill: its type, what it may
    hold, whether it is required or the system fills it, and how a new record
    of the kind is named (`naming`), which is the one thing frappe asks for
    that is not a field.
  - `fields_of` is the same, cut to a line per field, for a message to a
    model.
  - `missing` is what a record still needs before frappe saves it: its
    required fields, frappe's own list, and its name when the kind is named by
    a field or typed by whoever makes it.
  - `ready` runs frappe's own checks on a record that is never saved and says
    what would stop it: links, the kind's own validate, and `missing`.

  In `fields`, hidden fields are left out (that is how a workspace takes a
  field away, Company among them), and so is anything the reader may not see.
  A field the system fills (read only, or fetched from a link) is said to be,
  so the model neither asks for it nor invents it. Printing, what only filling
  needs (required, defaults, what the system fills) is left out, and a field
  frappe's own formats leave off the page is said to be, since most of a
  document of trade's fields are.

  In `ready`, the record is inserted exactly as Approve will insert it,
  inside a savepoint that is always rolled back, then what is still
  `missing` is said. Running `validate` alone, as it once did, refused every
  quotation for a price list currency and a unit that the insert fills in by
  itself (measured on the demo: a quotation of one customer and one item
  inserts, and failed the check). A model told "Leave Approver is missing" asks the person; a card
  that fails when they press Approve teaches them the cards do not work.
- `files.py`: a file dropped on the panel, kept as an attachment on the
  `AI Chat`. Only the newest turn's files are sent whole.

  Being an ordinary attachment on the `AI Chat` row, the file has an owner, a
  permission and a place in the workspace rather than living inside a
  conversation nobody can find again. What travels to the model is its bytes,
  base64'd, because the account cannot read a workspace's disk: the same
  reason a tool runs here and not there. The conversation is sent whole every
  round, so a 3 MB attachment on a five-round run is fifteen megabytes of HTTP
  for one question. Older files stay in the transcript by name, which is what
  a person reads them as anyway.
- `instructions.py`: an action's instruction is the account's. It is emptied
  on a workspace after every migrate.

  `AI Action` is a fixture, so a new action arrives with a migrate and every
  site gets the row: the label, the capability and the token caps, which is
  what a workspace needs to pick a model and add to the prompt. The
  **instruction** is not part of that. It is how the product behaves, a
  workspace cannot change it, and `proxy.ai_run` has always read it from the
  account's own copy and ignored anything sent with the call. Shipping it and
  then declining to render it would be a curtain rather than a wall: the row
  is in the workspace's database, and `frappe.client.get` reads it. So on a
  workspace the field is emptied after every migrate, and there is nothing to
  read.
- `logos.py`: the model makers' logos, cached.
- `heads.py`: the head of an `AI Proposal` (its state, its sentence, Apply and
  Refuse) and of an `AI Action Setting`.
- `legal.py`: the subprocessors and the privacy clause OneAI adds to the
  agreements.
- `tell.py`: the notification when an action's model or added instructions
  change (OneAI Changed), sent to the other administrators.
- `report/ai_credits`: the Credits report, from `proxy.ai_usage`, with the
  person read from the conversation.

  The chart's labels are the day of the month and nothing more. frappe-charts
  allows two or three letters a label at thirty bars and cuts anything longer
  to dots, and the report view overwrites the option that would thin them out.
  The period itself is in the filters above the chart.
- `custom/file.json`: `ai_generated` (Made by OneAI) on a File OneAI made.
- `evals.py`: the test bench. It sends real requests, runs on demand, is
  charged, and never runs in the test suite.

  The bench is real requests, asked the way the panel asks them, and what a
  right answer must have done. It is what says whether a change to OneAI, or a
  different model, made it smarter or only different. Run on demand, never by
  the test suite, because every case is a real call and is charged:

      bench --site <site> execute onedesk.one_ai.evals.run
      bench --site <site> execute onedesk.one_ai.evals.run --kwargs '{"model": "google-ai-studio:gemini-2.5-flash"}'
      bench --site <site> execute onedesk.one_ai.evals.run --kwargs '{"only": "mail"}'

  Each case is asked as `user` from `page`, through `run.ask` with the same
  context turn the panel sends. It passes when the run called one of `tools`
  (or none, for `tools=()`), made a card if `card`, and said something. What
  it wrote is not graded: the cards and the tools are where a wrong answer
  shows, and a judge model would grade its own kind. Cards and memories a
  case made are taken away after it.
- `public/js/oneai.js`, `public/js/oneai/`: the panel (`Panel.vue`), a card
  (`Record.vue`), the records read (`Found.vue`) and the field marks.
- `hooks.py`: each module declares what OneAI reads (`one_ai_reads`),
  suggests (`one_ai_suggests`) and offers on a page (`one_ai_suggestions`),
  and what it is told about the page (`one_ai_page`), the reader
  (`one_ai_reader`) and the workspace (`one_ai_workspace`).

### doctype/ai_action

`AI Action` is one thing a model is asked to do, and the instruction it is
asked with. It is a fixture, so a new action arrives with a migrate and an
operator's edit to one survives the next. It exists on every site because a
workspace has to know what it may ask for, but **the copy that decides is the
one on the administrator**, which is where a call is made from. A workspace
editing its own copy changes nothing, and the permissions say so: only the
operator role may write here, and nobody on a tenant site has it.

### doctype/ai_action_setting

`AI Action Setting` is what a workspace wants one action to run on, and what it
wants added. The model is a name on the administrator rather than a link,
because the catalogue lives there and a workspace holds no copy of it: the
picker asks for the list and stores what was chosen.

`extra` is the whole of what a workspace may say to a model, and it is
**added** to the action's own instruction rather than replacing it. That
distinction is the safety of the feature: a workspace can tell the summariser
to write in Arabic and keep it terse, and cannot tell it to ignore what it was
told about what it may touch.

### Where the money lives

The ledger is on the account (the OneAdmin site), not on the workspace.
`Credit Ledger Entry`, `Credit Reservation`, `AI Model` and its rates live
there, behind `one_admin/proxy.py`. A workspace reaches them the way it gets a
signed upload URL: it asks, holding a token that names it and authorises
nothing else. The account never calls a workspace.

- A balance is a sum over ledger rows, on a database the customer cannot reach.
- Only the Stripe webhook and the operator insert a row, and both run on the
  account.
- `ledger.py` is the only code that knows where a balance comes from.

What stays on the workspace is what people touch: action settings, runs,
conversations, cards. Putting those on the account would cost a round trip to
draw a screen.

### The gateway

Every call goes through Cloudflare AI Gateway (`one_admin/gateway.py`). The
provider keys are stored in the gateway. The account holds a gateway token
and the Cloudflare account id; a workspace holds neither. The gateway also
gives caching, retries, rate limits, a spend limit of our own and a request
log tagged with the workspace.

Two providers: Workers AI (`workers-ai`) and Gemini (`google-ai-studio`). Each
is a row in a table of path, body and where the words are, not a branch in
code. A 200 whose shape we don't recognise raises, so a changed response
can't quietly come back blank.

### The catalogue

`one_admin/catalogue.py` syncs `AI Model` nightly: what exists and what it can
do from each provider's API, and the price from the page each provider
publishes (`one_admin/prices.py`, with saved pages in `tests/samples/`).

- A rate is (kind, modality, unit, cost for N). Nothing converts between
  units: Gemini bills tokens by modality, Workers AI bills text per million
  tokens, pictures per tile and per step, speech per minute.
- A model with any price the parser couldn't read lands as `Needs Review`,
  with the wording that beat it. There is no default price.
- `priced_by_hand` makes the rate rows editable, and the sync then leaves the
  rates alone. That is how Veo and Lyria are sold.
- Two prices for the same thing is a gap. Gemini 2.5 Pro prices prompts under
  and over 200k tokens differently, and there is no field for context length,
  so the parser says so rather than picking one.
- The sync never decides whether a model is offered. It only takes a model off
  sale when it can no longer be priced, and marks one gone when the provider
  withdraws it.
- A model's capability is two facts: what it makes, and what it can be fed
  (`reads_*`). The one word on the list (Text Generation, Vision, Multimodal,
  and so on) is derived from both in `one_admin/capability.py`. The provider's
  word is a floor and the published rates raise it: `gemini-2.5-flash-lite`
  says text, but its price page has rates for pictures, sound and video.

### Credits

Customers buy credits, not tokens, so a provider re-pricing a model is our
problem rather than an announcement. A credit is `credits_per_dollar` of
provider cost times a markup: the model's own `markup`, or `default_markup` in
One Admin Settings. Neither has a default; an unset markup refuses the call.

`balance()` sums the ledger and is never a stored field.

- A grant that does not roll over has `expires_on`, and only unexpired grants
  count. Expiry is arithmetic, not a nightly job.
- A spend names the grant it drew from, soonest-expiring first, so a free
  monthly grant is used before bought credits. The ledger is append-only.
- A spend nothing covers is owed, and does not expire.

### A call, in three steps

1. Hold a ceiling: price the action's caps (`max_output_tokens` and the rest)
   and reserve that many credits. Every read the hold rests on is a locking
   read: measured, two processes holding seven of ten credits both succeeded
   with a plain `SELECT`, because InnoDB reads from the transaction's first
   snapshot.
2. Make the call through the gateway.
3. Settle what the provider reported and release the rest.

Every number billed is either reported by the provider or a parameter we
sent, and each `Use` says which (`asked`). Nothing is worked out from the
length of a string. Gemini's `usageMetadata` gives tokens per modality;
Workers AI reports text tokens only, so its pictures and speech are billed
from what we asked for. Cached tokens are taken off the input line, since
Google counts them in both.

- A call that answered but can't be metered is charged its hold and flagged.
- A call that failed releases its hold.
- `ledger.nightly` lets go of holds whose call never came back.

### Which model answers

An `AI Action` (fixture) names a capability; an `AI Action Setting` names a
model. With no setting, the action runs on the operator's default model for
its capability. For a conversation the order is: the person's pick
(`AI Chat.chosen_model`), then the workspace's setting for the chat action,
then the default. The account checks the pick again at call time, and
`pinned` keeps it through a handover.

`chat_title` names a conversation after its first answer: a 30-token action
with no tools. Once its person renames it, `titled` is set and OneAI never
names it again.

### Background runs

A generation takes two to forty seconds, and a gunicorn worker held for that
answers nothing else. So a run is a background job: the browser gets a run id
at once and subscribes. Progress goes out with `frappe.publish_realtime`
through redis to the socketio the bench already runs.

### How OneAI looks

Anything of OneAI's on screen is drawn in its spectrum with its mark: the
launcher's ring, the panel's edge, a field it wrote. Pages use two shared
parts in `public/js/oneai.js`:

- `onedesk.oneai.tag(label)`: frappe's badge with the mark in front, for
  something OneAI does or did ("Read by OneAI").
- `onedesk.oneai.button(label, ask)`: frappe's button, drawn the same way. It
  opens the panel on `ask`, the same question the page's suggestion asks.
  Inside a dialog it closes the dialog first.

`tests/guards/test_ai_look.py` fails on anything that badges OneAI by hand.

### What is deliberately not here

- No model named in application code. The one exception is `gateway.FIRST`,
  the model the operator's token test calls, and `tests/test_gateway.py`
  holds it to that.
- No estimate is ever billed.
- No second runtime: redis, socketio and the background queue the bench
  already has.
- No provider key on a workspace, and no bring-your-own-key. That would be a
  support burden, a billing hole and a place for a key to leak. A workspace
  that wants another model asks the operator to add it to the catalogue.
