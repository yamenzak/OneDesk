"""OneDoc was called OneWriter (P2.3): its two roles, the `one_app` that
names it and the defaults keyed by the old name take the new one
(one/renaming.py). Its module, folder and doctypes keep their names. Run
before the doctypes are synced; safe to run twice."""

from onedesk.one.renaming import app_renamed


def execute():
	app_renamed("OneWriter", "OneDoc", {"OneWriter User": "OneDoc User", "OneWriter Manager": "OneDoc Manager"})
