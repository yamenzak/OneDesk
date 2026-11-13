"""OneChat's role, made before its doctypes so their permissions resolve."""

from onedesk.one import rights


def execute():
	rights.made("OneChat User")
