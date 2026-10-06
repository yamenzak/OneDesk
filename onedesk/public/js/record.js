// A record shown on a page of its own instead of its form (one/tiers.py
// PAGES) keeps what the form gives it: frappe's ··· menu (Print, Email,
// Duplicate, Rename, Delete, Remind Me, Follow…) and its sidebar (assigned,
// tags, shared, likes, who is viewing, who made and last changed it). Each is
// frappe's own dialog or frappe's own call. Nothing here draws a record; the
// page draws the sidebar in its own look (frontend/src/kit/Record.vue).
//
// frappe's dialogs are written against a form. `handle` is the part of one
// they read, built from the record as `getdoc` sends it, and
// tests/guards/test_frame.py checks it still covers what they read.
frappe.provide("onedesk.record");

// The record and its docinfo, read fresh, without leaving a copy in locals
// that a form opened next would take for the saved record.
onedesk.record.read = async (doctype, name) => {
	const r = await frappe.call({ method: "frappe.desk.form.load.getdoc", type: "GET", args: { doctype, name } });
	const doc = (r.docs || [])[0] || {};
	const docinfo = r.docinfo || {};
	frappe.model.remove_from_locals(doctype, name);
	return { doc, docinfo };
};

// What a form would be to frappe's Share, Email, Remind Me and Links dialogs.
onedesk.record.handle = (doctype, { doc, docinfo }, changed = () => {}) => {
	const perm = frappe.perm.get_perm(doctype, doc);
	return {
		doctype,
		docname: doc.name,
		doc,
		meta: frappe.get_meta(doctype),
		perm,
		events: {},
		wrapper: null,
		email_field: null,
		__linked_docs: null,
		get_docinfo: () => docinfo,
		get_files: () => docinfo.attachments || [],
		is_new: () => false,
		is_dirty: () => false,
		reload_doc: changed,
		timeline: { get_recipient: () => "", get_last_email: () => null, refresh: changed },
		attachments: { attachment_uploaded: changed, refresh: changed },
		shared: { refresh: changed },
		sidebar: { reload_docinfo: changed },
	};
};

// The sidebar's facts, as the page draws them.
onedesk.record.said = ({ doc, docinfo }) => {
	const shared = docinfo.shared || [];
	return {
		assigned: (docinfo.assignments || []).map((one) => one.owner),
		tags: (docinfo.tags || doc._user_tags || "").split(",").map((tag) => tag.trim()).filter(Boolean),
		shared: shared.filter((one) => one.user && !one.everyone).map((one) => one.user),
		everyone: shared.some((one) => one.everyone),
		liked_by: frappe.ui.get_liked_by(doc),
		following: !!docinfo.is_document_followed,
		owner: doc.owner,
		creation: doc.creation,
		modified_by: doc.modified_by,
		modified: doc.modified,
	};
};

// What the reader may do from the sidebar.
onedesk.record.can = (doctype, { doc }) => {
	const perm = frappe.perm.get_perm(doctype, doc);
	return {
		assign: !!perm[0]?.write,
		tag: !!perm[0]?.write,
		share: frappe.model.can_share(null, { perm }),
		like: true,
	};
};

onedesk.record.assign = (doctype, name, done) =>
	new frappe.ui.form.AssignToDialog({
		method: "frappe.desk.form.assign_to.add",
		doctype,
		docname: name,
		callback: done,
	}).dialog.show();

onedesk.record.unassign = (doctype, name, user) =>
	frappe.xcall("frappe.desk.form.assign_to.remove", { doctype, name, assign_to: user });

// frappe's Share draws its sidebar part into `parent` as well; the page
// draws its own, so that part goes nowhere.
onedesk.record.share = (doctype, record, done) =>
	new frappe.ui.form.Share({ frm: onedesk.record.handle(doctype, record, done), parent: $("<div>") }).show();

onedesk.record.tag = (doctype, name, tag) => frappe.xcall("frappe.desk.doctype.tag.tag.add_tag", { tag, dt: doctype, dn: name });
onedesk.record.untag = (doctype, name, tag) => frappe.xcall("frappe.desk.doctype.tag.tag.remove_tag", { tag, dt: doctype, dn: name });
onedesk.record.tags = (doctype, txt) => frappe.xcall("frappe.desk.doctype.tag.tag.get_tags", { doctype, txt: (txt || "").toLowerCase() });

onedesk.record.like = (doctype, name, liked) => frappe.xcall("frappe.desk.like.toggle_like", { doctype, name, add: liked ? "Yes" : "No" });

onedesk.record.follow = (doctype, name, on) =>
	frappe.xcall(`frappe.desk.form.document_follow.${on ? "follow_document" : "unfollow_document"}`, { doctype, doc_name: name });

// Who else has the record open, as a form hears it: `heard(users)` with the
// reader left out. Returns the way to stop.
onedesk.record.viewers = (doctype, name, heard) => {
	const seen = ({ doctype: dt, docname, users = [] }) =>
		dt === doctype && docname === name && heard(users.filter((user) => user !== frappe.session.user));
	frappe.realtime.on("doc_viewers", seen);
	frappe.realtime.doc_open(doctype, name);
	return () => {
		frappe.realtime.off("doc_viewers", seen);
		frappe.realtime.doc_close(doctype, name);
	};
};

// A change to the record's sidebar made anywhere, as a form hears it.
onedesk.record.changes = (doctype, name, heard) => {
	const seen = ({ doc }) => doc && doc.reference_doctype === doctype && String(doc.reference_name) === String(name) && heard();
	frappe.realtime.on("docinfo_update", seen);
	return () => frappe.realtime.off("docinfo_update", seen);
};

// frappe's own menu items for a record, in frappe's words and order, each
// only where the form would offer it (frappe/form/toolbar.js). `standard`
// puts them below the page's own, as the form's are.
onedesk.record.menu = (doctype, record, { changed = () => {}, gone = () => {} } = {}) => {
	const { doc } = record;
	const name = doc.name;
	const meta = frappe.get_meta(doctype);
	const perm = frappe.perm.get_perm(doctype, doc)[0] || {};
	const frm = () => onedesk.record.handle(doctype, record, changed);
	const items = [];
	const add = (label, onClick) => items.push({ label, onClick, standard: true });

	if (perm.print && frappe.model.can_print_docstatus(doctype, doc.docstatus) && !meta.issingle)
		add(__("Print"), () => frappe.set_route("print", doctype, name));
	if (perm.email && doc.docstatus < 2)
		add(__("Email"), () => new frappe.views.CommunicationComposer({ doc, frm: frm(), subject: `${__(doctype)}: ${name}`, attach_document_print: true }));
	add(__("Show Links"), () => new frappe.ui.form.LinkedWith({ frm: frm() }).show());
	if (frappe.boot.user.can_create.includes(doctype) && !meta.allow_copy)
		add(__("Duplicate"), async () => {
			const copy = frappe.model.copy_doc(await frappe.model.with_doc(doctype, name));
			frappe.model.remove_from_locals(doctype, name);
			frappe.set_route("Form", doctype, copy.name);
		});
	if (meta.allow_rename && perm.write) add(__("Rename"), () => frappe.model.rename_doc(doctype, name, changed));
	add(__("Reload"), changed);
	if (doc.docstatus != 1 && frappe.model.can_delete(doctype)) add(__("Delete"), () => frappe.model.delete_doc(doctype, name, gone));
	// frappe keeps its Remind Me dialog inside the form's toolbar, where its
	// own menu item opens it; that item is asked to open it here.
	add(__("Remind Me"), () => frappe.ui.form.Toolbar.prototype.add_remind_me.call({ frm: frm(), page: { add_menu_item: (_label, open) => open() } }));
	if (meta.track_changes && frappe.boot.user.document_follow_notify) {
		const following = !!record.docinfo.is_document_followed;
		add(following ? __("Unfollow") : __("Follow"), () => onedesk.record.follow(doctype, name, !following).then(changed));
	}
	add(__("Copy to Clipboard"), () => frappe.utils.copy_to_clipboard(JSON.stringify(doc)));
	if (perm.create && !meta.issingle && !meta.in_create) add(__("New {0}", [__(doctype)]), () => frappe.new_doc(doctype, true));
	if (frappe.model.can_create("Custom Field") && frappe.model.can_create("Property Setter") && !frappe.model.core_doctypes_list.includes(doctype))
		add(__("Customize"), () => frappe.set_route("Form", "Customize Form", { doc_type: doctype }));
	return items;
};
