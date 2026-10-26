# OneAI: scratchpad

Known issues, plans and open questions, kept short. Something done or
answered leaves it.

## Built, not released

- **Search on AI Search** is built and switched off: no workspace has an
  instance, so nothing is written to R2. Releasing it means a Cloudflare AI
  Search instance per workspace (billed from 2026-11-01), its R2 data
  source on the workspace's prefix with the path filter `search/**`, then
  `onedesk.one_admin.search.adopt(tenant)`, and the agreements saying
  copies of what is searched sit at Cloudflare first.
- **Web search** is built and off until an administrator turns it on in
  TrustCenter. Releasing it needs AI Gateway credits or an Exa key in the
  gateway's Provider Keys (alias `default`); the one call tried answered
  402 for want of either. Exa is the provider.

## Known issues

- **Demo checks failing before this work, left alone:** OneCalendar's week,
  OneInventory's sent-out and equipment checks and OneBook's Home fail on
  dates that moved since the demo was seeded, and
  `oneai_is_told_what_every_place_shows` finds Settings › Mail and
  Mail Templates with no sentence for OneAI (Masters went in docs/ONE.md stage 5). None touch OneAI's reading.
- **Five reading scenarios have no sample yet:** a voice note, several
  attachments in one mail, a PDF longer than one Clairic pass, the same
  invoice twice, and a currency written as a word (docs/AICENTER.md, stage
  4). The readers handle the first four; the fifth relies on the talk read.
- **The demo workspace isn't connected to a control plane on this bench,**
  so AICenter's Usage and Balance say "Not Connected Yet" and the AI
  Credits report says it isn't available. A workspace OneAdmin runs shows
  both; the READY pass read them in code and checks only.
- **Fixed on the way:** `brief.py` defined `_off()` twice, so turning a
  record type's summaries off never took; the second is `_mailboxes_off()`.

- **The panel's bench misses on building and on mail rules.** On Full
  without thinking it passes 40 of 43; the three it misses (changing an
  extension, a screen with a list, mailing a report) end without the card
  they were asked for. Balanced misses those and approvals, events and a
  screen with mail. Not chased yet.
