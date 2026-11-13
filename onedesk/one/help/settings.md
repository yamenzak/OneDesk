# Settings

## The Workspace's Settings

One's {control_center} holds the workspace's own settings, a tab for each, and
only administrators see it. Each tab saves on its own, from the top right.

- **Company**: the workspace's name, company, country and currency, set when
  the workspace was created. They can't be changed here, and the currency
  can't change once there are transactions. Then **Contact** (**Phone**,
  **Email**, **Website**, **Tax ID**) and the **Address**, saved as the
  company's own, so new invoices use it. Fill these in once and printing never
  stops to ask for them. **Address in Mails** is printed at the bottom of every
  email the workspace sends. It starts as the company's address and follows it
  when the address changes, until you write something else; empty, mails have
  none.
- **Branding**: the **Company Logo** on printed and sent invoices, quotations
  and orders, the **Brand Colour** at the top of letter heads, and the **Frame
  Colour**, the rail and the bars around every screen, for everyone; leave it
  empty for {one}'s own. The Company Logo doesn't replace {one}'s own logo.
- **Region and Formats**: the default language and time zone for people who
  haven't chosen their own in Profile, and how dates, times and numbers are
  shown, with a line showing how they'll look. Then three tiles: **Rounded
  Totals**, **Totals in Words** and **Currency Symbol**, each with its switch,
  and under them the total of a sale as it will read with them.
- **Sign-in**: the rules below.
- **Sharing**
  - **Calendar Links**: when off, every calendar link stops working and no new
    ones can be made.
  - **Record Sharing** lets people share a record with someone who couldn't
    otherwise open it. When off, no one can.

If another administrator saved while you had the page open, the page tells you
instead of saving over their change.

## Sign-in Rules

**Sign-in**, in {one}'s {control_center}, sets how everyone signs in, a tile for
each part. Save from the top right.

- **Two-Factor** asks for a code after the password, for administrators only
  or for everyone. Each person sets it up at their next sign-in, with an
  authenticator app or by email.
- **Passkeys** and **Email Link** let people sign in without a password, with
  a passkey on their own device or a link sent by email. Passkey sign-in is on
  to begin with, and turning it off takes the button off the login page and
  stops the offer after signing in.
- **Passwords** sets how strong a new password must be, and **Passwords
  Expire After** asks for a new one once that many days have passed.
- **Sessions**: **Signed Out After** is how long someone stays signed in while
  they're not using {one}, and **One Device at a Time** signs a person out
  everywhere else when they sign in on a new device.
- **Lockout**: after **Wrong Passwords Before a Lockout** wrong passwords in a
  row, sign-in is blocked for **Locked Out For**.

{one_ai} offers **Is signing in here safe enough?** The answer covers the
sign-in rules, the number of people, passwords over a year old and last
week's failed sign-ins, with what to change.

## Pictures

**Pictures**, in {one}'s settings, is where every picture of a contact, a
customer or anyone else comes from.

**From the Web** has the two optional services: **Pictures from Gravatar**
and **Logos from Google**. They are the same switches as in {trust_center}, and
turning one on asks you to agree to what it sends, in the same way.

**Drawn** has a row for each kind of record: contacts, leads, customers,
suppliers, employees, users, manufacturers, brands and banks. Click its
picture to see every style, drawn from one of your own records' names, and
click one to use it. **None**, the letters, is the default.

- A picture somebody put on a record, or one found on Gravatar, is kept.
- Records with no picture get one a minute or two after you pick a style,
  and every new record gets one too. Picking another style redraws only the
  drawn pictures, and **None** takes them off again.
- The pictures are drawn on your workspace by DiceBear, which comes with
  One. Nothing is sent anywhere, so it isn't an optional service and
  changes nothing you agreed to.
- Each style is somebody's artwork. Hover over a style to see who drew it,
  and each picture carries the artist's name and licence inside it.

## Starting Again

**Start Again** is at the foot of the Company tab in {one}'s {control_center}. **Delete All
Transactions** deletes every sale, purchase, stock move, project, payslip,
lead and asset, for a workspace that tried {one} with made-up records.
Customers, suppliers, items, employees, accounts and settings stay. It is a
Transaction Deletion Record, which runs in the background; the page it opens
shows how far it has got.

## Turning an App Off

**Apps**, at the bottom of the rail above your picture, has **Turn Apps On or
Off** at its foot for administrators. Click an app's card to turn it off for the whole workspace:
it leaves everybody's rail, and the record types only it lists leave search,
the record-type pickers of Dynamic Link fields, and forms, where an empty field
linking to one is hidden. Nothing is deleted or locked. A link to one of its
records still opens it, on Home; {one_ai} still files into it; turning it
on again brings everything back. One itself can't be turned off.

Some apps can't be turned off once they hold records the law or another app
needs, and their card says why: {one_book} once it has a ledger entry or a
submitted invoice, {one_inventory} once stock has moved, and {one_hr} once a
salary slip is submitted. {one_crm} and the rest can always be turned off.

A card that says **Needs** names the apps it can't run without: {one_factory}
needs {one_inventory}, and {one_studio} needs {one_ai}. Turning it on turns
those on too, and an app another one needs says **Needed by** and can't be
turned off until that one is.

**{one_ai}** and its **Reading** have cards there too. {one_ai} off means nobody can
ask it anything: the {one_ai} button, the chat, the field explanations and the
writing help go, and nothing in the workspace calls a model, {one_hr}'s
screening and grievance triage included. Reading needs {one_ai}, so it goes
off with it, and can't be turned on until {one_ai} is. Reading off stops
reading mail and files: its rows leave the bar and {one}'s panel, and its
switches can't be turned on. What they read and filed before stays. A
{one_studio} extension waits for {one_ai}'s review, so none can be turned on while
{one_ai} is off.

**{one_portal}** off closes the portal. Nobody outside can sign in, anybody
signed in is signed out, links to records and invitations stop opening, and
every **Portal** button goes. Nobody is uninvited and no link is revoked:
turned back on, they all work as they did.

## Private Apps

**Private apps** are made for one customer. Somebody who administers the
workspace types the code they were given at the bottom of **Turn Apps On or Off** and presses
**Add**. The app is installed on the workspace, which takes a few minutes,
and its card says *Installing…* until it is on the rail. A private app
can't be turned off, now or later.
