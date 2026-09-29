"""What the provider charged us, for the calls settled before a call kept it
(ledger.mend_costs)."""

from onedesk.one_admin import ledger


def execute():
	ledger.mend_costs()
