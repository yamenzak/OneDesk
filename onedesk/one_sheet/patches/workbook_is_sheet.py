"""OneSheet was called OneWorkbook (P2.4): its two roles, the `one_app` that
names it and the defaults keyed by the old name take the new one
(one/renaming.py). Its module, folder and doctypes keep their names. Run
before the doctypes are synced; safe to run twice."""

from onedesk.one.renaming import app_renamed


def execute():
	app_renamed("OneWorkbook", "OneSheet", {"OneWorkbook User": "OneSheet User", "OneWorkbook Manager": "OneSheet Manager"})
