# OneAI: scratchpad

Known issues, plans and open questions, kept short. Something done or
answered leaves it.

## Questions

Each says what was done meanwhile, so nothing waited on it.

- **OneMail's OneAI settings stay on each mailbox.** The plan put "reading
  new mail, answering by Automation, the monthly limit per mailbox" in
  AICenter. They are set per mailbox, and OneMail is ready, so moving them
  is a OneMail version and a walk of its settings again. *Meanwhile:*
  AICenter › OneMail lists every mailbox with how far OneAI reads it, and
  each row opens that mailbox's OneAI tab. No OneMail file changed. Say if
  you want them moved into AICenter itself.
- **OneIntake's inbox is called Documents.** The plan said "its inbox
  becomes OneAI's" without a name. *Meanwhile:* the page, its row in One's
  sidebar, the bottom bar and Home's card say **Documents** ("3 waiting in
  Documents"). Say if you want another name.
- **Three doctypes still say Intake: Intake Settings, Intake Action and
  Intake Lesson**, and two notification names (Intake Waiting, Intake
  Weekly). OneIntake left every screen, Help page and clause; these are
  record-type names, and renaming a doctype moves its table and every link
  to it. *Meanwhile:* kept as they are. Say if they should become Reading
  Settings, Reading Action and Reading Lesson.

## Known issues

- **Demo checks failing before this work, left alone:** OneCalendar's week,
  OneInventory's sent-out and equipment checks and OneBook's Home fail on
  dates that moved since the demo was seeded, and
  `oneai_is_told_what_every_place_shows` finds Settings › Mail, Masters and
  Mail Templates with no sentence for OneAI. None touch OneAI's reading.
- **Five reading scenarios have no sample yet:** a voice note, several
  attachments in one mail, a PDF longer than one Clairic pass, the same
  invoice twice, and a currency written as a word (docs/AICENTER.md, stage
  4). The readers handle the first four; the fifth relies on the talk read.
- **Fixed on the way:** `brief.py` defined `_off()` twice, so turning a
  record type's summaries off never took; the second is `_mailboxes_off()`.

- **Chat with its tools is not benched.** It needs a workspace connected to
  an account; `evals.run` asks through the account. Stage 7.
- **Whether chat on Full answers better thinking** is not measured. Stage 7.
