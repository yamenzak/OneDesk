"""What OneAI does in AccountCenter: it reads, and changes nothing. One's own
tools answer who is in the workspace, the plan, its credits and its domains
(one/ai_workspace.py, which reads them from center.py), and every call here that
changes something is a person's to make (NOT_FOR_AI). Its one action,
Write My Bio, writes words a person then puts in their own profile."""

import frappe
from frappe import _lt

from onedesk.one import registry

REACH = {}

# OneAI's actions here, which are One's: AccountCenter is a centre of One
# (one_ai/actions.py), switched in AICenter under One.
ACTIONS = [
	{
		"key": "write_bio",
		"label": _lt("Write My Bio"),
		"about": _lt("Writes a person's bio on their profile from what they tell it and their employee record."),
		"module": "One",
	},
]

# How much of a person's record a bio is written from: their own words
# first, then their job, and at most this many of each list.
FEW = 5

NOT_FOR_AI = {
	"agent.write_bio": "Writing a bio is asked from a person's own profile, and only fills the field they then save.",
	"center.save": "A profile and a person's access are saved by the person changing them, never by OneAI.",
	"center.sign_out_elsewhere": "Signing out your other sessions is yours to do, never OneAI's.",
	"center.sign_out_everywhere": "Signing somebody out everywhere is an administrator's decision, never OneAI's.",
	"center.send_reset": "A password reset mail is sent by an administrator who chose to, never by OneAI.",
	"center.set_enabled": "Letting somebody sign in, or stopping them, is an administrator's decision, never OneAI's.",
	"center.invite": "Inviting somebody gives them the workspace, so an administrator does it, never OneAI.",
	"center.invite_again": "A new invitation is sent by an administrator who chose to, never by OneAI.",
	"signin.sign_out": "Ending one of your sessions is yours to do, never OneAI's.",
	"signin.reset_two_factor": "Setting two-factor up again on a new phone is yours to do, never OneAI's.",
	"center.reset_two_factor": "Resetting somebody's two-factor is an administrator's decision, never OneAI's.",
	"signin.update_password": "A password is changed by its owner, never by OneAI.",
	"companies.make": "A company builds its own accounts and payroll set-up, so an administrator adds it, never OneAI.",
	"devices.save":"Naming a company device and who uses it is an administrator's record, kept by hand.",
	"devices.lost": "Marking a device lost turns its passkeys off, so an administrator does it, never OneAI.",
	"devices.retire": "Retiring a device turns its passkeys off, so an administrator does it, never OneAI.",
	"devices.retire_passkey": "Turning a passkey off locks somebody out of a device, so an administrator does it, never OneAI.",
	"bills.payment_portal": "Paying is done by the person paying, never by OneAI.",
	"bills.change_card": "A card is given by the person paying, never by OneAI.",
	"bills.set_update_window": "When the workspace is offline for an update is an administrator's decision.",
	"bills.set_auto_topup": "Charging the saved card without asking is an administrator's decision about money, never OneAI's.",
	"bills.update_now": "Taking the workspace offline for an update is an administrator's decision.",
	"bills.set_spend_limit": "A limit on what the workspace spends is an administrator's decision about money, never OneAI's.",
	"bills.to_books": "An invoice from One goes into the books when somebody chooses to put it there.",
	"closing.prepare": "Getting ready to close the workspace is the billing owner's decision, never OneAI's.",
	"closing.close": "Closing the workspace is the billing owner's decision, never OneAI's.",
	"closing.keep": "Keeping the workspace after asking to close it is the billing owner's decision, never OneAI's.",
	"private.claim": "Claiming a private app installs it, so an administrator does it, never OneAI.",
}


def _about_me(told: str) -> str:
	"""What the bio is written from: what the person said, then their own
	User and Employee records, each line only when it has something."""
	from onedesk.account_center import center

	user = frappe.get_doc("User", frappe.session.user)
	lines = [f"In their own words: {told.strip()}" if told.strip() else "", f"Name: {user.full_name}"]
	if user.location:
		lines.append(f"Lives in: {user.location}")
	if user.bio:
		lines.append(f"Bio now: {user.bio}")
	employee = center._employee()
	if employee:
		for one in center._facts(employee, ("designation", "department", "branch", "employment_type", "date_of_joining")):
			lines.append(f"{one['label']}: {one['value']}")
		lines += [
			f"Studied: {', '.join(filter(None, (row.qualification, row.maj_opt_subj, row.school_univ)))}"
			for row in (employee.get("education") or [])[:FEW]
		]
		lines += [
			f"Worked before at: {row.company_name}" + (f", as {row.designation}" if row.designation else "")
			for row in (employee.get("external_work_history") or [])[:FEW]
		]
		skills = frappe.get_all(
			"Employee Skill", filters={"parenttype": "Employee Skill Map", "parent": employee.name}, pluck="skill", limit=FEW * 2
		) if frappe.db.exists("DocType", "Employee Skill") else []
		if skills:
			lines.append(f"Skills: {', '.join(skills)}")
	return "\n".join(line for line in lines if line)


@frappe.whitelist(methods=["POST"])
def write_bio(told: str = "") -> str:
	"""Write My Bio: a short bio in the person's own voice, from what they
	said and their records. It is only words: the person puts it in the field
	and saves it themselves."""
	from onedesk.one_ai import actions, run

	actions.refuse("write_bio")
	if len(told) > 2000:
		frappe.throw(frappe._("Tell {0} a little less, in a few sentences.").format(registry.name("one_ai")))
	return (run.once("bio", _about_me(told), reference=frappe.session.user) or "").strip()
