import frappe


def after_install():
	"""Set the workspace up as Rua, then bring the old app over when this
	site's config says where to read it from."""
	from rua import setup
	from rua.source import Source

	setup.run()
	if Source.configured():
		frappe.enqueue(
			"rua.importer.run",
			queue="long",
			timeout=4 * 60 * 60,
			job_id="rua-import",
			deduplicate=True,
			enqueue_after_commit=True,
		)
