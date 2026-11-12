"""Who may do what in OneQuality, where ERPNext's defaults do not fit:
ERPNext gives quality management to a Quality Manager alone, and lets every
desk user read it. Its Quality User records and works them.

A role that reads one already, by ERPNext's rules or the workspace's, keeps
what it has (one/roles.py `give`).
"""

from onedesk.one import roles

USER, MANAGER = "Quality User", "Quality Manager"

QUALITY = (
	"Quality Goal",
	"Quality Procedure",
	"Quality Review",
	"Quality Action",
	"Non Conformance",
	"Quality Meeting",
	"Quality Feedback",
)

GIVEN = {doctype: {USER: roles.WORK, MANAGER: roles.MANAGE} for doctype in QUALITY} | {
	"Quality Feedback Template": {USER: roles.USE},
}

RAISED = {"Quality Feedback Template": {MANAGER: roles.MANAGE}}
"""ERPNext lets its Quality Manager read feedback templates and nothing
more, so `give` would leave it there and nobody could make one."""


def settle() -> None:
	roles.give(GIVEN)
	roles.raise_once(RAISED)
	roles.open_report("Review", USER, MANAGER)
