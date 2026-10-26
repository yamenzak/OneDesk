# Address Book

**Contacts** and **Addresses**, under Address Book, are the people and places
the workspace deals with: a customer's buyer, a supplier's accountant, a
site's address. Every app uses the same ones.

The Address Book is one page with two tabs, **Contacts** and **Addresses**.
Search either, and click one to see it beside the list:

- A contact shows their email and phones, who they belong to (a customer, a
  supplier or another record), and **Their Addresses**: the addresses of
  those same records.
- An address shows the address in full, who it belongs to, and **People
  There**: the contacts of those same records.

Click an address or a person to go to it. **Edit** opens it in full to
change it.

**Adding a contact**

1. Open **Contacts** and click **New Contact**.
2. Enter their name, email and phone, and save. **Edit Full Form** shows
   every field.
3. Under **Links**, add the customer, supplier or other record they belong
   to. The contact then shows on that record.

**Addresses** work the same way, with **New Address**: a title, the type,
the lines, city and country, and under **Links** whose address it is.
**Preferred Billing Address** and **Preferred Shipping Address** mark the
one new documents use first.

A contact of a customer or supplier can be invited to the portal (see The
Portal).

## Lists

The short lists records pick their values from: a contact's salutation, a
customer's group, an item's unit, an employee's department. Each app keeps its
own, at the end of its ControlCenter under **Lists**, and its rail has a
**Lists** row that opens them.

- **One**: Salutations, Genders and Address Templates, the Address Book's.
- **OneStudio**: Print Headings.
- **OneCRM**: Customer Groups, Territories, Industries, Market Segments, Lead
  Sources, Lost Reasons, Issue Types and Issue Priorities.
- **OneBook**: Tax Categories and Finance Books.
- **OneInventory**: Item Groups, Brands, Units, Unit Categories, Attributes
  and Supplier Groups.
- **OneProject**: Project Types.
- **OneHR**: Departments, Designations, Branches, Employment Types, Skills, Key
  Result Areas, Grievance Types and ID Document Types.

Lists that carry settings of their own stay in their app's Setup, such as sales
stages, leave types and salary components.

Each one is a list like any other. Lists shows how many values each has;
click one to open it, and the app's other lists are in the pane beside it.

Administrators see every app's lists. An app's managers see their app's and
can add, rename and remove its values. One's and OneStudio's are the
administrators' alone.

## Changing a Value

**Add**, above the list, opens the new value in a dialog. A new customer
group, territory, item group, supplier group or department goes under the top
of its list unless you choose a parent. Click a value to open it: rename and
delete are in its menu, and **Connections** in its side panel lists the
records that use it. Renaming a value changes it on every record that uses
it. A value records still use can't be deleted. You can also add a value
straight from a field on a record, with **Create a new** at the bottom of its
list.

## Address Templates

Print headings are in OneStudio's **Lists**, address templates in One's
(Address Book › **Lists**).

**Print Headings**: the title printed above a document, such as **Tax
Invoice** or **Proforma Invoice**. A print format picks one.

**Address Templates**: how an address is laid out on a printed page and
wherever it's shown, one template per country. The **Default** template is
used for any country without its own. A template names the address's fields,
such as `{{ city }}`, and can leave out a line when a field is empty with
`{% if state %}`…`{% endif %}`. Nothing else can go in it.
