import frappe, time
from onedesk.one_admin import office
def run():
    frappe.set_user("Administrator")
    tenant = frappe.get_all("Tenant", {"is_house": 1}, pluck="name")[:1] or frappe.get_all("Tenant", pluck="name", limit=1)
    print("tenant", tenant)
    for i in range(6):
        try:
            made = office.convert(tenant[0], "quote.docx", open("/tmp/quote.docx", "rb").read(), reference="trial")
            print("ok", made["credits"], made["seconds"], made["data"][:8]); break
        except office.Refused as e:
            print("refused", e); time.sleep(40)
    frappe.db.commit()
