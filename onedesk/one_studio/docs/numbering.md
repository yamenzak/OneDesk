# Numbering

How each record type is named when a record is created: an invoice
ACC-SINV-2026-00006, a customer by its name, or a project by its title. Only
administrators see this, and only for record types they can open.

## The List

Setup › **Numbering** shows every record type you can open that uses a naming
series, a naming method the workspace chose, or naming rules:

| Column | What it says |
| --- | --- |
| **Naming Rule** | How a new record is named. |
| **Series** | The series or expression. |
| **Next** | The exact name the next record gets, where it can be known. |
| **Document Naming Rules** | How many naming rules it has. |

Click a row to open that record type's **Settings › Numbering**, where you
make changes. The list refreshes when you close it. **Set Up Naming** lets you
choose any other record type and opens it there. While you type a series or
expression, the window shows the next name it would give, or what's wrong
with it.

You can also ask OneAI: "number our invoices by year", "start this year's
quotations at 500", "name projects by their title", "give government
customers their own prefix" or "is any numbering behind?". OneAI suggests the
change as a card, and nothing changes until you approve it.

## Changing Invoice Numbers

The same steps work for quotations, orders or any record type with a series.

1. Open Setup › **Numbering** and click the **Sales Invoice** row.
2. Click the series to change, or **Add Series** for a new one.
3. Type the series, such as `INV-.YYYY.-.####`. The window shows the next
   name it would give, or what's wrong with it.
4. Tick **Default** so new invoices start with this series.
5. To start from a higher number, set **Current Value**. It can only go up.
6. Click **Update**, or **Add** for a new series.

Existing invoices keep their names. Only new ones use the change.

## Writing a Series

A series is parts separated by dots, read left to right.

| Part | What it gives |
| --- | --- |
| Text, such as `INV-` or `SO/` | Itself, as written. |
| `YYYY`, `YY` | The year (2026), or its last two digits (26). |
| `MM`, `DD`, `JJJ`, `WW` | The month, the day, the day of the year and the week of the year. |
| `FY`, `TFY` | The fiscal year (2025-2026), and its short form. |
| `ABBR` | The company's abbreviation. |
| A field in braces, such as `{department}`, or a field's name on its own | That field of the record. |
| `timestamp` | The time the record is created. |
| One `#` per digit, after a dot | The number: `.#####` gives 00001. Only the first run of `#` counts. |

The number restarts whenever the text before it changes:
`INV-.YYYY.-.####` restarts at 0001 each year, and
`INV-.YYYY.-.MM.-.####` each month. Only letters, digits, spaces and
`- / _ . # { }` are allowed. **Series Format**, in the edit window, explains
the same.

> A series another record type already uses is refused, so two record types
> never share numbers. You can move a series' number up, such as to start a
> new year at 1000, but never down, and never below the highest number a
> record already has.

The edit window shows that number. Each change is kept in the record's
history.

## Choosing How Records Are Named

**Name each new ... by**, at the top of Numbering, sets how a new record gets
its name:

| Option | What it does |
| --- | --- |
| **Naming Series** | The next name in one of its series, for record types that have them. |
| **Field** | The value of a field you choose, such as a project's title or a vehicle's plate. The field becomes required and unique. It's refused while two records share a value, and the message names that value. |
| **Expression** | A pattern written like a series, such as `PRJ-.YYYY.-.####`, for record types with no series of their own. The window shows the next name as you type, and **Use This Expression** applies it. |
| **Set by User** | The person creating the record types its name. Not offered for record types One creates in the background, such as expense claims OneHR files or timesheets from the timer, since no one is there to type a name. These can be named by a field only if that field is always filled in. Records OneAI creates from a document aren't limited this way, since OneAI reads the name or field from the document. |
| **Random** | A random name, for records no one refers to by name. |

**Customer**, **Supplier**, **Item**, **Employee** and **Campaign** have their
own naming options: Customer Name, Naming Series or Auto Name, an Item by its
Item Code, and an Employee by Full Name or Employee Number. The series list
and **Add Series** appear only while the record type is named by a series.

Changes never rename existing records. They apply only to records created
afterwards. Switching back to a series continues from the number it had
reached.

The naming method can only be changed on record types people create
themselves. Ledgers, logs, and the system's and One's own record types are
named by the system. Rules work on all of them.

## Naming Rules

A rule gives a record its own prefix when its fields match, whatever its
naming method: returns as `RET-.YYYY.-`, or government customers as
`CUST-GOV-.YYYY.-`.

1. Click **Add Rule**.
2. Enter the prefix, written like a series but without `#`. The window shows
   the next name it would give.
3. Set how many digits the number has.
4. Under **When**, add conditions, each a field, a comparison and a value. All
   of them must match. A rule with no conditions names every new record.

When two rules match, the one with the higher **Priority** wins. Rules only
check the record's standard fields.
