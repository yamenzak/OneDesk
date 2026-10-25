# Reading and writing

**OneMail** in the dock opens every mailbox you have access to, the
workspace's first, then shared ones, then your own. Folders list
conversations newest first. A conversation shows all its messages, including
your replies, with older ones collapsed.

A connected mailbox is checked for new mail every minute, and the list
updates on its own. **Refresh**, beside the search box, reloads it now.

Remote pictures are hidden until you click **Show pictures**, because loading
them tells the sender you opened the message.

**Working with several conversations:** select them with their checkboxes,
or with Shift and Ctrl, then mark read, star, move, archive or delete them.
Moving, archiving and deleting can be undone with **Undo** for a few seconds.
Deleting from Trash is permanent.

**Keyboard shortcuts:**

| Key | Action |
| --- | --- |
| `j` / `k` | Next / previous conversation |
| `e` | Archive |
| `#` | Delete |
| `r` / `a` / `f` | Reply / Reply all / Forward |
| `s` | Star |
| `u` | Mark as unread |
| `c` | New email |
| `/` | Search |

**Search** supports `from:`, `to:`, `subject:`, `has:attachment`,
`is:unread`, `is:read` and `is:starred`. Other words are searched anywhere in
the message. For example, `from:ana subject:"price list" is:unread` finds
unread mail from Ana with "price list" in the subject.

**Writing:** **New Email** at the top starts a message, and **Reply**,
**Reply all** and **Forward** answer the one you're reading. The email window
opens in the bottom-right corner, and you can minimise it and keep reading. You can schedule a message with the
arrow beside **Send**, undo it for a few seconds after sending, ask for a read
receipt or a copy to yourself from **⋯**, and link it to a record.

**Signatures** belong to the address, not the person. Set one under
**Signature** in the mailbox's **⋯** menu. It's added to every email sent
from that address. Only a Workspace
Administrator can change the signature of a workspace mailbox.

A signature is one of six styles drawn from what One already knows: the
holder's name, job title and numbers, and the company's name, logo, colour,
website and address. The tab shows the chosen style large, with a small card
for each style under it; pointing at a card shows that style. **Show** picks
which details appear, Company Name among them. A shared mailbox signs as the
company. The two logo styles are offered only once the company has a logo.
**Custom** is written by hand, starting from Simple's lines, and is never
redrawn. A style is drawn when it's saved, so a later change to the company
or the person shows up the next time it's saved (`signatures.py`).

The signature isn't put in the compose window's editor, which would flatten
its layout into paragraphs. It shows under the editor as it will be sent,
with **Remove** to leave it off one email, and goes in above the quoted mail
as the email is sent (`mail_compose.js`). The company logo goes inside the
email as an inline image rather than as a link to the workspace, which mail
clients block until asked: the signature keeps only the logo's path, and
`signatures.inline_logo` marks it to be embedded in the copy that is queued.
