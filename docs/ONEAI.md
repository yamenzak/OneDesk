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

**A model nothing could price is not sellable.** The parser returns what it could
not read alongside what it could, and a model with a gap lands as `Needs Review`
carrying the wording that defeated it. There is no default price, because the
failure mode of a default is billing somebody a number we invented.

**The sync never overrules the operator.** It creates rows and refreshes facts.
Whether a model is *offered* is a decision and stays one. The only two decisions
it makes on its own are the ones it must: a model that stopped being priceable
comes off sale, and a model the provider withdrew is marked gone.

**A capability is what the picker filters on.** An action declares the capability
it needs — text generation, vision, embedding, speech — and the model picker on
that action shows only models that have it. Nobody picks a model that cannot do
the job and finds out at the call.

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

**AI 3 — the ledger.** `Credit Ledger Entry` in One Admin, balance as a sum,
expiry, reserve and commit under a row lock. No AI in this stage at all: it is an accounting
module and is tested like one.

**AI 4 — pricing and the three-step call.** Markup per model, credits per dollar,
`ceiling()` from an action's limits, and the hold/call/settle in `gateway.py`.
Metering per provider lands here, with a saved response from each.

**AI 5 — actions.** The `AI Action` fixture, the per-workspace `AI Action
Setting` with its model picker filtered by capability and its appended wording,
and the first two real actions so the shape is proved by use rather than by one
speculative caller.

**AI 6 — top-ups.** Stripe checkout from the One area, a webhook that posts a
grant, and the idempotency that stops a retried webhook granting twice. Packs
rather than arbitrary amounts, so there is a price list rather than a calculator.

**AI 7 — tools.** The schema builder off type hints, the Frappe read surface, and
the rule that every one of them runs as the session user — with the test that
tries to read past a permission and is refused.

**AI 8 — proposals.** `AI Proposal`, the card, and Apply as an ordinary write by
an ordinary person.

**AI 9 — streaming.** The background run, the run id, the realtime room, and what
the browser shows while it waits.

**AI 10 — the operator's screens.** OneAdmin: the catalogue with its Offered
switch, the rates, the markup, and usage per workspace. Last on purpose — every
number it shows has to exist before there is a screen worth drawing.

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
