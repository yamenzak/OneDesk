# Webhooks

A webhook tells another system, such as Zapier, Make, n8n or your own server,
when a record is created or changed. Automation › **Webhooks** lists them, and
**Webhook Calls** lists every call each one made. Only administrators see
either.

## Adding a Webhook

1. Choose the record type and the event: created, changed, submitted,
   cancelled or deleted.
2. Enter the address the other system gave you.
3. Choose what to send: JSON with the record's fields, such as
   `{"customer": "{{ doc.customer_name }}", "id": "{{ doc.name }}"}`, or a
   list of fields, each under the name the other system expects.
4. Add a header if the other system needs a key. Turn on **Enable Security**
   to sign each call with a secret it can check.
5. Set **Max Retries** to retry a failed call, up to five times, waiting
   longer each time.

## Limits

- A webhook must be on a record type you can open, and can only send fields
  you can read. You can't send a salary above your level.
- It sends every record of its type on its event. To send only some, such as
  won deals, use an [automation](automations) with a Call Webhook step.
- What it sends can only use the record's fields, as `{{ doc.field }}`.
- It uses https to an address on the public internet, never an internal one,
  even through a redirect.

## Webhook Calls

**Webhook Calls** shows each call's record, what was sent, the response and
its status:

| Status | What it means |
| --- | --- |
| **Delivered** | The other system answered. |
| **Failed** | It will be retried. |
| **Exhausted** | No more retries. |

Each morning, administrators are told of any calls exhausted the day before
(**Webhooks Failing**).

{one_ai} offers **Are the webhooks working?**, and on the calls, **Why did these
fail?**
