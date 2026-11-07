import frappe, json
def run():
    frappe.set_user("karim@one.test")
    from onedesk.one_quality import home
    r=home.read()
    print(json.dumps(r["figures"]))
    for k,v in r["needs"].items(): print(k, v["count"], json.dumps(v["rows"], default=str)[:300])
