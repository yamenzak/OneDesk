"""What OneAI does in OneAccount: it reads, and changes nothing. One's own
tools answer who is in the workspace, the plan, its credits and its domains
(one/ai.py, which reads them from center.py), and every call here that
changes something is a person's to make (NOT_FOR_AI)."""

REACH = {}

NOT_FOR_AI = {
	"center.save": "A profile and a person's access are saved by the person changing them, never by OneAI.",
	"center.sign_out_elsewhere": "Signing out your other sessions is yours to do, never OneAI's.",
	"center.sign_out_everywhere": "Signing somebody out everywhere is an administrator's decision, never OneAI's.",
	"center.send_reset": "A password reset mail is sent by an administrator who chose to, never by OneAI.",
	"center.set_enabled": "Letting somebody sign in, or stopping them, is an administrator's decision, never OneAI's.",
	"center.invite": "Inviting somebody gives them the workspace, so an administrator does it, never OneAI.",
	"center.invite_again": "A new invitation is sent by an administrator who chose to, never by OneAI.",
	"signin.sign_out": "Ending one of your sessions is yours to do, never OneAI's.",
	"signin.update_password": "A password is changed by its owner, never by OneAI.",
	"devices.save": "Naming a company device and who uses it is an administrator's record, kept by hand.",
	"devices.lost": "Marking a device lost turns its passkeys off, so an administrator does it, never OneAI.",
	"devices.retire": "Retiring a device turns its passkeys off, so an administrator does it, never OneAI.",
	"devices.retire_passkey": "Turning a passkey off locks somebody out of a device, so an administrator does it, never OneAI.",
	"bills.payment_portal": "Paying is done by the person paying, never by OneAI.",
	"bills.to_books": "An invoice from One goes into the books when somebody chooses to put it there.",
	"closing.prepare": "Getting ready to close the workspace is the billing owner's decision, never OneAI's.",
	"closing.close": "Closing the workspace is the billing owner's decision, never OneAI's.",
	"closing.keep": "Keeping the workspace after asking to close it is the billing owner's decision, never OneAI's.",
	"private.claim": "Claiming a private app installs it, so an administrator does it, never OneAI.",
}
