# Printing

How the workspace's documents look on paper: letter heads and print formats.
Setup › **Printing** shows both. Only administrators see this, and only
formats for record types they can open. Print headings are under Setup ›
**Lists**.

## Letter Heads

A letter head is the header and footer of every printed page. Each letter head
shows as a card with a full page, as it prints. The star makes one the
default. Click a card to open it: the window has **Header** and **Footer**
tabs on the left, each a list of presets with its options under it, and the
page on the right. Pointing at a preset shows it on the page; clicking keeps
it.

**Edit in Builder** opens the letter head in the print format builder
instead, where the header and footer are each an image or HTML. A header or
footer edited there stays as written. Choosing a preset again replaces it.

**Default** prints a letter head on every document unless another is chosen.
**Disabled** keeps it but stops offering it. The workspace's standard letter
heads can only be made the default or disabled.

## Headers

The header uses one of thirteen presets, filled in from One's settings
(Company and Branding):

| Preset | What it looks like |
| --- | --- |
| **Classic** | The logo on the left, the company stacked on the right. |
| **Columns** | The logo on the left, the address and contacts in columns under small grey labels. |
| **Ledger** | The logo on the left, address, phone, email and tax number two by two under labels in the Brand Colour. |
| **Strip** | The logo on its own, then every detail in a labelled row across the page. |
| **Masthead** | The logo centred over three columns. |
| **Centred** | Everything centred. |
| **Window** | Everything top right, leaving the left free for the address a letter goes to. |
| **Accent** | A short bar in the Brand Colour over the logo. |
| **Wordmark** | With no logo, the name in large spaced capitals. |
| **Minimal** | The name and contacts on one line. |
| **Tinted** | The company on a faint tint of the Brand Colour. |
| **Band** | A band in the Brand Colour, the name or the logo on it. |
| **Logo Only** | The logo and nothing else. |

Under the presets, tick what it should **Show** (name, address, phone, email,
website, tax ID), set the **Logo Height**, and turn on the **Brand Line**, a
line in the Brand Colour under the header.

A company with no logo shows its initials on the Brand Colour next to its
name. The name isn't repeated next to a logo unless **Name** is ticked, for a
logo that is only a symbol. A light Brand Colour is darkened wherever it is
text, so it still reads; lines and bands keep it as it is. A UAE company's
tax number is its **TRN**. When any of these details change in One's
settings, including the Brand Colour, every preset header and footer updates.

## Footers

The footer uses one of nine presets, or **None**:

| Preset | What it looks like |
| --- | --- |
| **Centred** | One line. |
| **Two Sides** | The name and address on the left, the rest on the right. |
| **Fact Strip** | Each detail in a column under a small label. |
| **Legal** | The name, address and tax number centred, contacts under them. |
| **Accent** | A short bar in the Brand Colour over one line. |
| **Corner** | The logo or the name on the left, the rest on the right. |
| **Spread** | Each detail in an equal share of the width. |
| **Logo Above** | The logo centred above the line. |
| **Tinted** | The line on a faint tint of the Brand Colour. |
| **None** | No footer. |

A new letter head starts with the Centred footer, showing the phone, website
and tax number. Tick what else to **Show**, including the **Logo**, add a
**Note** of your own, such as "Thank you for your business.", and turn on its
**Brand Line** if you like.

The page number isn't part of the footer. It's part of the print format
(**Page Number**, in the builder), and it prints on every page.

## Print Formats

**Printing** shows the same cards as a record's **Settings › Print Formats**:
one group for each record type the workspace made a format for, with the
other formats it can print with. Click a page to preview it, the star to make
it the default, or the name to open it in the builder.

1. Click **New**.
2. Enter a name and choose what to **Start From**: a copy of one of the record
   type's formats, or all of its fields.
3. The format opens in the builder.

A format belongs to one record type. A printed record stays inside its app,
with that app's rail.

## Print Formats One Ships

Everything that leaves the company prints from a format of One's unless the
workspace chooses another: One Quotation, One Sales Order, One Sales Invoice,
One Payment Receipt, One Delivery Note, One Purchase Order, One Request for
Quotation, One Payslip, One Job Offer and One Appointment Letter. Each prints
under the default letter head, with its title and total in the company's
Brand Colour. To change one, open it in the builder and save a copy, which
the star then makes the default.

Their blocks are in the builder's **Library**, for any format of the
workspace's own:

| Block | What it shows |
| --- | --- |
| **One Title** | What the paper is (an invoice, a credit note, a receipt) and its number. A Print Heading chosen on the record replaces it. |
| **One Party** | Who it's for, their address, contact and tax ID, and where the goods go when that's somewhere else. |
| **One Details** | Its dates and references, the ones that are set. |
| **One Totals** | The subtotal, discount and each tax, the total, what's paid and still owed, the total in the company's currency when the record is in another, and the total in words. |
| **One Payment Schedule**, **One Bank Details** | When it's due, and the company's bank account to pay into, its default one first. |
| **One Payslip** | Earnings, deductions and net pay. |
| **One Payment** | The amount and the invoices it settles. |
| **One Signatures** | A line for each side to sign, on a quotation, a delivery note, a job offer and an appointment letter. |

## HTML Blocks

In the builder, a format is made of the record's fields, tables, text, images,
barcodes, the standard field templates and **Custom HTML** blocks.

- An HTML block is a template of the record and nothing else. It can use the
  record's fields and rows (`{{ doc.customer_name }}`,
  `{% for row in doc.items %}`), a field's formatted value, conditions,
  loops, translated words and plain filters.
- Every value is escaped. Scripts, forms, frames and images from other sites
  are removed. The same applies to a letter head's HTML, which can't contain
  template code at all.
- Images must be uploaded to the workspace.
- Typst blocks, formats written by hand, and styles that load anything from
  another site aren't available, since each would print exactly what's
  written, on the workspace's address.

## Designing With OneAI

OneAI offers **Suggest a letter head**, **Tidy our footer**, **Design a letter
head from our details**, **Design a clean invoice format** and **Which format
do invoices print with?** Each suggestion is a card an administrator
approves. **See the Page** on the card previews it first: a format on the
record type's latest record, or a letter head's header and footer.

- **Letter heads**: OneAI can change an existing header or footer as well as
  create one. Ask it to remove the footer's line or add a note, and only that
  changes. It can use any preset, or write HTML from the company's details,
  where [icon:phone], or any other icon's name, shows that icon in the Brand
  Colour.
- **Defaults**: OneAI can also suggest the default letter head, and which
  format a record type prints with.
- **Model**: designing a format uses a stronger model than the chat, which
  One picks.
- **Checks**: a layout that would print badly, such as an empty section, a
  table wider than the page, or an invoice without its customer or total, is
  fixed before you see a card. If it still can't be fixed, OneAI says nothing
  was made.

## How OneAI Lays Out Formats

- **Blocks**: OneAI designs a format for any record type from the builder's
  own blocks, so it opens in the builder like any other. It uses an HTML
  block only for a part the blocks can't show, such as a stamp, a grid of
  terms or a figure calculated from the rows, or across the whole body for a
  page designed from end to end.
- **Layout**: it starts from a standard layout for the record type and changes
  only what you ask, so the same request gives the same result. For an
  invoice, quotation, order or bill, that's who it's for on the left, the
  dates on the right, the items in one table, the totals below next to the
  amount in words, and the terms last.
- **Style**: by default it uses a house style based on the standard print
  style, with small muted labels, space between sections, an items table
  under a soft header without a box, and the totals as label and figure on
  one line, with the grand total above a rule. A look you ask for, such as a
  colour, a band behind the title or a typeface, replaces the house style. A
  typeface is set with the format's **Google Font** setting.
- **Properties**: it can set any property the builder shows, by the builder's
  own name: a section's background, padding, margin, radius, borders and when
  it prints, a field's size and colours, a table's style, which rows print and
  column widths, barcodes, images, repeaters, and the page's font size,
  margins and colours. You can keep editing all of it in the builder.
- **HTML blocks**: in the house style these use cards, large figures, status
  badges, stamps, tables and label and value rows, in One's own colours. They
  can only use the record's fields and rows, conditions, loops and plain
  filters.
