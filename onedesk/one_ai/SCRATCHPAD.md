# OneAI: scratchpad

Known issues, plans and open questions, kept short. Something done or
answered leaves it.

## Built, not released

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
- **Intake for buying, from OneInventory's pass (6 Nov 2026).** An offer
  with one line matching no item is dropped (`money.quotation`), where the
  sales order proposes; it never names its request for quotation, so an
  emailed quote is missing from Compare and the request's head. A
  supplier's order confirmation is grouped with its order and changes
  nothing (its dates); a supplier's price list never becomes Item Prices.
- **Intake for selling, from OneCRM's pass (6 Nov 2026).** A customer's
  order names our quotation, but the draft Sales Order is built from its
  lines, not through `make_sales_order`, so the quotation and the deal never
  become Ordered. An enquiry from a known customer or lead makes nothing
  (it should make an Opportunity), an acceptance by mail changes nothing,
  and a complaint has no kind (`understand.py`), so no Issue is made.
- **Intake for the books, from OneBook's pass (6 Nov 2026).** A receipt
  or an "Already Paid" invoice becomes an unpaid bill with a remark, so it
  shows in what we owe (`money.py` ~117): set `is_paid` with the bank
  account, or draft a Payment Entry. A payment advice takes only the first
  invoice it names and does not check its currency against the party
  account's. Bank lines are told apart only by a hash with the line's
  position, so an overlapping second statement makes duplicates: match on
  date, amount and reference on the same bank account. Not handled: a
  supplier's remittance advice for a payment we made, a customer's credit
  note to us.
