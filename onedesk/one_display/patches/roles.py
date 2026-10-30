"""OneDisplay's two roles, made before its doctypes so their permissions
resolve: the manager pairs screens and builds channels, the user works a
counter."""

from onedesk.one import rights

ROLES = ("OneDisplay Manager", "OneDisplay User")


def execute():
	for name in ROLES:
		rights.made(name)
