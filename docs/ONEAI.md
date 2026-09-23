# OneAI — models, credits, and what a model is allowed to do

Nine things arrive together and only make sense together: a gateway, a model
catalogue that keeps itself true, prices nobody types, a markup, a credit
ledger, a top-up, an action a workspace can re-point and re-word, tool calling
that cannot reach past the person who asked, and a call a browser watches
arrive. This is the argument for each and the order to build them in.

The desk has none of it today. `modules.txt` is One, One HR, One CRM and One
Admin; the operator side and the billing exist, and there is no AI.

## The decision that shapes the rest

**The operator is a separate site, and the ledger is on it.** `docs/INFRASTRUCTURE.md`
is the whole of that argument; what matters here is the consequence, which is
that a workspace has no credit table to write to. `Credit Ledger Entry`,
`Credit Reservation`, `AI Model` and its rates all live in One Admin on the
admin site, behind `one_admin/proxy.py`, and a tenant reaches them the same way
it reaches a signed upload URL: by asking, one direction only, holding a token
that identifies it and authorises nothing else.

So the three rules that used to be deterrence are now structural:

* A balance is a **sum over rows** on a database the customer cannot reach.
* Only two things insert a row — the Stripe webhook and the operator — and both
  run on admin.
* Nothing admin holds is reachable from a workspace, because admin never calls
  a workspace and a workspace can only call the endpoints in `proxy.py`.

**An earlier draft of this document said the opposite**, and said plainly that
it was the design's weakest point: the operator as a role on the tenant's own
site, the ledger beside the data it bills for, and an administrator who could
write themselves credits if they reached the database. That is what INFRA 5
replaced. The shape above it did not change — the gateway, the actions, the
tools and the proposals are what they always were — which was the point of
keeping `ledger.py` the only thing that knows where a balance comes from.

**What is still on the tenant's own site** is everything a person touches: the
action settings, the runs, the proposals. Those are the workspace's own records
about its own work, and putting them on admin would mean a round trip to draw a
screen.

## One gateway, and the keys are not here

Every call reaches a provider through **Cloudflare AI Gateway**. The provider
keys are stored in the gateway, so a tenant site never holds one: it holds a
gateway token and the account id, and the key stays at Cloudflare.

What the gateway is for, beyond that: caching, retries, rate limits, a spend
limit that is ours rather than the provider's, and a per-request log tagged with
the workspace. A direct call to Gemini would need none of that written, and it
would need all of it built.

Two providers to begin with, both through it: **Workers AI** — the local models,
running at the edge — and **Gemini**.

## The catalogue keeps itself true

Providers ship models weekly and re-price them without an announcement. A table
of models and prices typed by hand is wrong inside a month and the way you find
out is a margin rather than an error. So it syncs:

* **what exists, and what it can do** — from each provider's own API.
* **what it costs** — parsed from the page each provider publishes.

Four rules hold it up.

**There is no single unit.** Gemini bills everything in tokens by modality,
generated pictures and speech included. Workers AI bills text per million tokens,
pictures per tile and per diffusion step, speech per audio minute. So a rate is
`(kind, modality, unit, cost for N of them)` and **nothing converts between
units**. A price schema that flattened all of this to "tokens" would be wrong
for half the catalogue and silently.

**A model nothing could price is not sellable, unless a person prices it.** The
parser returns what it could not read alongside what it could, and a model with
a gap lands as `Needs Review` carrying the wording that defeated it. There is no
default price, because the failure mode of a default is billing somebody a
number we invented.

A person typing one is a different thing: `priced_by_hand` makes the rate rows
editable and the sync then leaves them alone while still refreshing everything
else. That is what makes Veo and Lyria sellable — Veo prices a second of video
and differs by resolution, Lyria prices a song, and neither shape fits a table
this reads. A hand-typed output rate also settles what the model *makes*, which
is the only statement Google's API gives us about Lyria at all.

**Two prices for the same thing is a gap, not a coin toss.** Found by the guard
rather than by reading: Gemini 2.5 Pro prices a prompt under 200k tokens at
$1.25 and one over it at $2.50, and the parser was keeping the first and billing
every long prompt at half price. A context length is a dimension this schema has
no field for, and inventing one to carry an unused distinction is worse than
saying so.

**The sync never overrules the operator.** It creates rows and refreshes facts.
Whether a model is *offered* is a decision and stays one. The only two decisions
it makes on its own are the ones it must: a model that stopped being priceable
comes off sale, and a model the provider withdrew is marked gone.

**A capability is what the picker filters on, and it is two facts rather than
one word.** A model carries what it *makes* and what it can be *fed*, the second
being a set, and the one word on a list is derived from both — Text Generation,
Vision, Multimodal, Transcription, Image Generation, Video Generation, Audio
Generation, Embedding. An action declares what it needs and the picker filters
on `reads_*` and the word together, so nobody picks a model that cannot do the
job and finds out at the call.

One word was not enough, and the first version of this proved it:
`gemini-2.5-flash-lite` was filed as text generation because that is what its
API said it could be *called* with, while its own price page carries input rates
for text, pictures, sound and video. So the provider's word sets a floor and the
published rates raise it. `one_admin/capability.py` is pure and holds the whole
of that decision.

## Credits are abstract, and the balance is a sum

Customers buy **credits**, not tokens. Deliberately: a provider re-pricing a
model, or an action moving to a cheaper one, is then our problem rather than a
pricing announcement to every customer.

A credit is a fixed number per US dollar of provider cost, times a **markup**
held per model with one fallback for a model that has none. Both are the
operator's, in OneAdmin, and neither is guessable from the catalogue — the
providers publish what a call costs them, never what it should cost anyone else.

`balance()` is a sum over `Credit Ledger Entry`, never a stored field, so it
cannot drift out of agreement with its own history. Two rules do most of the
work:

* A grant that does not roll over carries `expires_on`, and the balance only
  counts unexpired rows.
* Spend draws down the **soonest-expiring grant first**, so nobody loses credits
  they bought while a free monthly grant sits unused beside them.

**Reserve, then commit.** Reading a balance and then spending against it is a
race — two calls at once both see five credits and both spend four. A reservation
is taken under a row lock before the call and settled after it, which makes the
check-and-hold one atomic thing.

## A call is three steps and only the middle one is expensive

1. **Hold a ceiling.** Price the action's declared limits — its `max_output_tokens`
   and whatever else it caps — and reserve that many credits. It is a cap, not a
   forecast: the point is that two calls cannot both spend the last credit.
2. **Make the call**, through the gateway.
3. **Settle the actual.** The units the provider *reported* are charged and the
   rest of the hold is released.

Step three is where "never estimate" is either true or a slogan. Every number is
either returned by the provider or is a parameter we sent. Nothing is derived
from the length of a string. The two providers report differently and that is the
whole reason the rate schema is unit-aware: Gemini's `usageMetadata` carries
token counts per modality for prompt, cache and output, so a multimodal call is
exactly meterable; Workers AI reports tokens for text and nothing at all for the
rest, so pictures and speech are metered from what we asked for, which we know.

A call the provider answered but we could not meter is charged its hold and
flagged, never charged zero.

## An action is a fixture, and a workspace may re-point it

An **AI Action** is the unit an app declares and an operator edits: a key, a
label, the capability it needs, the system instruction we wrote, and the limits
that price its ceiling. They ship as fixtures, so a new one arrives with a
migrate and an operator's edit to one survives the next.

Beside it, per workspace, an **AI Action Setting**: which model this workspace
wants for it, and **extra system instructions that are appended and never
replace ours**. That distinction is the whole safety of the feature — a customer
can tell the summariser to write in Arabic and keep it terse, and cannot tell it
to ignore what it was told about what it may touch.

An action with no setting runs on the operator's default model for its
capability. Nothing is ever asked "which model" at the call site: a workspace
picks a model on a settings screen or does not, and the code that calls the
model never names one.

## A model cannot write

What a model can do is put a card in front of somebody — *this record, these
fields, that value* — and the doing happens afterwards, in a request a person
made by pressing Apply, down the same path they would have taken by hand.

The split is not a formality. A tool that saves is a tool that saves on a model's
say-so, and the failure mode is not a wrong field, it is a wrong *record* at the
end of a chain of lookups nobody read. A person between the asking and the doing
also puts the diff in front of them while they decide.

One doctype, `AI Proposal`, and a kind. Applying it is an ordinary `frappe`
write, with the ordinary permission check, made by the person who pressed the
button.

## Tool calling cannot reach past the person who asked

A tool is a Python function with type hints, and its JSON Schema is read off the
signature rather than written twice. `Annotated` carries the description,
`Optional` says what may be left out, `Literal` is a closed list.

Every tool runs **as the session user**. Not as Administrator with a filter
bolted on afterwards, and not with `ignore_permissions` anywhere: the same
`frappe.get_list` the browser would have called, under the same permissions, so a
model asked about somebody else's salary gets what that person would get, which
is nothing. This is the one rule in the module with no exception and no override,
and a tool that needs more than its caller has is a tool that does not ship.

Reading the whole of Frappe this way is the point — `get_list`, `get_doc`,
`get_value`, the report endpoints — because the alternative is a hand-written
tool per doctype that is out of date the week somebody adds a field.

## Watched, not waited out

A generation takes between two and forty seconds. A gunicorn worker held open
for that is a worker answering nothing else, and there are four of them.

So a run is a **background job**, and the browser is handed a run id
immediately and subscribes. The transport is the one the bench already runs:
`frappe.publish_realtime` writes to redis, the socketio process is already
subscribed and already has this person's browser in a room. No second runtime, no
second port, nothing new to deploy.

## The stages

Each one is worth having on its own, and each one is a commit.

**AI 1 — the gateway and one call.** *Done.* The gateway account, name and token
in `One Admin Settings`, beside the Cloudflare account they belong to.
`one_admin/gateway.py` — beside `press.py`, `stripe.py` and `storage.py`,
because it is the same thing they are: an outbound client for a service only the
admin site talks to. One un-metered text call to one hard-coded model, a
per-provider table of path, body and where the words are rather than a branch
per provider, and an operator button on the settings screen to prove the token
works before anything is billed against it.

The guards are the ones worth having later: no `Authorization` header and no
provider key anywhere in the file, no field on the settings that could hold one,
and exactly one model named in this app — `gateway.FIRST`, which AI 2 removes.
A 200 whose shape we do not recognise raises rather than reading as an empty
answer, because the other way is a changed response quietly returning blanks.

The One AI module itself arrives with AI 5, when there is a doctype that belongs
on every site rather than only on admin.

**AI 2 — the catalogue.** *Done.* `AI Model` and its `AI Model Rate` rows in One
Admin, `one_admin/catalogue.py` for the sync and `one_admin/prices.py` for the
reading, with a saved copy of each page in `tests/samples/`.

**Discovery comes from two places for one reason.** Cloudflare's models are
listed from Cloudflare's own API, because the token for that is one we already
hold and it is not a provider secret. Google's are listed *through the gateway*,
which forwards the request and attaches the stored key — so the catalogue is
built without a Google key ever reaching this site.

**The pages are nothing like each other.** Cloudflare puts one row per model
with its id in the first cell, so nothing has to be matched up. Google puts the
model in a heading above the table, in a display name — "Gemini 3.1 Flash Image
(Nano Banana 2)" against an API that says `gemini-3.1-flash-image` — so both
sides go through `fold`, and a name that still does not match is left unpriced
rather than guessed at.

**Measured rather than argued: ten units across sixty-five Cloudflare models.**
Tokens per million, 512x512 tiles, tiles *per diffusion step*, first and
subsequent megapixels, audio minutes, characters per thousand, and images per
million. Google adds prices that change on a date, one price covering three
modalities, and a restatement of the same price in another unit. Nothing
converts between any of them; a rate keeps the provider's own words and metering
matches on them.

**What defeats the parser is the point.** `$0.067 per 1K image` is a picture a
thousand pixels wide, not a thousand pictures, and reading that `1K` as a
multiplier is a bill a thousand times too large. So an amount's own unit is only
believed where the page attaches it — `$0.005/min`, or a parenthetical opened
right before it — and prose like "Equivalent to $0.045 per 0.5K image" is left
unread, which puts the model in front of a person. Five of Google's models land
that way and all five are image models.

**A charge sharing a cell is not a call price.** Google prices context-cache
storage per hour in the same cell as the cache read. Billed per call it would
charge somebody for holding still, so it is skipped — and skipped rather than
flagged, because a model is perfectly sellable without it.

**AI 3 — the ledger.** *Done.* `Credit Ledger Entry` and `Credit Reservation` in
One Admin, `one_admin/ledger.py` for the rows and `one_admin/credits.py` for the
arithmetic, which has no frappe in it. No AI in this stage at all: it is an
accounting module and is tested like one.

**A grant is a bucket with a date on it and expiry is arithmetic.** What is left
in one is what was granted plus everything drawn from it, and a bucket whose day
has passed stops counting. There is no expiry row to write and nothing to run
nightly — the balance simply stops including it.

**A spend names the grant it came out of**, which is what lets the ledger be
append-only: drawing a bucket down without rewriting it means writing a row that
points at it. The soonest-expiring bucket goes first, because the other order
loses somebody credits they bought while a free monthly grant sits unused beside
them, quietly, a month later. A remainder nothing covers is a spend belonging to
no grant, and an overdraw does not expire — it is owed rather than granted.

**A hold is not enough on its own, and this was measured.** Two processes
reserving seven credits against a balance of ten both succeeded. The second
waited on the lock exactly as intended, and then read the balance from the
snapshot its own transaction had taken *before* the first one committed —
InnoDB fixes that snapshot at a transaction's first read and no plain `SELECT`
afterwards sees past it. So every read the decision rests on is a locking read,
and the lock on the workspace's row is only what stops the two of them
interleaving. There is a guard that fails if either half goes away.

**A hold whose call never came back is let go nightly.** A worker that died
mid-flight would otherwise promise a customer's credits to nothing, for good.

**AI 4 — pricing and the three-step call.** *Done.* `one_admin/pricing.py` for
the arithmetic and `one_admin/meter.py` for reading a provider's answer, both
pure; `markup` on a model with `default_markup` and `credits_per_dollar` behind
it in One Admin Settings; and `gateway.call` holding, calling and settling.

**The markup is per model with one fallback, and neither number has a default.**
A flux tile at $0.0000528 and a Gemini Pro call at $2.50 a million tokens will
not take the same multiplier, so one global number either gives the cheap models
away or prices the expensive ones out. Providers publish what a call costs
*them* and never what it should cost anybody else, so an unset markup refuses
the call rather than inventing a margin.

**The three steps, and where each one can be wrong.** The hold is priced from
the caps the caller declared and is a ceiling rather than a forecast — the only
thing that matters about it is that two calls cannot both spend the last credit.
The call goes through the gateway. The settle charges what the provider
*reported*, per modality where it says so: Gemini's `usageMetadata` breaks a
prompt into text and picture tokens, which is two rates on this catalogue and
could only ever have been billed at one of them otherwise.

Cached tokens are the subtle one. Google counts them inside the prompt total as
well, so the input line comes down by what the cache covered — left alone, the
same four thousand tokens are billed at the input rate and again at the cache
rate.

**A call that answered but could not be metered is charged its hold and
flagged.** Never zero: the provider billed us either way, and a model that costs
money and earns none is worse than one nobody can call. A provider that fails
outright releases the hold instead, so a dead call costs nothing.

**Nothing is estimated.** A `Use` is either a count the provider reported or a
parameter we sent, and it says which — `asked` is on the row. A reported line
always beats one we asked for; what we sent is used only for the parts a
provider does not report, which for Workers AI is pictures and speech.

The operator gets `Price a call` on a model: a real call against a real
workspace's real credits, because a number worked out any other way is a number
nobody can check against a bill.

**AI 5 — actions.** *Done.* The One AI module arrives, on every site, with
`AI Action` as a fixture and `AI Action Setting` per workspace.
`one_admin/actions.py` joins the two and is where the safety of the feature is
actually written down.

**Ours first, theirs after, never instead.** The action's instruction goes where
each provider puts a *system* instruction rather than being glued onto the front
of a prompt, a workspace's addition follows it, and between them is one sentence
telling the model which wins. There is nowhere for a workspace to put anything
that replaces ours: `proxy.ai_run` takes an action key, some text, a model and
an addition, and no instruction — the instruction is read from the
administrator's own copy of the fixture, which a tenant has nobody who may write.

**The action exists on every site and decides on one.** A workspace carries the
fixture so it knows what it may ask for and so its settings screen has labels to
draw. Only `One Operator` may write it, and no user on a tenant holds that role.

**A model answers only a job it can do.** `capability.COVERS` is the table and
it is a decision rather than a derivation. Offering whisper caught the first
version of it: a transcriber writes text back, so "Transcription covers Text
Generation" looked right, and a model that reads sound and nothing else had
turned up as a candidate summariser.

**Nothing asks "which model" at the call site.** A workspace picks one on its
settings screen — from a list the *account* answers with, filtered to what the
action needs, because a workspace holds no catalogue — or picks nothing, and the
operator's `default_for` answers. A picked model is checked again when the call
is made, because the first check happened on a machine we do not control.

The two shipped actions are `summarise` and `reply`. Both tell the model what
*not* to do, which has a guard of its own: an action that only says what to
write is an action that fills gaps with plausible fiction.

**AI 6 — top-ups.** *Done.* `one_admin/topup.py`. A workspace buys a pack from
its own account screen, admin makes the Stripe session, and the grant is the
webhook's — a workspace that could grant itself credit by opening a page is a
workspace that never pays.

**Packs rather than amounts.** A customer buys a row from a price list, not a
number they typed, because a calculator on that screen would be a second place
where credits per dollar is decided and the first is in One Admin Settings. A
pack carries `credits`; a plan carries `credits_a_month`. Two fields, because a
lump granted once and an allowance granted monthly under one name is a nightly
job granting somebody's one-off purchase every night.

**The monthly allowance a plan promises.** Nothing was granting it. It runs
nightly rather than on the first, so a workspace built on the twelfth has its
credit that night instead of waiting nineteen days, and the key carries the
month — `plan:<tenant>:<YYYY-MM>` — which is what makes running it every night
free. It expires at the end of its month and does not roll over, which is the
case the ledger's draw order was built for.

Overdue workspaces still get it, for the same reason `proxy.SERVING` carries
Overdue: Overdue is defined as nothing happening to the workspace, and cutting
off its allowance would be the grace period not existing.

**Two ways credit could arrive twice, one field stopping both.** Stripe
redelivers by design and a nightly job runs nightly; `ledger.grant`'s key is
unique on the row, so both meet a database index rather than a check somebody
remembered to write. A top-up and a signup are told apart by what the session
carries — a signup names the request it came from, a top-up names the workspace
and the pack.

**AI 7a — the tools, and what they may do.** *Done.* `one_ai/schema.py` reads a
JSON Schema off a function's signature — `Annotated` carries the description, a
union with `None` or a default says a parameter may be left out, `Literal` is a
closed list — so there is no schema beside every function to fall out of step
with it. `one_ai/tools.py` is the seven; `one_ai/proposals.py` is the card and
Apply, which is why AI 8 is now only the places a card appears.

Every tool runs as the session user. Not as Administrator with a filter bolted
on, not with `ignore_permissions`, and never through `frappe.get_all` — which
looks exactly like `get_list`, ignores permissions, and is the single most
likely way for this rule to be undone by somebody being helpful. A guard names
all four ways of reading past a caller.

Proved on the site as a user with one role and no permissions: listing
workspaces refused, reading one refused, *describing the type* refused, and
proposing to create one refused at the point it was suggested. Then the same
user creating a ToDo through a card, applying it, and owning the record that
came out. Plus: somebody else's card is not theirs to answer, and an edit whose
record moved underneath it is stale.

**AI 7b — the model loop.** *Done.* Tool calling needs a conversation — the
model asks for a tool, the tool runs, the model is called again — and the model
is on the administrator while the data is on the workspace. The shape that is
consistent with `proxy.py` is the **tenant driving the loop**: `one_ai/run.py`
sends the turns so far, admin answers with what the model wants, the tenant runs
each tool as the session user, appends the results and asks again. Admin keeps
nothing between rounds and still never calls a workspace.

A turn of ours is `{role, text, calls}`, or `{role: "tool", id, tool, result}`,
and the two providers spell all three of those differently: Workers AI speaks
OpenAI's dialect, where a tool result has a role of its own and the arguments
arrive as a JSON string — or as an object, which it has also done — and Google
has no tool role at all, so a result goes back as the user's next turn carrying
a `functionResponse`. Both are written down once, in `PROVIDERS`, beside where
each one says how it takes a prompt.

**The rounds are counted on the side that pays.** `actions._conversation` reads
the model turns in what it was handed and refuses past five, because a loop only
the caller can stop is a loop a caller with a bug never stops — and every round
is a billed call. `AI Action.may_use_tools` decides whether an action is offered
any tools at all, so `summarise` cannot start looking things up because somebody
sent it a tool list.

**A tool that refuses answers anyway.** A refusal comes back to the model as a
result saying so, stripped of frappe's markup; a model told "you may not see
that" can say it, and a model told nothing writes something plausible instead.
Tool answers go through `_plain` first — a row out of the database carries dates
and decimals, and a date left as a date is not a display problem, it is the
round that fails to serialise.

**Each round commits what it parked.** A run is up to five model calls, so the
request is open for minutes; a card suggested in round two that disappears
because round four timed out is work somebody did and lost, and a transaction
held across five model calls is locks held across five model calls.

Proved on the site end to end, as a user with one role: two rounds, one
`list_records` in the middle, both rounds metered and billed, the refusal of a
workspace listing arriving as a result rather than a traceback, a conversation
five model turns deep refused by admin, and a `create_record` mid-loop parking a
card that the asking user owns while the model is told plainly that nothing
happened.

**AI 8a — the panel.** *Done.* A launcher bottom right, the shape everybody
already knows from a live chat widget, and a panel above it: a list of
conversations and one conversation. Two views rather than a channel rail,
because a list of threads is the shape OneMessaging will want too — its threads
join this list rather than needing a second panel drawn beside this one.

**Two layers, and only the small one is on every page.** `public/js/oneai.js` is
in `app_include_js` and is a button, a badge and the route; the panel is a Vue
island in `oneai.bundle.js`, fetched by `frappe.require` the first time somebody
opens it. Frappe's own esbuild compiles `.vue` for any app's `*.bundle.js` and
its file uploader is loaded exactly this way, so this is the framework's own
pattern rather than a new one — and a page nobody asks a question on pays
nothing for Vue. The launcher appends to `body`, not to the page container,
which is what makes a conversation survive moving between records: frappe tears
the page down on every route change and would take the panel with it.

**The page is a pointer, not a payload.** What travels is the route — the
doctype, the id, which view, a list's filters — never the record's values. The
model has `read_record` and that runs as whoever is signed in, so assembling
values here would be a way around a permission rather than a convenience. The
pointer is a turn in the conversation, marked so it is said to the model and not
shown to the reader, and it is kept with the turn it was said on: the context of
the third message is where they were for the third message, not where they are
now. The chip above the box names it, and switching the chip off stops sending
it.

**The conversation is a doctype.** `AI Chat` holds a title, when it was last
said to, what it has cost, and the turns — the same turns the gateway speaks,
because the conversation *is* the turns and a second shape beside them is a
second shape to keep in step. It is `if_owner` to everybody: one person's chat
is not another's to read. The question is stored *before* the answer is asked
for, so a run that fails leaves it in the chat rather than losing it, and only
the last two dozen turns are sent while the whole thing is kept.

**Counting is a tool, and the instruction says to reach for it.** `list_records`
answers with twenty rows unless asked for more and never more than a hundred,
and the panel draws three of them — but the rows the model was sent are rows the
workspace paid tokens for, so "how many tasks do I have" answered by listing is
a bill for a number. The `chat` and `find` instructions say to count rather than
list, and the `limit` parameter's own description says so where a model reading
the tool will see it.

**A record is drawn, not described.** When a lookup comes back, the panel shows
the records themselves — the type as a chip, what the record is called, a few
labelled fields, and buttons to open it or copy its link — rather than a line
saying a lookup happened. One record gets six fields; several get two each,
because a list drawn at full height is a list the answer sits below the bottom
of, and past three it says how many more there were. The drawing is done on the
server: labelling a field needs the doctype's meta, and the panel fetching meta
for every type a conversation touches is a round trip per answer.

**A card is answered where it was made**, and it is the same card. A suggestion
is a record drawn the same way — the fields are what is being proposed, which
for a change is only what changes — with the chip reading Suggested and Approve
and Refuse underneath. The moment somebody would answer it is the moment it was
made, not the next time they remember to open a list. Cards are read back on
every render rather than stored in the transcript: a copy kept in the turn would
go on saying Proposed for ever.

**No gradient edges.** The spectrum is on the launcher, where it is the mark,
and on the bloom that breathes while it works. A coloured bar down the side of
every card is a border round everything, and it is the first thing that makes a
panel look generated rather than designed. A suggestion is told apart by what
its chip says and by the two buttons under it.

**A model is handed the answer, not our envelope.** The tool result in a turn
is what the tool said — rows for a read, the card for a write, `{"error": ...}`
for a refusal — and `ran` and the card's id sit *beside* it in the turn rather
than inside it. Only `result` is sent to a provider, so a model cannot quote our
bookkeeping back at the reader as if the wrapper were the answer, which is
exactly what it did the first time.

**Who said it is read off where it sits.** The reader's words are a tinted
bubble on the right; OneAI's are plain text on the left, because an answer is
usually the longest thing in the panel and a bubble round a paragraph is a box
round a page. What it did on the way — "Looked at ToDo", "Suggested a change to
ToDo" — is one grey line, a footnote to the answer rather than a second message.
The names stay for a screen reader, which has no left and right to read.

**The colour is the mark's own, and it is used twice.** The six stops of
`ai-spectrum` are tokens in `theme.css`; they are worn by the launcher's ring,
where the colour is the mark, and by the bloom that breathes while it works. Not
by a bar down the side of every card and not by a strip across the panel's top,
which is the first thing that makes a panel look generated rather than designed.
Later, the badge on a field it wrote.

**AI 8c — eight more tools, prose, three sizes and a way back from a
failure.** *Done.*

Four reads were added because the workspace already knows things a model was
guessing at. `find_records` is frappe's own link search, so "Apple" becomes a
supplier's id the way it does when a person types into a Link field, instead of
listing suppliers and picking one. `what_links_here` reads the Link graph, which
is the question behind "can I delete this". `what_can_happen` reads the record's
workflow transitions — the moves it actually has, to the roles it has them to —
and answers plainly that there is no workflow where there is none, because
raising there would come back as a refusal and read like a permission.
`run_report` runs one of the workspace's own reports: an answer somebody already
wrote down and tested beats a model inventing an aggregation, and the rows are
capped at fifty because a report is exactly the thing that answers with
thousands.

And one write. `move_record` suggests a workflow move, and approving it runs
`apply_workflow` — the workflow's own transition, with the role it checks and
the log entry it writes — rather than setting the state field, which would move
the record without any of that.

**Answers are rendered, not printed.** A model writes markdown whether or not
anybody asked it to. `frappe.markdown` is showdown with tables on and a
whitelist sanitiser after it, so a model that answers with a script tag has its
script tag removed by the framework rather than by something we wrote.

**Three sizes.** Snug is the live-chat shape, roomy is for a conversation with
records in it, full is for reading a report beside the page it is about — and
the cards put two field pairs across once there is room, which is the difference
between a card six lines tall and one that is three. Kept in frappe's own
per-user settings rather than this browser's storage, so the size somebody chose
is theirs on whatever machine they sign in from next.

**A failure says what happened and leaves the question where it was.** A fault
out of the account carries an endpoint and a status: right in a log, wrong in a
panel. `Again` is transient and becomes "could not be reached just now — try
again"; `Refused` already reads as a sentence and is passed through. The
question stays on screen with the reason under it and a button that sends the
same thing again, because a failed run that clears the box is a question
retyped. While it runs it says what it is doing — thinking, then looking things
up — rather than showing a spinner that says nothing for twenty seconds.

**LIVE — the real providers, and the seven things the stand-in hid.** *Done.*
Wired to a real Cloudflare account and a real Gemini key. The catalogue is now
the providers' own: 65 Workers AI models, 54 priced, and 50 Gemini models, 18
priced. Seven failures, none of which a stand-in could have shown, because a
stand-in answers in whatever shape it was written to answer in:

**Workers AI has two response shapes.** `result.response` on the classic text
models, and OpenAI's `result.choices[].message.content` on the newer ones —
gpt-oss, gemma-4, qwen3, glm. Every call to gemma-4 raised "answered 200 with
nothing in it" while the model had in fact answered. Both are read now, and so
are both tool-call shapes. `reasoning_content` is deliberately not read: it is
the model thinking out loud, and showing it is showing somebody working notes
and calling them a reply.

**Google refuses an array without `items`.** `properties[fields].items: missing
field`, 400. OpenAI's dialect accepts it, so the schema reader now writes the
stricter form.

**Gemini function calling needs v1beta.** v1 answers "Function calling is not
enabled for api version v1", and the catalogue was already listing from v1beta
— one version for both, so what is listed is what can be called.

**A permanent refusal arrived as "try again".** Frappe answers every thrown
exception with a 500, and 500 is retryable, so a model that is not offered and a
conversation that has run too long both looked like a server having a bad
moment. The other side's `exc_type` now wins over the status — and the proxy
throws rather than letting the fault propagate, because an unhandled exception's
body carries `exc_type` and nothing else, so the sentence saying *why* never
reached the workspace at all.

**A provider may reclassify a model.** Cloudflare moved llama-3.2-11b-vision
from Vision to Text Generation, and the validation refusing a default it can no
longer do stopped the entire nightly sync. The default goes rather than the sync
stopping.

**A provider may drop one.** llama-3.1-8b-fp8-fast was withdrawn while it was
the default for Text Generation, and then held that default against every
replacement — each attempt refused by a row for a model that no longer exists.
Withdrawal clears the default, and a withdrawn model no longer holds one.

**Gemini 3 will not talk to you twice without its own signature.** Every
`functionCall` part comes back with a `thoughtSignature`, and the next request
is refused without it — "Function call is missing a thought_signature in
functionCall parts". It is opaque and it is the model's; our turn carries it
only so it can be handed back on the same part it arrived on. Gemini 2.5 sends
none and needs none, which is exactly why testing one Gemini model was not
testing Gemini.

Measured on real models, same question, same tools: **gemma-4** answers in two
rounds with one `count_records` for 0.68 credits; **gpt-oss-20b** in two for
1.58; **gemini-2.5-flash-lite** in two for 0.53. All three reached for counting
rather than listing, which is the instruction from AI 8c landing. **gemini-3.1-flash-lite** in two for 1.55, and
**gemini-3.8-flash** in five for 16.17 — it counted, then described the type,
then listed, then read one record, and hit the round cap having already had the
answer. Thorough is not free. **llama-3.2-3b** cannot do this at all: it asks
for two tools at once and Workers AI answers "This model only supports single
tool-calls at once!" — a model limitation, now legible, and a reason not to
offer it rather than something to code around.

**THE GATEWAY — the premise, proven.** *Done.* The site now calls Cloudflare's
real AI Gateway. `gemini-2.5-flash-lite` and `gemini-3.1-flash-lite` both answer
the tool loop through it, and the site sends **no Google key at all** — only
`cf-aig-authorization` with the gateway token. The key is in the gateway and the
gateway attaches it. That is the sentence at the top of `gateway.py`, and until
now it was a design claim rather than a measured one.

**Three things learned getting there.** An AI Gateway token is a separate
permission from managing one: Read and Edit govern the gateway's configuration,
**Run** governs sending traffic through it, and a token with Edit alone answers
401 on inference. Run is all OneAdmin ever needs, so it is the only permission
the app's token should carry — a leaked one buys somebody the rate limit rather
than the ability to turn logging off.

**Workers AI needs the gateway's own path, and this one cost an hour of blaming
the wrong thing.** `/workers-ai/@cf/vendor/model` — the path the direct API uses
— answers **401 through the gateway** with a token that answers 200 on the
direct API a second earlier. That reads as a credential problem and is a path
problem: behind the gateway Workers AI is the OpenAI-compatible endpoint,
`/workers-ai/v1/chat/completions`, with the model in the body. Same token, same
gateway, 200.

It also answers in a third shape: `choices` and `usage` at the top level, no
`result` wrapper, where `/ai/run` wraps both. Reading one shape only is a call
that answers fine and then bills its hold because nothing could be metered.

**The tenant tag lands.** Read back off the gateway's own request log:
`Metadata — tenant: probe9x`, beside the model, the endpoint and the token
counts. A bill somebody disputes can be checked against Cloudflare's record
rather than only against ours, which is what `cf-aig-metadata` was put there
for.

**A reasoning model that says nothing has still answered.** Given a small output
budget, gemma-4 spends all of it on thinking and says nothing — `content` absent
on `/ai/run`, an explicit `null` on the gateway's endpoint, and the thinking
itself under `reasoning_content` in one and `reasoning` in the other — and the guard that exists to catch a provider changing its response
shape fired on it. A choice that came back at all is an answer, even an empty
one; `None` is kept for a body with no choices in it, which is the case the
guard is actually for.

The two authentication failures are told apart by shape rather than status, both
being 401: a bad gateway token comes back as `AiGatewayError` code 2009, and
anything the provider refuses as Cloudflare's own code 10000.

**And the gateway is rate limited** — `one-gateway` is set to 50 requests per 60
seconds, which a five-round tool loop brushes against with two people asking at
once. Not a problem today. It is a number to remember when it is real.

**THE MATRIX — one question, every priced text model.** *Done.* Forty-one
models, the same question, the same tools, throttled under the gateway's fifty a
minute and capped at 200 output tokens. **Twenty-eight answer correctly.** The
run cost about five cents and found four things.

**Three were ours.** `qwen2.5-coder` puts a tool call in `content` as an object
rather than using `tool_calls`, and a dict handed on as words crashed three
functions later; it now reads as no words, and deliberately not as a call —
inventing one from free-form content is how a model ends up having "asked" for
something it never asked for. `granite-4.0` sends `arguments` as a JSON string
*of* a JSON string, so one `json.loads` left another string behind, which
reached a tool where a dict was expected. And DeepSeek R1 and QwQ put the whole
of their reasoning *inside* `content`, fenced in `<think>` — so unlike
`reasoning`, it cannot be ignored, it has to be cut. All three were invisible
until a model that does it turned up. All three are fixed, and the eight models
they broke now answer.

**One was the catalogue's.** Cloudflare calls a reranker and a sentiment
classifier "Text Classification" and two translators "Translation", and
`A_TASK` mapped all four to Text Generation, because "produces text from text"
is exactly what a chat model does too. They were offered, picked, and answered
`Bad input` to a chat body. Translation and Text Classification are capabilities
of their own now, covered by nothing, so an action needing Text Generation
cannot reach one.

**What is left is the models being models.** `llama-3.2-1b` and `-3b` call a
tool and then answer as though it returned nothing. `llama-4-scout` and
`qwen2.5-coder` will not call one at all. `llama-guard-3-8b` rejects the tool
schema outright, and `llama-3.2-11b-vision` needs a licence accepted in
Cloudflare's dashboard. None of that is ours to fix; it is a reason the
catalogue's Offered switch exists, and the matrix is how it gets set.

**And the cheapest that work are not the ones anybody would have guessed.**
`granite-4.0-h-micro` answers in two rounds for **0.13 credits**; `glm-4.7-flash`
for 0.49; `gemini-2.5-flash-lite` for 0.53. Gemma 4, the current default, costs
1.16 and takes three rounds. `gemini-3.5-flash` gets there too — for 16.36,
which is a hundred and twenty times the cheapest correct answer to the same
question.

**THE INSTRUCTION IS THE ACCOUNT'S.** *Done.* A workspace configures each
action we register: it picks a model from what the account offers, and it adds
to the prompt. It does not see the prompt.

`AI Action` stays a fixture, because a new action has to arrive with a migrate
and a workspace needs the row — the label, the capability, the token caps — to
draw a picker at all. The instruction is not part of that, and shipping it while
declining to render it would be a curtain rather than a wall: the row sits in
the workspace's own database and `frappe.client.get` reads it. So `trim` empties
the field on a workspace after every migrate and leaves the account's copy
alone. `proxy.ai_run` was already reading the account's copy and ignoring
anything sent with a call; now there is nothing on the other side to send.

`ready` writes a setting per enabled action at the same time, so all four have a
screen from the start — a setting that only exists once somebody saves it is a
setting nobody knows is there.

**THE PERSONA — what is always true, said once.** *Done.* `One Admin
Settings.persona` goes before every action's own instruction: who it is, that it
never invents a fact or a name or a figure, that it says plainly when it cannot
see something, and what it does when it is given tools — look things up, count
rather than list, suggest rather than do, treat the reader's page as a pointer.
Four fixtures were each carrying their own copy of that, which is four places to
edit and three chances to disagree. Each action now says only what *it* is for,
and the longest of them is four lines.

A Single that already exists does not pick up a new field's default, so `voice`
fills it on migrate when nobody has written one — reading the text from the
field's own default rather than repeating it, so there is still one copy.

**AI 8d — the upload.** *Done.*

A file dropped on the panel attaches to the `AI Chat` row and goes to the model
with the question, which is how "make a quotation from this PDF" works. It is an
ordinary attachment, so it has an owner, a permission and a place in the
workspace rather than living inside a conversation nobody can find again — and
the paperclip opens frappe's own `FileUploader`, which already does the drive,
the camera, the link and the size check. Asking with no conversation open starts
one first, because an attachment needs a row to hang off.

**Only the newest turn carries bytes.** The conversation is sent whole every
round, so a 3 MB attachment over five rounds is fifteen megabytes of HTTP for one
question. `files.carried` puts the base64 on the last turn that has files and
leaves the older ones in the transcript by name, which is what a person reads
them as anyway. Four megabytes a file, three files a turn: the limit that matters
is what a round costs, not what the provider would accept.

**The bytes are read here, as the person asking.** `_held` does a
`check_permission("read")` before anything is encoded, so a file somebody may not
open is a file the model is never handed. The stored turn keeps name, url, type
and size and never the data, so `AI Chat` does not grow a base64 copy of every
attachment.

**A model that cannot read it says so before anything is reserved.**
`capability.can_read` reads the catalogue's own `reads_image`, `reads_audio` and
`reads_video` flags, and PDF is a special case: Google takes a PDF as inline
data and Workers AI does not, whatever its vision flag says. `actions.run`
checks it before `gateway.call`, so "gemma-4-26b-a4b-it cannot read
application/pdf." costs nothing and leaves the balance where it was.

**The two providers are handed a file differently.** OpenAI's shape wants a data
URL in a content list; Gemini's wants `inline_data` with the mime type and the
base64 beside the text part. That is the turn shape change this stage was its own
stage for.

Proven against a real quotation PDF: `gemini-2.5-flash-lite` answered "The
supplier is Falcon Steel LLC and the total is AED 18,400" in one round for 0.64
credits, and `gemma-4` refused it for nothing.

**The composer.** One card holds everything about the next question: the
files waiting to go, the words, and a row under them — attach, the model, speak,
send. The box and its buttons read as one thing rather than a field with buttons
parked beside it.

The model pill shows which model answers, read from the last answer or else the
workspace's setting for the chat action, and trimmed to the model's own name.
It does not switch anything, because the model is the workspace's choice per
action and one person switching it would switch it for everybody. For a System
Manager it opens that setting; for everybody else it is a label.

Speaking uses the browser's own speech recognition, so the button is simply
absent in a browser without it (Firefox). What it hears is typed into the box
and not sent, so a misheard word is fixed before the question goes. In Chrome
the recognition itself runs on Google's servers, which is the browser's doing
and costs no credits.

The panel's greys were `--gray-*`, which frappe does not flip in dark mode, so
every chip and bubble went white on dark. They are the `--surface-*` and
`--outline-*` tokens now, which it does.

**Who configures it.** Nobody on a workspace is ever given System Manager, so
nothing may wait for it. `one/roles.py` adds **Workspace Administrator** — not
frappe's Workspace Manager, which is about the desk's sidebar pages — and it is
what `AI Action Setting`, the model list, *Try it*, the model pill, the
workspace's address and buying credits all check. `tests/test_roles.py` refuses
any new `System Manager` gate; the one place it is still read is the apps
screen, where hiding frappe's Framework tile from everybody is the point.

**AI 8b — the field tools and the badge.** *Done.*

The OneAI mark beside every Small Text, Text, Long Text, Text Editor and
Markdown Editor field a person may write opens the same panel, pointed at that field —
not a second UI. A chip under the conversation says which field, and three asks
cover most of what anybody wants from a paragraph: improve it, make it shorter,
fix the spelling. An empty field has one: write a first draft.

**The field's text comes from the browser, not the record.** It is what the
person has in front of them, typed and perhaps not saved, and it is theirs to
send. `touch.told` reads nothing. And the field is checked against the doctype's
own meta on the way in (`touch.target`), so a browser naming a field that is not
there, or is not prose, gets an ordinary question instead.

**The answer is an `AI Proposal` of kind Edit**, the same card as an agentic
edit, so there is one thing to trust rather than two. The model's last turn
becomes that card rather than printing the paragraph and then the card. A Text
Editor's answer is converted from markdown on the way; a plain field is told to
write plain text.

**Approve puts the text into the open form**, as the person, after the same
checks as any other suggestion (`touch.took`). They save it the way they save
anything. A save on the server there would either lose whatever else they had
typed or be refused as stale. This is also what makes a field on a document that
is not saved yet work: it has no name to edit, so the proposal carries none, and
`proposals.apply` refuses one on the server.

**The badge is the same mark, in colour.** Grey, it is the button; in its own
colours, it says what the field holds now is what OneAI wrote — one icon per
field rather than a button and a label beside it. **It is a comparison, not a
flag.** `AI Touch` holds what was written,
one row per document and field. `doc_events["*"]["onload"]` hands the form the
fields that still say it, so the badge costs no request of its own; it shows
while they match and goes the moment somebody edits the field, with no hook on
anybody's write path. Compared as words, tags stripped, because a Text Editor
wraps what it is given in its own markup. A new document's badge waits for the
save that gives it a name (`touch.landed`), and is only granted if the record
was made after the text was taken and still says it — an abandoned form and
another record opened in its place collect nothing.

Every applied write leaves a touch, not only a field's own: an agentic Edit or
Create from the chat badges the prose fields it set. `File.ai_generated` is set
when a suggestion creates a file.

Measured on a ToDo: the control, the card, Approve into the form, the badge
after save and reload, and the badge gone once a person edited the field — and
the same for a new ToDo drafted before it had a name.

**AI 9 — watched, not waited out.** *Done.*

`chat.say` now stores the question, starts a background job and answers at
once with a run id — about a second, where it used to hold a web worker for the
whole generation. `chat.answer` is the job. frappe starts it as whoever
enqueued it, so every tool the model calls still runs with that person's
permissions; nothing about the rule changes by moving it off the request.

`run.ask` takes a `heard` callback and says each thing as it happens — a round
starting, a tool it ran — and `_tell` sends it to that person's browser over
`frappe.publish_realtime`, the socketio the bench already runs. The panel
draws what it has done so far as quiet lines above what it is doing now:
"Looked at ToDo", then "Reading what it found…". When the run says done, the
panel reads the conversation back from `AI Chat`, which is where the answer was
kept whether or not the browser heard the last message.

**Realtime is the fast path, not the only one.** Every step is also kept in the
cache for fifteen minutes, and the panel asks `chat.progress` every five
seconds while it waits — so a socket that dropped, or a tab that slept, is late
rather than stuck. Measured: 2.9 seconds to an answer over the socket, 5.6 by
polling alone. Only the person whose run it is can read it back.

**One run per conversation.** A question sent while the last is still being
answered is refused, and a panel closed mid-run and opened again picks the run
back up from `opened`'s `running`. A job that dies is logged when it is a bug
and said in words when it is a refusal, and either way the chat is free again.

It is not token streaming. The model's words come back from the account in one
piece per round, because the account is another site answering a request; the
steps are what arrives as it happens. Streaming the words through would need
the proxy to stream too, and the wait it would save is the last second of a
run, not the first thirty.

On a dev bench the socket needs three things `bench start` does and a bare
`bench serve` does not: `DEV_SERVER=1` on the web server (or the browser dials
its own port), `webserver_port` matching the port it serves on (socketio checks
the session by calling it), and a worker.

**AI 10 — the operator's screens.** *Done.*

**The catalogue shows what a model sells for.** Two stored fields on
`AI Model`, credits per million text tokens in and out, after markup — the
model's own markup or the default. They are the number an operator chooses
on, and the rates table is not: the rates are the provider's dollars, and what
a workspace pays is those times the markup times the credit rate. Worked out
by `pricing.per_million` on every save, and again for every model when
One Admin Settings changes the default markup or the credit rate. A model not
priced in tokens — an image or audio model — has no such number; the column
cannot hold nothing, so it holds zero and the list and the form both leave it
blank rather than print a price of 0.00 that reads as free.

**Offering is one press on the row.** The list's indicator says what a row is
for — Default, Offered, Not offered, Needs review, Withdrawn — and a Priced
row carries Offer or Stop offering. It is the model's own save, so every rule
on it still holds: a default cannot stop being offered while it is the default.
Provider left the columns for the filters, so the name has room.

**AI Usage** is a report in the Selling group and a button on every workspace:
calls, credits, credits per call and the last call, for a period, by workspace,
by model, or both. One call is one settled `Credit Reservation` — what it was
charged once the provider said what it used — and the query is
`ledger.usage`, because only the ledger reads its own tables. The total is the
report's own row rather than frappe's, which adds up every number column: a
sum of "workspaces" or of "per call" is not a number anybody means, so the
total counts the period once and divides credits by calls.

Measured against this bench's own month: 234 calls across 35 models, 223.76
credits, 0.96 a call; gemma-4 selling at 200 in and 600 out a million, granite
at 34 and 224.

**Where OneAI lives.** It is not a place on the rail. frappe gives every
module a sidebar of its own, and One AI's was five doctype lists nobody
navigates to; `code_only_modules = {"One AI": ["One"]}` takes it off the dock
and hands its screens to One. A workspace administrator finds them under
**One → OneAI**: Actions (what each action runs on and is told), Credits,
Conversations and Suggestions. The operator's side is **One Admin → OneAI**:
Models and AI Usage.

**Credits** is the workspace's own analytics: credits left, used, calls and
what expires next as cards; a bar a day for the period; and the table cut by
model, by person or by day. The numbers come from the account in one call
(`proxy.ai_usage`, which names the workspace from its token). By person is the
join only a workspace can make: a call is filed against the conversation it
was made for, and the conversation has an owner here. It is the Workspace
Administrator's, which is why it is a report rather than cards on One's home
page, where everybody would see what the workspace spends.

**On the Tenant form**, the credit actions — give credits, the ledger, AI usage
— are in the form's own sidebar, because none of them changes where the
workspace stands and the toolbar is for the things that do. The header carries
a Credits bar beside Storage: what this month has used against what is left,
with the calls it took, and empty and red when there is nothing left.

**What would you like to do?** The panel opens on a new conversation, not
the last one — it is opened to do something here, and the last conversation is
about somewhere else; every earlier one is one press back. Its empty state
offers the few things that fit the page, from `one_ai/suggest.py`: a summary on
a record, what stands out on a list, and whatever each module adds for its own
doctypes under `one_ai_suggestions` in `hooks.py`. A suggestion is offered only
to somebody holding the verb it names, and one that needs a file opens the
uploader and asks the moment the file is in. Buttons on every form were the
alternative, and a form carrying an AI button per feature is a form nobody
reads.

**Modules bring their own tools.** `one_ai_reads` and `one_ai_suggests` in
`hooks.py` add a module's functions to the tools a model is offered, under the
same two rules: a read runs as the person asking, a suggestion writes a card.
OneHR's live in `one_hr/ai.py`.

**The first is a receipt.** On Expense Claim, *Claim a receipt* takes a photo
or a PDF and `claim_expense` suggests an Expense Claim with one row — in the
asker's own name, read from their employee record and never taken as an
argument. The type is picked on this side from the workspace's own list, the
model's word and the receipt's text, because a model told "Taxi is not a type"
stops to ask the person rather than trying Travel. A receipt in another
currency is said, not converted: a converted amount would be a rate the model
made up. On Approve the claim is a draft that goes through the workspace's
approval like any other, and the receipt is attached to it.

For that, a suggestion may now carry rows of its doctype's own child tables —
plain values, twenty rows at most — and the card draws every row; and a
suggestion carries the files it was made from, attached to what it makes.

Measured on a taxi receipt drawn as a PNG: AED 75, 21 September, Travel, the
trip in the description, Rania Sabbagh as the employee, 1.42 credits. Two
things the live run found: Gemini answers the round after a tool call with an
empty candidate, which is *done* and is now read as done; and an empty
candidate anywhere else is a blip, retried once before it is said as "try
again".

**The second is leave.** *How much leave do I have?* and *Book time off* are
offered on Leave Application and on the OneHR home. `my_leave` reads what is
left of each kind, the holidays in the dates asked about, what they would cost,
and who on the team is already off — by HRMS's own department rule, so it says
nothing the leave calendar would not. `book_leave` counts the days with HRMS's
own function, refuses more than are left, and refuses before the card when
nobody approves this person's leave and HR Settings makes an approver
mandatory; Approve would otherwise fail on a field the person never saw. The
reply names any day in the range that costs nothing, because "Thursday and
Friday" costing one day is the thing the person did not expect.

The model has no clock, so every turn now opens with today's date — asked for
"this Friday" it had booked a Friday in 2024. And a suggestion card reads its
fields in the form's order: stored changes come back alphabetical, which put
"Asked For On" on the card and pushed "To Date" off it.

Measured as Rania on the OneHR home: the balance answer right in one round,
Thursday 24 and Friday 25 September booked as one day of Annual Leave with
Friday named as the weekly off, and Approve making HR-LAP-2026-00002 for her
approver. Just under two credits for the whole conversation.

**The third is a CV.** On a Job Opening, or the applicant list, *Add
applicants from CVs* takes one CV or a batch and `add_applicant` suggests a
Job Applicant for each — name, email, phone, the opening, and the CV as the
resume, attached when the card is approved. With it goes one line for the
hiring manager, in HRMS's own notes field: what the CV matches of what the
opening asks for and what is missing. Never the rating field — a number a
model gave is a number somebody will sort candidates by. The opening is
matched by id or by its title, and somebody whose email is already an
applicant is said, not added twice. A batch of files is asked about once
they are all in: the uploader answers file by file, and the panel had been
asking on the first.

Measured with two CVs on the Site Engineer opening: a site engineer and a
graphic designer, two cards, the designer's line reading "Has experience as a
Graphic Designer, not a Site Engineer" and the engineer's CV attached to her
applicant on Approve, 1.28 credits for both. The first run found three
things. The model named each file as it pictured it — "Layla Nasser CV.pdf"
for layla-nasser-cv.pdf — so no CV was attached; files are matched as a
person would match them, by the applicant's name in the file's. It called the
designer a fit, never having read the opening; a record's form now tells the
model what the record says — its title, its main fields and the first of its
long text — on every turn. And the fit line was cut mid-word at the notes
field's 140 characters; it is asked for shorter and cut at a word.

**The fourth is an appraisal.** On an Appraisal, *Draft my feedback*
reads the cycle with `appraisal_facts` — the employee's goals and how far
they got, the KRAs, their own reflection, the feedback already given, their
attendance, late arrivals and leave in the period, every one read as the
reviewer — and `draft_feedback` suggests the reviewer's Employee Performance
Feedback with the words, or puts them into the draft the reviewer already
has. HRMS's feedback is where a reviewer's words live, one per reviewer per
appraisal; the ratings stay the reviewer's to give, and the model gives
none. Somebody drafting on their own appraisal is told their words go in its
reflections.

Measured as a recruiter reviewing Omar: the facts read, the draft built from
his goal at 55% and the feedback already given, and Approve making his
Employee Performance Feedback. The small model twice wrote the draft into
the chat and made no card, and once asked the reviewer for the goals it had
just been handed. So a suggestion now names the tool its question exists to
call — `expects` — and a run that ends without that call is asked once for
it, as a question to remember is; the receipt and CV suggestions name
theirs too. The facts carry their own next step.

**The fifth is why people leave.** On the exit interview list, and on
employee separations, *Why are people leaving?* reads every completed exit
interview in the period and every leaver's recorded reason — each person
once, read as the asker — and the model groups what they said into a few
reasons with how many gave each and their own words. Measured on six
interviews: gemini-2.5-flash answered pay 2, progression 2, relocation 1,
each with the words behind it, for 3.9 credits; flash-lite, told the same,
answered one sentence folding pay into progression. A grouping is the
model's judgement, and a small model's is visibly worse; this is the tool
where a workspace's choice of model shows most.

**What a model is told about a type, and what happens when it guesses.**
On a list or a form the context turn carries the type's fields — fieldname,
label, required — and who the reader is, with OneHR adding their employee
record through the `one_ai_reader` hook; "my leave" had been a filter on an
invented `applicant` field with the value "me". `describe_type` says what is
required, what shows when, the options of a Select, a table's own fields, and
what the system fills itself; hidden fields, Company among them, are left out.

A new record is tried before it becomes a card: frappe's link check, then the
doctype's own `validate` inside a savepoint that is always rolled back, then
what is still required. That is where HRMS says a leave needs an approver, so
the model hears it and asks, instead of the person pressing Approve on a card
that fails. Before that, what frappe can resolve without guessing is resolved:
a field named by its label is that field (`due_date` is ToDo's `date`), and a
link given as a title is that record when exactly one the reader may see has
it. A field the type does not have is refused with the list of fields it does
have, for reads as well — frappe's own "no permission to access field" read to
a model as "this cannot be done".

Every value on a card is frappe's own formatter's: the site's date format,
money with its currency, a link as its record's title. A record read twice
while answering one question is one card, and the reply says in a sentence
what the cards add up to rather than listing them again.

**What it knows beyond the record** — `one_ai/memory.py`, four kinds with
four owners.

The records themselves, read live: `about_record` is everything the form's
own sidebar knows about one record — its fields, what links to it, its
comments, mail, changes, assignments and files — through frappe's own
`get_docinfo`, so it is never a copy that went stale and never more than the
reader may open. A Knowledge doctype holding copies of records was the other
way, and it leaks: a note summarising a salary is readable by whoever reads
the note.

A person's own memory, `AI Memory`: short facts somebody told OneAI to keep.
Private by the doctype's if-owner rule and by an owner filter on every read,
because Administrator is not held by if-owner. Kept at once and quietly,
with no card and no line in the chat: it is what the person just said, it is
theirs alone, and the memory list is where it is seen and deleted — `KEEPS`
in `tools.py` is the one write that is not a card, named on its own for that
reason. Kept only when
the person asks, or tells OneAI a lasting fact about themselves or how they
work — the tool and the persona both say so, and neither the task at hand
nor anything a record holds. The same fact twice is one memory (equal, one
inside the other, or worded 80% alike), a correction replaces what it names
as corrected, and past two hundred the oldest goes. The newest eight ride
along on every turn; `recall` finds the rest. Tied to a record only when the
fact names that record's title or id. The conversation list links to the
memory list, which is where they are read and deleted.

The workspace's knowledge, `AI Knowledge`: what a Workspace Administrator
wrote for everybody — a policy, a glossary, how things are done here. A note
tied to a type is told to the model whenever that type's list or form is on
screen; an untied one is found by `recall`.

What the live runs of memory found. A small model says "I will remember that"
and calls nothing: a question that asks to be remembered and ends with no
`remember` call is asked once more, quoting the person's own words. The
memories every turn carries were worded "the reader asked you to remember
X", which the model read as being asked again and re-saved X; they are
"already remembered" now. And a model reading "HR-EXP-2026-00004" asked for
the type "HR-EXP" and was told by frappe that a module failed to import;
a type that does not exist, given with an id, is found by searching for the
id, and otherwise refused with where to look.

And one that had been there since the loop was written: the account counted
rounds over the whole conversation rather than over the question being
answered, so the sixth question of any chat was refused before it was asked.
It counts from the last thing the person said now. A tool's refusal shows the
reader its first sentence only; the rest — the fields a type has, the values
there are — is written for the model.

The panel had shown every earlier call to a tool with the last answer that
tool gave — Gemini's call id is the tool's name, and calls were matched to
their answers by id. Each call is matched to the tool turns straight after it
now, in order.

Search across every type, `search_everywhere`: frappe's own global search,
the desk's search bar — the workspace's Global Search Settings say which
types are indexed, and frappe checks `has_permission` on every hit before it
is answered. Beside `find_records`, which is one type's link search, the
tool for turning "Apple" into a supplier's id. The index is built by the
scheduler; a site whose scheduler is off has an empty one, and the search
answers nothing rather than something wrong.

The reader's past conversations, searched by `search_my_chats` in what was
said rather than in the page pointers and tool rows around it.

**What every turn opens with.** Today; the workspace — whose it is, its
money, its clock, and what a module adds through `one_ai_workspace` (OneHR:
the weekly days off); the reader — name, email, their language when it is not
English, and what a module adds through `one_ai_reader` (OneHR: their
employee record); the page and its type's fields; then their memories and the
knowledge for that type. The persona gained two rules: a tool's error is read,
corrected and tried once more before the person is asked, and something worth
keeping is offered as a memory.

Three things the first live run of this found, each fixed where frappe could
say it rather than by more words in the prompt. A link filtered on a record
that does not exist — leave type "Annual" for "Annual Leave" — matched
nothing, and the model asked the same empty question nine times until the
round limit ended the run; that filter is now refused with the values there
are, and the identical call twice in one answer is answered "already asked,
answer with what you have" instead of being run again. A memory tied itself
to the reader's own employee record rather than the person it was about; it
is tied to a record only when the fact names that record's title or id. And a
model that looked something up and then said nothing — Gemini's empty reply
after a tool result — left a blank panel; a finished run with no words and no
card is asked once more, in a turn the reader never sees, to answer.

Found on the way: `what_links_here` had been broken since v17 changed
`linked_with.get` to answer `{docs, hidden_count}` per type. It reads both
shapes now, and says how many links the reader may not see as a number.

**Settings, one field at a time.** On any settings page — frappe's Single
— every field a person might not know the meaning of has a quiet OneAI mark
beside its label, shown when the field is pointed at. It asks what the field
is for and what it should be here, and sends the field with the page, so the
model is handed `about_field` before it answers: what the field is for, what
it holds, what it may hold, when it shows, and for a link how many records
there are to choose from and what a new one needs — the page's own field
list had been answered "no change suggested" for an empty template field
with the obvious template sitting there. A question from that mark expects a
change card, and a change to what the field already holds is refused as
nothing to change, so "it is right as it is" stays a sentence. An Edit card
on the open page puts the value into the form for the person to save. Every
settings page also offers *Help me set this up*, whatever module it is in.

Measured on HR Settings: the empty Exit Questionnaire Notification Template
field got a card setting it to "Exit Questionnaire Notification"; Standard
Working Hours, at 8.5, got "That is right as it is" and no card. Found on the
way: every call from a workspace to its account waited ten seconds, AI runs
included, and a run longer than that — any real draft — failed as
unreachable; runs wait seventy-five now.

**A card carries every change it would make.** A change card had shown the
first six fields, so a "set everything up" card changing twenty showed six
and applied twenty. Every field is on the card now: eight shown, the rest
behind "Show N more", each a change read as what it holds now, struck, and
what it would hold. And only what would change goes on it: fields the model
set to what they already hold are dropped before the card is made, and a
card left with none is refused as nothing to change. Checked with a card
built by hand, no model: twelve fields asked, three already right and
dropped, nine on the card.

**A big change is read on the page, not on the card.** Nine rows of was and
will-be in a chat column is a table nobody reads. A change to more than four
fields is now one line on the card — "9 changes to HR Settings", the field
labels, and *See the changes* for the table — and Approve on the open form
puts the values in, marks each changed field with what it held ("was:
Naming Series"), counts the changes on every tab that holds some, and opens
the first such tab when the open one has none. The marks go when the form is
saved. A yes/no on a settings page reads On and Off rather than Yes and No.
Four fields or fewer still draw the table, because four rows is readable.

## What is deliberately not here

**No model is named in application code.** An action names a capability; a
workspace names a model; nothing else knows one exists.

**No estimate is ever billed.** A count comes from the provider or from a
parameter we sent, and a call that cannot be metered is charged its hold and
flagged for a person.

**No second runtime.** Redis and the socketio the bench already starts, the
background queue it already has, and nothing else.

**No provider key on a tenant site**, and no way for a workspace to supply its
own. Bring-your-own-key is a support surface, a billing hole and a place for a
key to leak, and a workspace that wants a model we do not offer is asking the
operator for a catalogue entry rather than for an escape hatch.
