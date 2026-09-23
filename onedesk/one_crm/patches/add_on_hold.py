"""The On Hold stage, on a workspace whose stages were seeded without it."""

from onedesk.one_crm import stages


def execute():
	stages.add_hold()
