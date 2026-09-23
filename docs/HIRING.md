# Hiring, with OneAI on every step

What OneAI does from the moment somebody decides to hire to the day the new
person starts, what it writes where, what it costs, and what it will not do.
Written before the code, as the plan, and kept as the reference.

## The lifecycle, and where OneAI is in it

HRMS already has every record the walk needs, in order:

    Job Requisition → Job Opening → Job Applicant → Interview → Interview Feedback
      → Job Offer → Appointment Letter → Employee Onboarding → Employee

Nothing below adds a step to that walk or replaces a record in it. OneAI reads
each record as it is made and leaves something on it: a number, a remark, a
draft to approve. A person still moves the applicant from Open to Accepted, and
a model never changes a status.

| Step | What OneAI does | Automatic or asked | Where it lands |
|---|---|---|---|
| Opening | Writes the description and the criteria a strong applicant meets | Asked, from the opening's panel | A change card on the opening |
| Applicant arrives | Reads the CV against the criteria, rates it, places it among the others | Automatic | Two fields and a comment on the applicant |
| Another applicant arrives | Places the new one, and moves the others where the new one changes the picture | Automatic, the same call | The same two fields; a comment on anybody moved far |
| Before the interview | What to ask, and what to know first | Automatic when an interview is made | A field on the interview |
| The interview | Records it, with the candidate's agreement | A person presses Record | An Interview Recording, in five-minute parts |
| After the interview | Transcribes it and remarks on it | Automatic when recording stops | The transcript on the recording; a comment on the interview |
| Feedback | Drafts an interviewer's feedback from the recording | Asked, from the interview's panel | A card creating Interview Feedback |
| Offer, letter, onboarding | Drafts terms, a decline note, an onboarding plan | Asked | Cards, or words in the chat |

## Everything is offered in the panel

No OneAI button goes on a page. What OneAI can do on an applicant, an opening,
an interview or a recording is what its panel offers when it opens there —
the questions ("What should I ask first?") and the jobs ("Screen again",
"Rank the applicants again", "Prepare this interview again", "Transcribe
again"). A job is a suggestion with `run`: the panel calls it on the open
record and says what is happening, with no model call in between. A person
wanting help looks in one place. *Record* stays on the interview, because
recording is not OneAI.

## Numbers are fields, opinions are comments

One rule places everything. **A number goes in a field** because a field sorts, a
list column can show it and a filter can ask for it. **An opinion goes in a
comment** because a comment has an author, a time and a place in the record's
history, and it can be answered by the person who disagrees. **Reference
material an interviewer reads with the candidate in front of them goes in a
field** at the top of the interview, because a timeline is the wrong place to
look for it in a hurry.

Every comment OneAI leaves is written by a user called OneAI — a disabled
account with the OneAI mark as its picture, so the timeline says who wrote it and
nobody can sign in as it.

## The two numbers

**OneAI rating** (`one_ai_rating`, a Rating, five stars) is the applicant against
the opening on their own: how much of what the opening asks for the CV shows. It
is set once, when the CV is read, and changes only if the CV is read again.

**Standing** (`one_ai_standing`, a Percent) is the applicant against everybody
else applying to the same opening. It is the number that moves: every new
applicant is placed, and the others are promoted or demoted where the newcomer
changes the picture — a pool of juniors where everybody sits near 70 is a pool
where the first senior person to apply moves them all down. The list of an
opening's applicants sorts by it.

HRMS's own `applicant_rating` stays exactly what it was: the rating a person
gives. The two OneAI numbers sit beside it and never write to it, so "what the
model thought" and "what we thought" can always be told apart and compared.

This reverses a line in `add_applicant`, which kept the model's opinion out of
the rating because a number a model gave is a number somebody will sort by.
Sorting by it is now the point, so it is a field of its own, labelled as the
model's, with the reasons one click away in the comment.

## One call per applicant

Screening and ranking are one call. The model is handed the opening and its
criteria, the new CV, and every other applicant still in the running as a line
each — their id, their rating, their standing and the brief OneAI wrote when it
read their CV. It answers with the new applicant's assessment and a standing for
everybody. Two calls would read the pool twice and cost twice.

The pool is capped at the forty best-placed applicants still open, and nobody's
name is in it — only the id and what they can do. What was said about a person
is the brief OneAI wrote from their CV, which is also the only thing about them
that is compared.

A standing that moves by fifteen points or more gets a one-line comment on that
applicant saying why ("Moved down: HR-APP-0031 has the same stack and five more
years of it."). Smaller moves are silent; a comment for every shuffle is a
timeline nobody reads.

**Rank the applicants again**, offered in the OneAI panel on an opening, re-places everybody from their briefs alone, with
no CV read again — for when the criteria were edited, or when somebody wants a
clean sort. One call.

## What it is told not to do

The instruction the `screen` action carries says, before anything else, that
the model must not use age, sex, gender, marital or family status, pregnancy,
religion, race, ethnicity, nationality, origin, disability, a photograph or
the sound of a name — and must not infer any of them. A gap in employment is a
question to ask, not a mark against somebody. Where a CV says nothing about a
criterion, the answer is "not shown", not "missing".

The rating never rejects anybody. Nothing changes an applicant's status, sends
them a message or closes a door; the lowest standing is a place in a list a
person reads.

Recruitment is a high-risk use of AI under the EU AI Act, and New York City and
others require notice and audits for automated employment decision tools. What
this design does about that is keep a person as the decider, keep the model's
reasons on the record next to its number, and keep the human rating separate.
What it does not do is the notice or the audit — those are the workspace's, and
the HR Settings switch that turns screening off is where a workspace that may
not use it says so.

## Before the interview

When an Interview is made, OneAI writes **Interview Preparation** onto it: what to
confirm first (gaps, dates, anything the CV leaves unclear), then eight questions
at most, each saying which criterion or which of the interview type's expected
skills it tests and why it is being asked of this person. Questions from an
earlier round's feedback — "ask again about the migration" — come first.

The same list's first half, *know before you call*, is in the screening comment
already, so a hiring manager who phones before booking anything has it.

## Recording an interview

A new doctype, **Interview Recording**, one per sitting, with the interview, who
recorded it, when, how long, whether the candidate agreed, and its parts.

**Agreement first.** The recorder does not start until the interviewer ticks
*Candidate Consented to Recording*, and the recording
keeps who ticked it and when. Recording somebody without telling them is illegal
in many places and hostile everywhere; a tick box is the least that can be asked.

**Five-minute parts.** The recorder is the browser's own MediaRecorder, restarted
every five minutes so each part is a whole file that plays on its own. A part is
uploaded as soon as it closes and transcribed as soon as it lands. So a laptop
that dies in minute forty loses at most five minutes, a transcript is ready a
minute after the interview ends instead of ten, and no part is too big to send:
opus at 24 kbit/s is under a megabyte for five minutes.

**A call in another tab.** An interview over a video call is two voices and a
microphone hears one of them. *Include a call in another tab* asks the browser
for that tab's sound as well and mixes the two before recording.

**Sound is kept for an audit and then let go.** HR Settings says for how many
days (a year by default). After that the parts' files are deleted and the
transcript stays. Before that, only an HR Manager can delete a recording or
its sound; an interviewer who can write to a recording still cannot remove
what was said in it.

## Transcription and remarks

Each part goes to the `transcribe` action with the time it starts at, and comes
back as text with *Interviewer* and *Candidate* and a timestamp on each turn —
the model is not told anybody's name, and does not need to be. When the last
part is transcribed, the transcript is put together on the recording and the
`interview` action reads it against the criteria, the interview type's expected
skills and the questions OneAI suggested, and comments on the interview: what
was shown for each skill, with the minute it was said at; what was not asked;
concerns; what to follow up. A one-line summary goes on the applicant's timeline
too, so the whole story of a candidate is in one place.

Audio can only go to a model that reads sound — Gemini, today, and not Workers
AI, whose chat endpoint carries pictures and nothing else. The `transcribe`
action needs *Transcription*, which a Multimodal model covers.

## Feedback, offer and onboarding

**Draft my feedback from the recording** on the interview makes an Interview
Feedback card for the person asking — their ratings against each expected skill
and a paragraph, from the transcript — which they approve, edit and submit as
their own. It is theirs; OneAI's remarks stay in OneAI's comment.

The offer, the letter and onboarding get suggestions in the panel rather than
automation: *Draft the offer terms* against the opening's range, *Write a kind
decline* for an applicant who was not chosen (in the chat, to be sent from
OneMail when it exists), and *Plan the onboarding* from the designation's usual
activities. None of them is worth a call nobody asked for.

## What it costs a workspace

Automatic calls, and nothing else is automatic:

- one call per applicant — the CV, the opening, and forty lines of pool;
- one call per interview made — the preparation;
- one call per five minutes of recording, and one when it ends.

Each has its own switch in HR Settings, under Recruitment → OneAI, and each
action can be pointed at a cheaper or better model on the OneAI settings screen
like any other.

## Stages

1. **The opening** — *Screening Criteria* on Job Opening; *Write this
   opening* in the panel.
2. **Screening and standing** — the fields, the OneAI user, the `screen` action,
   the background call on every new applicant, the comments, *Screen again* and
   *Rank again*, the switch.
3. **Before the interview** — the `interview` action, *Interview Preparation*.
4. **Recording** — Interview Recording, the recorder, agreement, parts, the
   call-tab mix, retention.
5. **Transcription and remarks** — `transcribe`, the transcript, the remarks.
6. **Feedback, offer, onboarding** — the feedback card and the suggestions.

## What landed, and how it was checked

Every stage above is built. Nothing was run against a live model: each call
was replaced by a canned answer and the rest ran for real on the dev site —
the fields written, the pool re-placed, the comments posted as OneAI, the
interview prepared, a recording made in Chromium with its fake microphone in
three parts, each filed and transcribed in turn, the transcript put together,
the remarks posted, and a two-year-old recording's sound purged with its
transcript kept.

Three things were learned doing it:

- **HRMS names an applicant after their email address**, so the pool shown to
  the model uses labels (`NEW`, `A1`, `A2`…) and the answer is turned back
  into applicants afterwards. A label the model invents reaches no record.
- **A read-only Text Editor draws no bullets or numbers for a plain list.**
  Quill 2 writes every list as an `<ol>` with the marker in a span keyed by
  `data-list`, so *Interview Preparation* is written that way.
- **An account with no model set for Transcription refuses the call** before
  anything is charged, and the recording is marked Failed. *Transcribe again* in the panel
  on the recording retries the parts once a model is picked. On an account,
  the operator sets a default for Transcription, or each workspace picks one
  for *Transcribe* on its OneAI settings.

**Measured live, once.** A 23-second two-voice clip, spoken by espeak-ng and
fed to Chromium as its microphone, recorded as Chrome's `audio/webm`:
`gemini-2.5-flash-lite` took it, answered in 3.3 seconds for 0.59 credits,
told the two voices apart and timed every turn. It misheard two words of
synthetic speech ("before and report" for "before every pour"). The remarks
that followed ran on the account's default text model, Gemma 4 on Workers
AI, took 30 seconds and 1.35 credits, and did not answer with the JSON asked
for — so nothing was written. An answer that cannot be read is now kept in
the error log with its text; before, it vanished. A workspace using these
actions should point *Interviews* and *Screen applicants* at a model that
follows a format, as it does *Transcribe*.

**The level meter.** The recording bar draws the last two seconds of sound as
bars in the OneAI spectrum, and says *No sound — check the microphone* after
eight seconds of silence, which is a muted or wrong microphone rather than a
quiet candidate.

## What is deliberately not here

**No automatic rejection**, and no automatic anything that reaches the
candidate. The first thing an applicant hears is from a person.

**No emotion, tone or "confidence" reading from the recording.** What was said
is evidence; how somebody sounded saying it is not, and a model that claims to
read it is guessing in a way that lands hardest on people who interview in their
second language.

**No video.** Sound is enough for a transcript and a tenth of the size.

**No live transcript during the interview.** A part is transcribed when it
closes; watching words appear while somebody is talking is a distraction for the
interviewer and a cost for nothing.
