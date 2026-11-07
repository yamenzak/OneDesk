"""Who may do what in OneFactory, where ERPNext's defaults do not fit.

A role that reads one already, by ERPNext's rules or the workspace's, keeps
what it has (one/roles.py `give`).
"""

from onedesk.one import roles

GIVEN = {
	"Subcontracting BOM": {
		"Purchase User": roles.USE,
		"Manufacturing User": roles.USE,
		"Purchase Manager": roles.MANAGE,
		"Manufacturing Manager": roles.MANAGE,
	},
	"Subcontracting Order": {
		"Manufacturing User": roles.USE,
		"Manufacturing Manager": roles.USE,
	},
	"Subcontracting Receipt": {
		"Manufacturing User": roles.USE,
		"Manufacturing Manager": roles.USE,
	},
	"Plant Floor": {
		"Manufacturing User": roles.USE,
		"Manufacturing Manager": roles.MANAGE,
	},
}


def settle() -> None:
	roles.give(GIVEN)
