"""OneAI in OneQuality: what it suggests asking on each of its record types.
It reads them through the generic tools (about_record, read_record,
list_records) and changes none of them."""

from frappe import _lt

REACH = {}

NOT_FOR_AI = {}

_OPEN = {
	"label": _lt("What is still open?"),
	"ask": _lt("Which non conformances and quality actions are still open, against which procedure, and since when?"),
	"expects": "list_records",
}
_FIXED = {
	"label": _lt("What was done about it?"),
	"ask": _lt("What went wrong here, what was done to put it right, and what stops it happening again?"),
	"can": "read",
	"expects": "read_record",
}
_STEPS = {
	"label": _lt("Summarise this procedure"),
	"ask": _lt("Say in a few lines how this work is done, and which goals and problems point at it."),
	"can": "read",
	"expects": "read_record",
}

SUGGESTIONS = {
	"Non Conformance": [_FIXED, _OPEN],
	"Quality Action": [_FIXED, _OPEN],
	"Quality Procedure": [_STEPS, _OPEN],
}
