"""The people: the owner who paid for the workspace, the team invited from
People with the apps their work needs, and everybody on the payroll as an
employee, office and workshop alike."""

import frappe
from frappe.utils.password import update_password

from onedesk.one_demo.base import COMPANY, make, on, tag

OWNER = "wsadmin@one.test"
APPS = ("OneCRM", "OneBook", "OneInventory", "OneFactory", "OneQuality", "OneProject", "OneHR", "OneMail")

PEOPLE = (
	("Layla", "Haddad", OWNER, "Management", "General Manager", "Female", (2019, 3, 1), 42000, None, dict.fromkeys(APPS, "Manager")),
	("Samir", "Aoun", "samir@one.test", "Projects", "Projects Manager", "Male", (2020, 6, 14), 28000, "Layla", {"OneProject": "Manager", "OneCRM": "User", "OneInventory": "User"}),
	("Omar", "Farouk", "omar@one.test", "Sales", "Sales Manager", "Male", (2021, 1, 10), 24000, "Layla", {"OneCRM": "Manager", "OneProject": "User", "OneBook": "User", "OneWriter": "Manager"}),
	("Huda", "Nasser", "huda@one.test", "Accounts", "Accountant", "Female", (2021, 9, 1), 18000, "Layla", {"OneBook": "Manager", "OneInventory": "User", "OneProject": "User", "OneAccount": "Manager", "OneWorkbook": "Manager"}),
	("Karim", "Mansour", "karim@one.test", "Purchase", "Procurement Officer", "Male", (2022, 2, 20), 15000, "Samir", {"OneInventory": "Manager", "OneFactory": "User", "OneQuality": "Manager", "OneBook": "User", "OneProject": "User"}),
	("Mariam", "Saleh", "mariam@one.test", "Human Resources", "HR Officer", "Female", (2022, 5, 3), 15000, "Layla", {"OneHR": "Manager", "OneMail": "Manager", "One": "Manager", "OneCalendar": "Manager"}),
	("Rania", "Sabbagh", "rania@one.test", "Projects", "Site Engineer", "Female", (2022, 8, 15), 16000, "Samir", {"OneProject": "User", "OneInventory": "User"}),
	("Nadia", "Khoury", "nadia@one.test", "Design", "Designer", "Female", (2023, 3, 1), 14000, "Samir", {"OneProject": "User", "OneSlide": "Manager"}),
	("Tariq", "Haidar", "tariq@one.test", "Workshop", "Workshop Supervisor", "Male", (2020, 11, 2), 12000, "Samir", {"OneProject": "User", "OneInventory": "User", "OneFactory": "Manager", "OneQuality": "User"}),
	("Yousef", "Bakr", "yousef@one.test", "Workshop", "Installer", "Male", (2023, 7, 9), 6500, "Tariq", {"OneInventory": "User", "OneFactory": "User"}),
	("Arun", "Kumar", None, "Workshop", "Fabricator", "Male", (2021, 4, 12), 4800, "Tariq", None),
	("Ravi", "Menon", None, "Workshop", "Fabricator", "Male", (2022, 1, 17), 4500, "Tariq", None),
	("Joseph", "Mathew", None, "Workshop", "Glazier", "Male", (2022, 10, 3), 4600, "Tariq", None),
	("Bilal", "Ahmed", None, "Workshop", "Installer", "Male", (2023, 2, 6), 4200, "Tariq", None),
	("Imran", "Khan", None, "Workshop", "Installer", "Male", (2024, 5, 20), 4000, "Tariq", None),
	("Sanjay", "Patel", None, "Workshop", "Driver", "Male", (2024, 9, 1), 3800, "Tariq", None),
	("Fatima", "Zahra", None, "Accounts", "Accounts Assistant", "Female", (2025, 1, 12), 7000, "Huda", None),
	("Noor", "Hassan", None, "Sales", "Estimator", "Female", (on(2, 1).year, 2, 1), 9000, "Omar", None),
)

ABILITIES = {"samir@one.test": ("OneProject Manager",)}


def run(password=None):
	from onedesk.one.people import set_access
	from onedesk.one_account.center import invite
	from onedesk.one_demo.setup import BUILDER

	frappe.db.set_single_value("System Settings", "enable_password_policy", 0)
	if not frappe.db.exists("User", OWNER):
		with _as(BUILDER):
			invite(OWNER, "Layla", "Haddad", dict.fromkeys(APPS, "Manager"))
	set_access(frappe.get_doc("User", OWNER), dict.fromkeys(APPS, "Manager"), 1, told=False)
	for first, last, email, *_rest, access in PEOPLE:
		if not email or email == OWNER:
			continue
		with _as(OWNER):
			if frappe.db.exists("User", email):
				set_access(frappe.get_doc("User", email), access, 0, told=False)
			else:
				invite(email, first, last, access)
	for _first, _last, email, *_rest in PEOPLE:
		if email and password:
			update_password(email, password)
	for email, held in ABILITIES.items():
		frappe.get_doc("User", email).add_roles(*held)

	for name in {one[3] for one in PEOPLE}:
		if not frappe.db.exists("Department", f"{name} - {_abbr()}") and not frappe.db.exists("Department", name):
			make({"doctype": "Department", "department_name": name, "company": COMPANY})
	for name in {one[4] for one in PEOPLE}:
		if not frappe.db.exists("Designation", name):
			make({"doctype": "Designation", "designation_name": name})

	made = {}
	for first, last, email, department, designation, gender, joined, _pay, _boss, _access in PEOPLE:
		found = frappe.db.get_value("Employee", {"first_name": first, "last_name": last})
		if found:
			made[first] = found
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": first,
				"last_name": last,
				"gender": gender,
				"date_of_birth": f"{1975 + len(first) * 2 + len(last)}-0{1 + len(last) % 9}-1{len(first) % 9}",
				"date_of_joining": f"{joined[0]}-{joined[1]:02d}-{joined[2]:02d}",
				"company": COMPANY,
				"department": _department(department),
				"designation": designation,
				"user_id": email,
				"prefered_email": email,
				"cell_number": f"+97150{len(first)}{len(last)}{abs(hash(first + last)) % 100000:05d}",
				"status": "Active",
			}
		)
		doc.insert()
		made[first] = tag(doc).name
	if frappe.db.exists("Employment Type", "Full-time"):
		for name in made.values():
			if not frappe.db.get_value("Employee", name, "employment_type"):
				frappe.db.set_value("Employee", name, "employment_type", "Full-time", update_modified=False)
	for first, *_rest, boss, _access in PEOPLE:
		if boss:
			manager = frappe.db.get_value("Employee", made[boss], "user_id")
			doc = frappe.get_doc("Employee", made[first])
			doc.update({"reports_to": made[boss], "leave_approver": manager, "expense_approver": manager})
			doc.save()
	_agree()
	_look()


LOOK = {
	"one_brand_colour": "#0E6E8C",
	"phone_no": "+971 4 885 2210",
	"email": "hello@saharaglass.test",
	"website": "saharaglass.test",
	"tax_id": "100234567800003",
	"address_line1": "Plot 597-1024, Dubai Investments Park 2",
	"city": "Dubai",
}


HEAD = {
	"one_top": {"preset": "details", "show": ["address", "phone", "email", "website"]},
	"one_foot": {"preset": "corner", "show": ["website", "tax_id"]},
}


def _look():
	"""The company's look and its letter head, set by the owner as a new
	workspace sets them: General in One's ControlCenter, then Printing."""
	from onedesk.one import control
	from onedesk.one_studio import printing

	with _as(OWNER):
		control.save("general", LOOK)
		if not frappe.db.exists("Letter Head", COMPANY):
			printing.save_letter_head({"letter_head_name": COMPANY, "is_default": 1, **HEAD})


def _abbr():
	return frappe.db.get_value("Company", COMPANY, "abbr")


def _department(name):
	return frappe.db.exists("Department", f"{name} - {_abbr()}") or name


class _as:
	def __init__(self, user):
		self.user = user

	def __enter__(self):
		self.was = frappe.session.user
		frappe.set_user(self.user)

	def __exit__(self, *args):
		frappe.set_user(self.was)


def _agree():
	"""What each person agrees to on their first sign-in, the owner first,
	for the workspace and for themselves (one_legal/gate.py); and the owner
	turns on the optional services, so the demo's faces and logos show."""
	from onedesk.one_legal import gate, services

	for _first, _last, email, *_rest in PEOPLE:
		if not email:
			continue
		with _as(email):
			waiting = [row["document"] for row in gate.standing() if not row["accepted"]]
			if waiting:
				gate.accept(waiting)
			if email == OWNER:
				for one in services.standing():
					if not one["on"]:
						services.switch(one["key"], 1)

