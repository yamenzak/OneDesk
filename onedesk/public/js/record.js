frappe.provide("onedesk.record");

onedesk.record.held = new Set();

onedesk.record.read = async (doctype, name) => {
	await frappe.model.with_doctype(doctype);
	const r = await frappe.call({ method: "frappe.desk.form.load.getdoc", type: "GET", args: { doctype, name } });
	const doc = (r.docs || [])[0] || {};
	const docinfo = r.docinfo || {};
	if (!onedesk.record.held.has(`${doctype}/${name}`)) frappe.model.remove_from_locals(doctype, name);
	return { doc, docinfo };
};

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

onedesk.record.share = (doctype, record, done) =>
	new frappe.ui.form.Share({ frm: onedesk.record.handle(doctype, record, done), parent: $("<div>") }).show();

onedesk.record.tag = (doctype, name, tag) => frappe.xcall("frappe.desk.doctype.tag.tag.add_tag", { tag, dt: doctype, dn: name });
onedesk.record.untag = (doctype, name, tag) => frappe.xcall("frappe.desk.doctype.tag.tag.remove_tag", { tag, dt: doctype, dn: name });
onedesk.record.tags = (doctype, txt) => frappe.xcall("frappe.desk.doctype.tag.tag.get_tags", { doctype, txt: (txt || "").toLowerCase() });

onedesk.record.like = (doctype, name, liked) => frappe.xcall("frappe.desk.like.toggle_like", { doctype, name, add: liked ? "Yes" : "No" });

onedesk.record.follow = (doctype, name, on) =>
	frappe.xcall(`frappe.desk.form.document_follow.${on ? "follow_document" : "unfollow_document"}`, { doctype, doc_name: name });

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

onedesk.record.changes = (doctype, name, heard) => {
	const seen = ({ doc }) => doc && doc.reference_doctype === doctype && String(doc.reference_name) === String(name) && heard();
	frappe.realtime.on("docinfo_update", seen);
	return () => frappe.realtime.off("docinfo_update", seen);
};

onedesk.record.email = async (
	doctype,
	name,
	{ email = null, all = false, sent = () => {}, recipients = null, subject = null, message = "" } = {}
) => {
	const record = await onedesk.record.read(doctype, name);
	const frm = onedesk.record.handle(doctype, record, sent);
	const { doc } = record;
	const me = frappe.session.user_email;
	const args = {
		doc,
		frm,
		recipients: recipients || (email && email.sender != me ? email.sender : doc.email_id || doc.email || doc.contact_email || ""),
		is_a_reply: Boolean(email),
		title: email ? __("Reply") : null,
		last_email: email,
		subject: subject || (email && email.subject),
		reply_all: all,
		sender: email && email.sender,
		message: message || "",
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
			if (!onedesk.record.held.has(`${doctype}/${name}`)) frappe.model.remove_from_locals(doctype, name);
			frappe.set_route("Form", doctype, copy.name);
		});
	if (meta.allow_rename && perm.write) add(__("Rename"), () => frappe.model.rename_doc(doctype, name, changed));
	add(__("Reload"), changed);
	if (doc.docstatus != 1 && frappe.model.can_delete(doctype)) add(__("Delete"), () => frappe.model.delete_doc(doctype, name, gone));
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

{
	const Sidebar = frappe.ui.form?.Sidebar;
	if (Sidebar && !Sidebar.prototype.__one_repeats) {
		Sidebar.prototype.__one_repeats = true;
		const shown = Sidebar.prototype.show_auto_repeat_status;
		Sidebar.prototype.show_auto_repeat_status = function (...args) {
			this.sidebar?.find(".auto-repeat-status:not(:has(span))").append("<span></span>");
			return shown.apply(this, args);
		};
	}
}

onedesk.record.sidebar_parts = {};

onedesk.record.sidebar = (page, doctype, name, { files = null } = {}) => {
	const open_files = files || (() => frappe.set_route("onecloud", { node: `@records/${doctype}/${name}` }));
	const files_row = () => {
		const $side = onedesk.record_files.side(frm, open_files);
		onedesk.record_files.badge($side, (frm.get_docinfo().attachments || []).length);
	};
	let frm = null;
	let gone = false;
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
			fields_dict: Object.fromEntries(frappe.get_meta(doctype).fields.map((df) => [df.fieldname, { df: { ...df, read_only: 1 } }])),
			get_docinfo: () => frappe.model.get_docinfo(doctype, name) || {},
			get_title: () => frappe.model.get_doc_title(frm.doc),
			get_field: () => null,
			get_docfield: () => null,
			has_perm: (ptype) => frappe.perm.has_perm(doctype, 0, ptype, frm.doc),
			get_perm: (permlevel, ptype) => frappe.perm.has_perm(doctype, permlevel, ptype, frm.doc),
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
		frm.sidebar.reload_docinfo = (done) => draw().then(() => done && done(frm.get_docinfo()));
		frm.viewers = new frappe.ui.form.FormViewers({
			frm,
			parent: $('<div class="form-viewers d-flex"></div>').prependTo(page.page_actions),
		});
	};
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

onedesk.record.form = (doctype, name, changed = () => {}, edited = () => {}) =>
	new Promise((done) => {
		frappe.model.with_doctype(doctype, () => {
			const cached = locals[doctype] && locals[doctype][name];
			if (cached && !cached.__onload) frappe.model.remove_from_locals(doctype, name);
			frappe.model.with_doc(doctype, name, (got, r) => {
				if (r && r["403"]) return done(null);
				const key = `${doctype}/${name}`;
				onedesk.record.held.add(key);
				const $host = $('<div class="one-record-form" hidden></div>').appendTo(document.body);
				const frm = new frappe.ui.form.Form(doctype, $host.get(0), false);
				frm.in_dialog = true;
				const set_active_tab = frm.set_active_tab.bind(frm);
				frm.set_active_tab = (tab) => {
					const was = window.location.href;
					set_active_tab(tab);
					if (window.location.href !== was) history.replaceState(history.state, "", was);
				};
				const heard = (refreshed) => refreshed === frm && changed(frm);
				const refresh_field = frm.refresh_field.bind(frm);
				let soon = null;
				frm.refresh_field = (...args) => {
					const out = refresh_field(...args);
					clearTimeout(soon);
					soon = setTimeout(() => changed(frm), 0);
					return out;
				};
				frappe.ui.form.on(doctype, "refresh", heard);
				const typed = (fieldname, value, doc) => doc && doc.name === frm.docname && edited(fieldname);
				frappe.model.on(doctype, "*", typed);
				const rows = frappe.meta
					.get_table_fields(doctype)
					.map((df) => df.options)
					.filter((one, i, all) => all.indexOf(one) === i);
				const row_typed = (fieldname, value, doc) =>
					doc && doc.parent === frm.docname && doc.parenttype === doctype && edited(fieldname, doc.name);
				rows.forEach((child) => frappe.model.on(child, "*", row_typed));
				frm.refresh(name);
				changed(frm);
				done({
					frm,
					stop() {
						const handlers = (frappe.ui.form.handlers[doctype] || {}).refresh || [];
						const at = handlers.indexOf(heard);
						if (at >= 0) handlers.splice(at, 1);
						const off = (dt, heard) => {
							const any = frappe.model.events[dt]?.["*"] || [];
							if (any.includes(heard)) any.splice(any.indexOf(heard), 1);
						};
						off(doctype, typed);
						rows.forEach((child) => off(child, row_typed));
						removeEventListener("beforeunload", frm.beforeUnloadListener, { capture: true });
						if (window.cur_frm === frm) window.cur_frm = null;
						onedesk.record.held.delete(key);
						$host.remove();
					},
				});
			});
		});
	});

onedesk.record.lend = (frm, fieldname, spot, hooks = {}) => {
	const control = frm.fields_dict[fieldname];
	const $home = $('<span hidden class="one-field-home"></span>').insertBefore(control.$wrapper);
	return onedesk.record.float(control, spot, hooks, () => {
		control.$wrapper.insertAfter($home);
		$home.remove();
	});
};

onedesk.record.lend_row = (frm, table, row, fieldname, spot, hooks = {}) => {
	const doc = onedesk.record.row(frm, table, row);
	const control = frappe.ui.form.make_control({
		df: onedesk.record.row_df(frm, table, row, fieldname),
		parent: $("<div></div>"),
		doc,
		doctype: doc.doctype,
		docname: doc.name,
		frm,
		value: doc[fieldname],
		render_input: true,
	});
	control.get_query = frm.fields_dict[table].grid.get_field(fieldname).get_query;
	return onedesk.record.float(control, spot, hooks, () => control.$wrapper.remove());
};

onedesk.record.row = (frm, table, row) => (frm.doc[table] || []).find((one) => one.name === row) || null;

onedesk.record.row_df = (frm, table, row, fieldname) => {
	const doc = onedesk.record.row(frm, table, row);
	return doc ? frappe.meta.get_docfield(doc.doctype, fieldname, frm.docname) : null;
};

onedesk.record.row_status = (frm, table, row, fieldname) => {
	const doc = onedesk.record.row(frm, table, row);
	const status = frm.fields_dict[table]?.get_status();
	if (!doc || !status || status === "None") return doc ? "None" : null;
	const df = onedesk.record.row_df(frm, table, row, fieldname);
	if (!df) return "None";
	const own = frappe.perm.get_field_display_status(df, doc, frm.perm);
	return status === "Read" && own === "Write" ? "Read" : own;
};

onedesk.record.set_row = (frm, table, row, fieldname, value) => {
	const doc = onedesk.record.row(frm, table, row);
	return doc ? frappe.model.set_value(doc.doctype, doc.name, fieldname, value) : null;
};

onedesk.record.add_row = (frm, table, values = {}) => {
	const doc = frappe.model.add_child(frm.doc, frm.fields_dict[table].df.options, table);
	Object.assign(doc, values);
	frm.dirty();
	frm.refresh_field(table);
	return doc.name;
};

onedesk.record.float = (control, spot, { keys = () => {}, left = () => {} } = {}, back = () => {}) => {
	const $float = $('<div class="one-field-float"></div>').appendTo(document.body).append(control.$wrapper);
	const place = () => {
		const r = spot.getBoundingClientRect();
		$float.css({ top: r.top, left: r.left, width: Math.max(r.width, 192) });
		spot.style.height = `${$float.outerHeight()}px`;
	};
	place();
	control.refresh();
	place();
	window.addEventListener("scroll", place, true);
	window.addEventListener("resize", place);
	$float.on("keydown", keys);
	$float.on("focusout", () =>
		setTimeout(() => {
			if ($float[0].contains(document.activeElement)) return;
			if (document.querySelector(".datepicker.active, .awesomplete > ul:not([hidden]):not(:empty)")) return;
			left();
		}, 200)
	);
	return {
		control,
		place,
		give_back() {
			window.removeEventListener("scroll", place, true);
			window.removeEventListener("resize", place);
			back();
			$float.remove();
			spot.style.height = "";
		},
	};
};
