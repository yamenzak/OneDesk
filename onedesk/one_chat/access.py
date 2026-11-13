"""What OneChat lets a role do beyond its records (one/rights.py,
docs/ROLES.md): its one ability, making channels, is one of frappe's
Permission Types on Chat Channel, declared in permission_type/ beside this
file. Who reads a conversation is its members alone (channels.py), which no
ability changes: a conversation is opened to somebody by adding them to it."""

from frappe import _lt

from onedesk.one import registry

APP = registry.name("one_chat")

# Everybody talks in OneChat: its User role is given to every person
# (rights.everyone).
EVERYONE = "OneChat User"

DOCTYPE = "Chat Channel"

TITLE = "title"

WORKSPACE = _lt("Workspace")

SCOPE_LABELS = {"none": _lt("No"), "all": _lt("Yes")}

ABILITIES = [
	{
		"key": "channels",
		"group": WORKSPACE,
		"label": _lt("Make Channels"),
		"kind": "switch",
		"all": "chat_channels",
		"about": _lt("Make a channel and choose who is in it."),
	},
]

# Nothing of OneChat's is given on one record.
SHARED = ()

# OneChat's one role and what it starts with: made and written once on
# migrate (rights.settle), and shown in Help ({roles}).
DEFAULTS = {
	"OneChat User": {"channels": 1},
}
