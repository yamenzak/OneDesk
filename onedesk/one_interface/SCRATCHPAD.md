# OneInterface: scratchpad

Known issues, plans and open questions, kept short. Something done or
answered leaves it.

## Planned

- **Choosing a look.** Canvas is the only look offered; the workspace
  default `one_look` picks another, and nowhere on screen sets it yet.
- **The main action and two more.** The lab hid every action past the
  third; the renderer keeps them all until the extra ones can move into
  the menu rather than vanish.
- **The rest of the dialog kit.** Ask, Tell, Task, Create and Centre are
  drawn; still to come are the toast, an island's frappe-ui dialog, the
  search-first and kind-first creates, a centre's actions moved into its
  footer, and the create dialog's own foot (Save and what is missing)
  becoming the kit's footer.
- **Callers still say Yes and No.** frappe.confirm keeps whatever words it
  was given; each caller moves to `onedesk.interface.ask` with a verb as
  its screen is walked.
- **Island pages** carry a stamp in the bottom bar until each is replaced
  by a framework screen in the screen-by-screen walk.
- The window's search box draws over an open dialog (seen on New Customer from the Customer list): it should sit under the modal.
- New Customer's create dialog says "Still needed: Customer Name" but shows no Customer Name field on Details.

- **A hidden form per row.** The kit's `useForm` without a `given` form builds
  a second Form of the record, and each builds a record panel (an Item with
  two price rows had three panels). Harmless now; pass the open form where
  there is one, and think about a lighter reader for rows.
- **Money chart axes clip their first letter** ("ED 600,000" on OneCRM's
  Home): frappe-ui's charts measure label widths in Inter (`CHART_FONT_FAMILY`),
  Sand draws another font. One fix for every chart: tell the charts our font.
- **A form's first open on a phone.** At 4x CPU the Item form takes 10.5s
  and a Purchase Order 9.7s (6 November 2026); the server answers in
  60ms. The time is the main thread: frappe's form Toolbar refresh (1.3s)
  and the sidebar's `apply_page_visibility` (1.4s) each read a computed
  style and force a full restyle, and popper measures every popover it
  makes. Profile with `~/tools/browser/cpuprof.mjs`; the many `:has()`
  rules in canvas.css are the first suspect for the cost of each restyle.
- **A v2 board's columns stay in English.** The Pipeline's column headings are the Sales Stage values as stored ("New", "Negotiation") while its strip above says them in Arabic; frappe's kanban v2 draws column titles without __(). For every board (from OneCRM's pass, 6 Nov 2026).
