"""OneAI's part of the integration suite (one_demo/check.py runs it):
AICenter as an administrator and as somebody who isn't, and web search only
while its service is on."""

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_demo.check import check
from onedesk.one_demo.people import OWNER


@check
def ai_center_sets_the_tier_and_a_modules_part():
	"""AICenter (one_ai/center.py): the tier set and put back, one of
	OneHR's switches turned and put back, OneMail's mailboxes listed, one of
	reading's settings changed and put back, and reading and OneAI turned off
	and on; somebody who doesn't administer the workspace
	is refused all of it and sees only what OneAI keeps about them."""
	from unittest import mock

	from onedesk.one import apps
	from onedesk.one_ai import center

	with as_user("nadia@one.test"):
		assert "facts" in center.yours()
		for refused in (center.state, center.parts, lambda: center.set_tier("full")):
			try:
				refused()
			except frappe.PermissionError:
				continue
			raise AssertionError("somebody who doesn't administer the workspace reached AICenter's workspace parts")
	with as_user("wsadmin@one.test"), mock.patch("onedesk.one.account.ask", return_value=[]):
		was = center.tier()
		try:
			assert center.set_tier("full" if was != "full" else "fast") == center.state()["tier"] != was
		finally:
			center.set_tier(was)
		parts = {one["module"]: one for one in center.parts()}
		assert {"OneHR", "OneMail"} <= set(parts) and parts["OneMail"]["mailboxes"], parts
		job = next(one for one in parts["OneHR"]["jobs"] if one["kind"] == "switch")
		try:
			assert center.set_job(job["key"], 0 if job["value"] else 1)["value"] != job["value"]
		finally:
			center.set_job(job["key"], job["value"])
		try:
			center.set_on(0)
			assert not apps.ai_on() and center.modules()
		finally:
			center.set_on(1)
		assert apps.ai_on()
		read = center.reading()
		assert read["on"] and {one["key"] for one in read["settings"]} >= {"floor", "quiet_minutes", "audit"}, read
		quiet = next(one["value"] for one in read["settings"] if one["key"] == "quiet_minutes")
		try:
			center.set_reading("quiet_minutes", 9)
			assert frappe.db.get_single_value("Reading Settings", "quiet_minutes") == 9
		finally:
			center.set_reading("quiet_minutes", quiet or 0)
		try:
			center.set_reading_on(0)
			assert apps.ai_on() and not apps.intake_on()
		finally:
			center.set_reading_on(1)
		assert apps.intake_on()
		assert center.summaries() and isinstance(center.knowledge(), list)
		used = center.usage()
		assert used["reached"] or not used["jobs"], used


@check
def oneai_searches_the_web_only_while_its_service_is_on():
	"""Web search (one_ai/ai_web.py): off, OneAI isn't given the tool or its
	group, and asking it reaches nobody; on, the question alone goes to the
	account, and the pages come back."""
	from unittest import mock

	from onedesk.one_ai import ai_web, groups, tools
	from onedesk.trust_center import services

	with as_user(OWNER):
		was = services.on(ai_web.SERVICE)
		try:
			services.switch(ai_web.SERVICE, 0)
			frappe.local.one_services = {}
			assert "web_search" not in tools.names() and "web" not in groups.chosen("look up Gulf Extrusions online")
			with mock.patch("onedesk.one.account.ask") as asked:
				assert ai_web.web_search("Gulf Extrusions Dubai")["pages"] == []
				asked.assert_not_called()
			services.switch(ai_web.SERVICE, 1)
			frappe.local.one_services = {}
			assert "web_search" in tools.names() and "web" in groups.chosen("look up Gulf Extrusions online")
			page = {"url": "https://gulf.example", "title": "Gulf Extrusions", "about": "Aluminium profiles"}
			with mock.patch("onedesk.one.account.ask", return_value={"pages": [page]}) as asked:
				assert ai_web.web_search("Gulf Extrusions Dubai") == {"pages": [page]}
				assert asked.call_args.kwargs == {"query": "Gulf Extrusions Dubai", "most": ai_web.MOST}, asked.call_args
		finally:
			services.switch(ai_web.SERVICE, int(was))
			frappe.local.one_services = {}


@check
def a_oneai_manager_writes_knowledge():
	"""Knowledge (one_ai/center.py keep_knowledge): Nadia, with no role
	beyond User, is refused; given OneAI Manager she writes a piece, changes
	it and removes it in AICenter, though the record type's own form is an
	administrator's; OneAI may do none of it (agent.py NOT_FOR_AI)."""
	from onedesk.one_ai import agent, center

	with as_user("nadia@one.test"):
		assert not center.may()["knowledge"]
		try:
			center.keep_knowledge("Refused", "Nobody reads this.")
			raise AssertionError("Nadia wrote Knowledge")
		except frappe.PermissionError:
			pass
	user = frappe.get_doc("User", "nadia@one.test")
	user.add_roles("OneAI Manager")
	try:
		with as_user("nadia@one.test"):
			assert center.may()["knowledge"], "OneAI Manager holds Knowledge, given once by the update that brought it"
			assert not frappe.has_permission("AI Knowledge", "create"), "the record type's own form stays an administrator's"
			name = center.keep_knowledge("Site visits", "<p>Site visits are booked two days ahead.</p>", enabled=1)
			assert center.knowledge_of(name)["title"] == "Site visits"
			center.keep_knowledge("Site visits", "<p>Three days ahead.</p>", enabled=0, name=name)
			assert {"name": name, "enabled": 0} in [{"name": one["name"], "enabled": one["enabled"]} for one in center.knowledge()]
			center.drop_knowledge(name)
			assert not frappe.db.exists("AI Knowledge", name)
	finally:
		user.remove_roles("OneAI Manager")
	assert "center.keep_knowledge" in agent.NOT_FOR_AI and "center.drop_knowledge" in agent.NOT_FOR_AI
