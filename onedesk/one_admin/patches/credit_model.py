"""A spend's model as a link to it, and the spends a workspace's calls wrote
as nobody (Guest), for the rows written before ledger.commit said either."""

from onedesk.one_admin import ledger


def execute():
	ledger.mend()
