"""A Display Channel is only what is seen now (D6): each channel's music,
voice ads, voice and calls move into a Sound Zone of its own, named after
it, which the channel's screens play, and each queue whose board a calling
channel showed says its calls in that zone. Nothing sounds different."""

import frappe
from frappe.utils import cint


def execute():
	if not frappe.db.has_column("Display Channel", "music_playlist"):
		return
	channels = frappe.db.sql(
		"select name, channel_name, music_playlist, announce, voice, voice_language, widget_collection from `tabDisplay Channel`",
		as_dict=True,
	)
	for row in channels:
		ads = frappe.get_all("Channel Ad", filters={"parent": row.name, "parenttype": "Display Channel"}, pluck="name")
		music = frappe.get_all("Channel Programme", filters={"parent": row.name, "parenttype": "Display Channel", "plays": "Music"}, pluck="name")
		if not (row.music_playlist or ads or music or cint(row.announce)):
			continue
		zone = frappe.get_doc(
			{
				"doctype": "Sound Zone",
				"zone_name": _free(row.channel_name or row.name),
				"music_playlist": row.music_playlist,
				"announce": cint(row.announce),
				"voice": row.voice,
				"voice_language": row.voice_language,
			}
		).insert(ignore_permissions=True)
		for name in ads:
			frappe.db.set_value("Channel Ad", name, {"parent": zone.name, "parenttype": "Sound Zone"}, update_modified=False)
		for name in music:
			frappe.db.set_value("Channel Programme", name, {"parent": zone.name, "parenttype": "Sound Zone"}, update_modified=False)
		for screen in frappe.get_all("Display Screen", filters={"channel": row.name}, pluck="name"):
			frappe.db.set_value("Display Screen", screen, {"sound_zone": zone.name, "plays_sound": 1}, update_modified=False)
		if cint(row.announce):
			for queue in _queues_shown(row):
				if not frappe.db.get_value("Queue", queue, "sound_zone"):
					frappe.db.set_value("Queue", queue, "sound_zone", zone.name, update_modified=False)
		frappe.clear_document_cache("Display Channel", row.name)
		frappe.clear_document_cache("Sound Zone", zone.name)


def _free(name: str) -> str:
	taken, n, said = frappe.db.exists, 2, name
	while taken("Sound Zone", said):
		said, n = f"{name} {n}", n + 1
	return said


def _queues_shown(channel) -> set:
	"""The queues a channel's widgets read, in its own collection and any its schedule shows."""
	collections = {channel.widget_collection} | set(
		frappe.get_all("Channel Programme", filters={"parent": channel.name, "parenttype": "Display Channel", "plays": "Widgets"}, pluck="widget_collection")
	)
	sources = frappe.get_all("Display Widget", filters={"parent": ["in", [one for one in collections if one] or [""]], "parenttype": "Widget Collection"}, pluck="source")
	return set(frappe.get_all("Display Source", filters={"name": ["in", [one for one in sources if one] or [""]], "kind": "Queue"}, pluck="queue"))
