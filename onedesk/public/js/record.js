// A record shown on a page of its own instead of its form (one/tiers.py
// PAGES) keeps what the form gives it: frappe's ··· menu (Print, Email,
// Duplicate, Rename, Delete, Remind Me, Follow…) and its sidebar (assigned,
// tags, shared, likes, who is viewing, who made and last changed it). Each is
// frappe's own dialog or frappe's own call. The sidebar is frappe's own form
// sidebar, on the page's right as on a form (`onedesk.record.sidebar`).
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

// frappe's Email dialog on a record shown on a page: New Email, or Reply and
// Reply All on one of its emails, with the arguments the form timeline's
// compose_mail gives it (frappe/form/footer/form_timeline.js), so the
// recipients, copies, subject and quoted mail are what a form would give.
// `email` is the email as `getdoc` and the timeline keep it: name, sender,
// recipients, cc, bcc, subject, content, communication_date.
onedesk.record.email = async (doctype, name, { email = null, all = false, sent = () => {} } = {}) => {
	const record = await onedesk.record.read(doctype, name);
	const frm = onedesk.record.handle(doctype, record, sent);
	const { doc } = record;
	const me = frappe.session.user_email;
	const args = {
		doc,
		frm,
		recipients: email && email.sender != me ? email.sender : doc.email_id || doc.email || "",
		is_a_reply: Boolean(email),
		title: email ? __("Reply") : null,
		last_email: email,
		subject: email && email.subject,
		reply_all: all,
		sender: email && email.sender,
		message: "",
	};
	if (email) {
		const outgoing = (frappe.boot.email_accounts || [])
			.filter((one) => !["All Accounts", "Sent", "Spam", "Trash"].includes(one.email_account) && one.enable_outgoing)
			.map((one) => one.email_id);
		args.cc = "";
		if (outgoing.includes(me) && email.sender != me)
			args.cc = `${(email.recipients || "").split(",").map((one) => one.trim()).filter((one) => one && one != me).join(", ")}, `;
		if (all) {
			args.cc += cstr(email.cc);
			args.bcc = cstr(email.bcc);
		}
	}
	return new frappe.views.CommunicationComposer(args);
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

// frappe's own form sidebar, on the right of a page that shows one record
// (onedesk.island_page's `record`), and frappe's "Currently Viewing" avatars
// in the page head, both as a form draws them. frappe.ui.form.Sidebar and its
// parts (Assign, Attachments, Tags, Share, likes, who made and last changed
// it) read a form; `handle` is the part of one they read, and the docinfo
// they change is frappe's own (frappe.model.docinfo), kept current by the
// record's realtime room. Its Attachments are the record's Files, one row
// that opens them (`files`), as on a form (record_files.js). Returns the way
// to stop.
// A record type's changes to its sidebar, each given the sidebar's form.
onedesk.record.sidebar_parts = {};

onedesk.record.sidebar = (page, doctype, name, { files = null } = {}) => {
	// The page's own Files view, or else OneCloud on the record's room.
	const open_files = files || (() => frappe.set_route("onecloud", { node: `@records/${doctype}/${name}` }));
	const files_row = () => {
		const $side = onedesk.record_files.side(frm, open_files);
		onedesk.record_files.badge($side, (frm.get_docinfo().attachments || []).length);
	};
	let frm = null;
	let gone = false;
	// What a record type changes in its sidebar, as a form's own script would.
	const dress = () => (onedesk.record.sidebar_parts[doctype] || []).forEach((part) => part(frm));
	const draw = async () => {
		const record = await onedesk.record.read(doctype, name);
		if (gone || !record.doc.name) return;
		(frappe.model.docinfo[doctype] ||= {})[name] = record.docinfo;
		if (frm) {
			frm.doc = record.doc;
			frm.sidebar.refresh();
			files_row();
			dress();
			return;
		}
		frm = {
			...onedesk.record.handle(doctype, record, draw),
			page,
			wrapper: page.wrapper,
			// Each field as the parts look it up, read-only: the page is not
			// the form, so its image is changed on the form.
			fields_dict: Object.fromEntries(frappe.get_meta(doctype).fields.map((df) => [df.fieldname, { df: { ...df, read_only: 1 } }])),
			get_docinfo: () => frappe.model.get_docinfo(doctype, name) || {},
			get_title: () => frappe.model.get_doc_title(frm.doc),
			get_field: () => null,
			get_docfield: () => null,
			has_perm: (ptype) => frappe.perm.has_perm(doctype, 0, ptype, frm.doc),
			set_value: (field, value) => frappe.db.set_value(doctype, name, field, value).then(draw),
			refresh_field: () => {},
			share_doc: () => frm.shared.show(),
			print_doc: () => frappe.set_route("print", doctype, name),
		};
		delete frm.attachments;
		delete frm.shared;
		frm.sidebar = new frappe.ui.form.Sidebar({ frm, page, toolbar: { setup_editable_title: () => {} } });
		frm.sidebar.make();
		files_row();
		dress();
		// What the parts reload after a change, read again with the record.
		frm.sidebar.reload_docinfo = (done) => draw().then(() => done && done(frm.get_docinfo()));
		frm.viewers = new frappe.ui.form.FormViewers({
			frm,
			parent: $('<div class="form-viewers d-flex"></div>').prependTo(page.page_actions),
		});
	};
	// Who else has it open, and any change to it or its sidebar, as a form
	// hears them.
	const stop = [onedesk.record.changes(doctype, name, draw)];
	frappe.realtime.doc_subscribe(doctype, name);
	frappe.realtime.doc_open(doctype, name);
	const saved = (data) => data.doctype === doctype && data.name === name && draw();
	frappe.realtime.on("doc_update", saved);
	draw();
	return () => {
		gone = true;
		stop.forEach((one) => one());
		frappe.realtime.off("doc_update", saved);
		frappe.realtime.doc_close(doctype, name);
		frappe.realtime.doc_unsubscribe(doctype, name);
		page.page_actions.find(".form-viewers").remove();
		page.sidebar.empty();
	};
};
