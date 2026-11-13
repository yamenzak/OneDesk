"""TrustCenter's part of the integration suite (one_demo/check.py runs it):
what everybody agreed to, TrustCenter's services and changes, what OneMail
adds to the agreements, and who sees who agreed."""

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_demo.checking import check
from onedesk.one_demo.people import OWNER


@check
def trustcenter_every_person_has_agreed_and_reads_what_to():
	"""Everybody accepted what they must on their first sign-in, so nothing is
	outstanding; the documents, an old version and what was agreed read back,
	and OneAI reads an agreement."""
	from onedesk.trust_center import agent, gate, reading

	for user in (OWNER, "rania@one.test"):
		with as_user(user):
			assert not gate.outstanding()["blocking"], user
	with as_user(OWNER):
		listed = reading.catalogue()["documents"]
		assert {"terms", "privacy"} <= {one["key"] for one in listed}, listed
		standing = {one["key"]: one for one in reading.overview()["documents"]}
		assert not standing["terms"]["organisation"]["owed"], standing["terms"]
		said = reading.document("terms")
		assert said["html"] and said["version"]
		agreed = reading.history("terms")
		assert agreed and agreed[0]["document"] == "terms"
		assert reading.document("terms", agreed[0]["version"])["version"] == agreed[0]["version"]
		gate.accept(["terms"])
		assert gate.accept(["terms"])["accepted"] == [], "agreeing again at the same version records nothing"
		assert agent.agreement("privacy").get("text")


@check
def trustcenter_trustcenter_services_changes_and_laws():
	"""TrustCenter (docs/READY.md, mechanism 13): Layla's workspace has both
	of OneMail's optional services on, as she agreed in the demo; turned off,
	no picture is asked for; given somewhere new, one is off until she agrees
	again. Rania may not move them. The agreements changed since she agreed
	are told, not asked: nobody is stopped, and each says the day it takes
	effect. Before production nothing is published ahead and a person's own
	policies change without a notice (docs/READY.md, Before production).
	Everything TrustCenter shows reads back for OneMail."""
	from unittest.mock import patch

	from onedesk.one import ready
	from onedesk.trust_center import gate, reading, services
	from onedesk.one_mail import faces

	with as_user(OWNER):
		for one in services.standing():
			if not one["on"]:
				services.switch(one["key"], 1)
		assert all(one["on"] for one in services.standing()), services.standing()
		services.switch("gravatar", 0)
		with patch("requests.get") as asked:
			assert faces.fetch("someone.new@example.com") is None
			asked.assert_not_called()
		services.switch("gravatar", 1)
		assert services.on("gravatar")
		with patch.object(services, "version_of", return_value="00000000.11111111"):
			frappe.local.one_services = {}
			assert not services.on("gravatar")
			assert next(one for one in services.standing() if one["key"] == "gravatar")["asks_again"]
		frappe.local.one_services = {}
		assert not gate.outstanding()["blocking"], "a new revision stops nobody"
		said = reading.trust("OneMail")
		assert said["module"]["documents"] and {"gravatar", "logos", "web_search"} <= {one["key"] for one in said["services"]}, said["services"]
		gravatar = next(use for row in said["companies"] for use in row["uses"] if use["service"] == "Pictures from Gravatar")
		assert gravatar["used"]
		assert bool(said["changes"]) == ready.PRODUCTION, said["changes"]
		assert set(said["update"]) == {"held_until"}, "One's update held for the terms is said, or nothing"
		terms = next(one for one in said["documents"] if one["key"] == "terms")
		assert terms["html"] and terms["organisation"]
	with as_user("rania@one.test"):
		try:
			services.switch("logos", 0)
			raise AssertionError("Rania turned a service off")
		except frappe.PermissionError:
			pass
	told = []
	with patch("onedesk.one.notify.notify", side_effect=lambda name, users, **said: told.append((name, said))):
		keys = [f"trust_center_told_{party}_{key}" for party in ("workspace", "user") for key in gate.keys_for(gate.WORKSPACE if party == "workspace" else gate.USER)]
		was = {key: frappe.db.get_default(key) for key in keys}
		try:
			for key in keys:
				frappe.db.set_default(key, "")
			with patch.object(gate, "_accepted", return_value="0.abc"):
				gate.told_of_changes()
				gate.told_of_changes()
		finally:
			for key, value in was.items():
				frappe.db.set_default(key, value or "")
	names = [one[0] for one in told]
	assert names.count("Agreements Changed") == 1 and names.count("Policies Changed") == int(ready.PRODUCTION), names
	assert all(one[1]["effective"] for one in told)


@check
def legal_tab_says_what_onemail_agrees_to():
	"""Nadia, with no role beyond User, reads what OneMail adds to the
	agreements: its paragraphs of the Privacy Policy and the AI Addendum and
	the companies mail passes through, each agreement at the version the
	Agreements page shows, and the version of OneMail that recorded it
	(trust_center/reading.py of_module, assemble.stamp)."""
	from onedesk.one import ready
	from onedesk.trust_center import assemble, reading

	with as_user("nadia@one.test"):
		said = reading.of_module("OneMail")
	keys = [one["key"] for one in said["documents"]]
	assert {"privacy", "ai", "subprocessors"} <= set(keys), keys
	for one in said["documents"]:
		assert one["version"] == assemble.version_of(one["key"]), one
		assert one["sections"] or one["companies"], one
	assert {"Cloudflare, Inc.", "Google LLC"} <= {row["name"] for row in said["companies"]}, said["companies"]
	assert all(use["module"] == "OneMail" for row in said["companies"] for use in row["uses"])
	assert ready.versions("OneMail")[0]["legal"] == assemble.stamp("OneMail")
	assert reading.of_module("OneNothing")["documents"] == []


@check
def who_agreed_is_a_managers():
	"""Who Agreed (trust_center/reading.py acceptances): Layla, who administers
	the workspace, reads who agreed to the Terms for the organisation and to
	the Privacy Policy for themselves, each with its version and day; Nadia,
	with no role beyond User, is told her role doesn't allow it, and
	TrustCenter offers her no button for it."""
	from onedesk.trust_center import reading

	with as_user(OWNER):
		assert reading.overview()["sees_acceptances"]
		terms = reading.acceptances("terms")
		assert terms and all(one["for"] == "organisation" and one["version"] and one["on"] for one in terms), terms
		privacy = reading.acceptances("privacy")
		assert {one["for"] for one in privacy} == {"self"} and len({one["who"] for one in privacy}) > 1, privacy
	with as_user("nadia@one.test"):
		assert not reading.overview()["sees_acceptances"]
		try:
			reading.acceptances("terms")
			raise AssertionError("Nadia read who agreed")
		except frappe.PermissionError:
			pass
