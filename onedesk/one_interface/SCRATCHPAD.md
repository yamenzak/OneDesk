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
