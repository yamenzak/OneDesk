// Mail templates (Email Template), edited from OneMail's settings and from a
// record type's Customize page (doctype_settings.js): their fields, `/` for
// a record's fields, Preview, Save and Delete (one_mail/mail_templates.py).
frappe.provide("onedesk.mail_templates");

onedesk.mail_templates.API = "onedesk.one_mail.mail_templates.";

// A template's fields, shared by the dialog below (a record type's Customize
// page) and OneMail's settings, which opens one in place. A template with code
// in it, as the apps' own are written, is edited as code: the text editor
// would show its tags as words and break them.
onedesk.mail_templates.CODE = /\{%|\{\{(?!-?\s*[A-Za-z][A-Za-z0-9_]*\s*-?\}\})/;

onedesk.mail_templates.fields = (name, doc) => {
	const code = !!doc && !doc.use_html && onedesk.mail_templates.CODE.test(`${doc.subject || ""}${doc.response || ""}`);
	return [
		{ fieldtype: "Data", fieldname: "template_name", label: __("Name"), reqd: name ? 0 : 1, hidden: name ? 1 : 0 },
		{ fieldtype: "Data", fieldname: "subject", label: __("Subject"), reqd: 1 },
		{
			fieldtype: "Link",
			fieldname: "reference_doctype",
			label: __("For"),
			options: "DocType",
			get_query: () => ({ query: "onedesk.one.rules.watchable" }),
			description: __("Leave empty to use it for any record type."),
		},
		{ fieldtype: "Check", fieldname: "use_html", label: __("Write in HTML"), hidden: code ? 1 : 0 },
		code
			? {
					fieldtype: "Code",
					fieldname: "response",
					label: __("Message"),
					options: "HTML",
					description: __("Parts in {{ }} and {% %} are filled in when it is sent."),
			  }
			: { fieldtype: "Text Editor", fieldname: "response", label: __("Message"), depends_on: "eval:!doc.use_html" },
		{ fieldtype: "Code", fieldname: "response_html", label: __("Message"), options: "HTML", depends_on: "eval:doc.use_html" },
		{
			fieldtype: "HTML",
			fieldname: "help",
			options: `<p class="text-muted small">${__("Type / to insert a field of the record.")}</p>`,
		},
	];
};

// Typing `/` in the subject or the message opens the record's fields at the
// cursor: typing narrows them, the arrows and Enter pick, Escape closes. A
// table asks which columns, then writes one line, {{ table(items, "item_name",
// "qty") }}, which is mailed as a table (mail_templates.fields_of, check,
// _table). The same in the text editor, the HTML editor and the subject.
onedesk.mail_templates.slash = (form) => {
	const API = onedesk.mail_templates.API;
	const esc = frappe.utils.escape_html;
	const TRIGGER = /(^|\s)\/(\w*)$/;
	let said = null;
	let loaded = null;
	const load = async () => {
		const doctype = form.get_value("reference_doctype");
		if (loaded === doctype) return;
		loaded = doctype;
		said = doctype ? await frappe.xcall(API + "fields_of", { doctype }) : null;
	};
	const $pop = $(`<div class="one-slash hide" role="listbox"></div>`).appendTo(document.body);
	let open = null;
	const close = () => {
		open = null;
		$pop.addClass("hide").empty();
	};
	// Those whose name starts with what was typed first, then those holding it;
	// fields before tables, each in the record's own order. A table is marked.
	const choices = (query) => {
		const q = query.toLowerCase();
		const score = (one) => {
			const label = one.label.toLowerCase().replace(/\s+/g, "");
			if (!q || label.startsWith(q) || one.fieldname.startsWith(q)) return 0;
			return label.includes(q) || one.fieldname.includes(q) ? 1 : 2;
		};
		const all = [
			...(said?.fields || []).map((one) => ({ ...one, kind: "field" })),
			...(said?.tables || []).map((one) => ({ ...one, kind: "table" })),
		].map((one, i) => ({ one, i, score: score(one) }));
		const kept = all.filter((x) => x.score < 2).sort((a, b) => a.score - b.score || a.i - b.i);
		const best = kept.filter((x) => x.score === kept[0]?.score).map((x) => x.one);
		const rest = kept.filter((x) => x.score !== kept[0]?.score).map((x) => x.one);
		const order = (list) => [...list.filter((x) => x.kind === "field"), ...list.filter((x) => x.kind === "table")];
		return [...order(best), ...order(rest)].slice(0, 40);
	};
	const place = (at) => $pop.css({ left: Math.min(at.left, window.innerWidth - 300), top: at.top });
	const draw = () => {
		$pop.removeClass("hide").empty();
		if (open.table) {
			const table = open.table;
			$(`<div class="one-slash-head"></div>`).text(__("Columns of {0}", [table.label])).appendTo($pop);
			const $list = $(`<div class="one-slash-list"></div>`).appendTo($pop);
			// The ticked first, as they were offered, so they are seen.
			const first = open.offered || (open.offered = [
				...table.fields.filter((f) => open.columns.includes(f.fieldname)),
				...table.fields.filter((f) => !open.columns.includes(f.fieldname)),
			]);
			for (const one of first) {
				const $row = $(`<label class="one-slash-check"><input type="checkbox"><span></span></label>`).appendTo($list);
				$row.find("span").text(one.label);
				$row.find("input").prop("checked", open.columns.includes(one.fieldname)).on("change", (e) => {
					open.columns = e.target.checked
						? table.fields.map((f) => f.fieldname).filter((f) => f === one.fieldname || open.columns.includes(f))
						: open.columns.filter((f) => f !== one.fieldname);
				});
			}
			$(frappe.ui.button.html({ label: __("Insert Table"), variant: "solid", size: "sm" }))
				.addClass("one-slash-go")
				.on("mousedown", (e) => e.preventDefault())
				.on("click", () => pick())
				.appendTo($pop);
			return;
		}
		if (!form.get_value("reference_doctype")) {
			$(`<div class="one-slash-empty"></div>`).text(__("Choose For to insert its fields.")).appendTo($pop);
			return;
		}
		if (!open.items.length) {
			$(`<div class="one-slash-empty"></div>`).text(__("No matching fields")).appendTo($pop);
			return;
		}
		open.items.forEach((one, i) => {
			const table = one.kind === "table";
			$(`<div class="one-slash-item" role="option"></div>`)
				.toggleClass("active", i === open.active)
				.html(
					`${table ? frappe.utils.icon("table-2", "xs") : ""}<span>${esc(one.label)}</span>` +
						(table ? `<span class="one-slash-kind">${esc(__("Table"))}</span>` : "")
				)
				.on("mousedown", (e) => e.preventDefault())
				.on("click", () => {
					open.active = i;
					pick();
				})
				.appendTo($pop);
		});
		$pop.find(".one-slash-item.active").get(0)?.scrollIntoView({ block: "nearest" });
	};
	const pick = () => {
		if (open.table) {
			if (!open.columns.length) return;
			const text = `{{ table(${open.table.fieldname}, ${open.columns.map((one) => `"${one}"`).join(", ")}) }}`;
			const done = open;
			close();
			done.put(text);
			return;
		}
		const one = open.items[open.active];
		if (!one) return;
		if (one.kind === "table") {
			open.table = one;
			open.columns = [...one.columns];
			open.offered = null;
			draw();
			return;
		}
		const done = open;
		close();
		done.put(`{{ ${one.fieldname} }}`);
	};
	const typed = async (query, put, at) => {
		await load();
		open = { query, put, items: choices(query), active: 0, table: null, columns: [] };
		place(at);
		draw();
	};
	const keys = (e) => {
		if (!open) return;
		const n = open.items.length;
		if (e.key === "Escape") close();
		else if (e.key === "Enter" || e.key === "Tab") pick();
		else if (e.key === "ArrowDown" && !open.table) open.active = (open.active + 1) % Math.max(n, 1);
		else if (e.key === "ArrowUp" && !open.table) open.active = (open.active - 1 + Math.max(n, 1)) % Math.max(n, 1);
		else return;
		e.preventDefault();
		e.stopImmediatePropagation();
		if (open) draw();
	};

	// The subject: a plain input.
	const subject = form.fields_dict.subject.$input.get(0);
	subject.addEventListener("keydown", keys, true);
	subject.addEventListener("input", () => {
		const caret = subject.selectionStart;
		const found = TRIGGER.exec(subject.value.slice(0, caret));
		if (!found) return close();
		const start = caret - found[2].length - 1;
		const rect = subject.getBoundingClientRect();
		typed(found[2], (text) => {
			subject.value = subject.value.slice(0, start) + text + subject.value.slice(subject.selectionStart);
			subject.setSelectionRange(start + text.length, start + text.length);
			$(subject).trigger("change");
		}, { left: rect.left, top: rect.bottom + 4 });
	});

	// The message: frappe's text editor (Quill) and the HTML editor (Ace).
	const quill = (control) => {
		const q = control.quill;
		if (!q) return;
		q.root.parentElement.addEventListener("keydown", keys, true);
		q.on("text-change", (_d, _o, source) => {
			if (source !== "user") return;
			const at = q.getSelection();
			if (!at) return close();
			const from = Math.max(0, at.index - 40);
			const found = TRIGGER.exec(q.getText(from, at.index - from));
			if (!found) return close();
			const start = at.index - found[2].length - 1;
			const bounds = q.getBounds(start);
			const rect = q.root.getBoundingClientRect();
			typed(found[2], (text) => {
				const end = q.getSelection(true).index;
				q.deleteText(start, end - start, "api");
				q.insertText(start, text, "api");
				q.setSelection(start + text.length, 0, "api");
			}, { left: rect.left + bounds.left, top: rect.top + bounds.bottom + 4 });
		});
	};
	const ace_editor = (control) => {
		const editor = control.editor;
		if (!editor) return;
		editor.container.addEventListener("keydown", keys, true);
		editor.on("change", () =>
			setTimeout(() => {
				const at = editor.getCursorPosition();
				const found = TRIGGER.exec(editor.session.getLine(at.row).slice(0, at.column));
				if (!found) return close();
				const column = at.column - found[2].length - 1;
				const screen = editor.renderer.textToScreenCoordinates(at.row, column);
				typed(found[2], (text) => {
					const Range = ace.require("ace/range").Range;
					const now = editor.getCursorPosition();
					editor.session.replace(new Range(at.row, column, now.row, now.column), text);
					editor.focus();
				}, { left: screen.pageX, top: screen.pageY + editor.renderer.lineHeight + 4 });
			})
		);
	};
	const wire = () => {
		for (const fieldname of ["response", "response_html"]) {
			const control = form.fields_dict[fieldname];
			if (!control || control.one_slashed) continue;
			if (control.quill) quill(control);
			else if (control.editor) ace_editor(control);
			else continue;
			control.one_slashed = true;
		}
	};
	wire();
	// The editors are made when first shown: Write in HTML shows the other.
	form.fields_dict.use_html?.$input?.on("change", () => setTimeout(wire, 50));
	const field = form.fields_dict.reference_doctype;
	const changed = field.df.onchange;
	field.df.onchange = (...args) => {
		changed && changed.apply(field, args);
		load();
	};
	$(document).on("mousedown.one_slash", (e) => {
		if (open && !$(e.target).closest(".one-slash").length) close();
	});
	form.one_slash_close = () => {
		close();
		$pop.remove();
		$(document).off("mousedown.one_slash");
	};
};

// The template as it would be sent, from one record of the kind it is for:
// the latest unless another is picked (mail_templates.preview).
onedesk.mail_templates.preview = async (form, template) => {
	const doctype = form.get_value("reference_doctype");
	const latest = doctype
		? (await frappe.db.get_list(doctype, { fields: ["name"], limit: 1, order_by: "modified desc" }))[0]?.name
		: null;
	const dialog = new frappe.ui.Dialog({
		title: __("Preview"),
		size: "large",
		fields: [
			{
				fieldtype: "Link",
				fieldname: "record",
				label: doctype ? __(doctype) : __("Record"),
				options: doctype || "DocType",
				hidden: doctype ? 0 : 1,
				default: latest || "",
				description: !doctype
					? ""
					: latest
					? ""
					: __("No {0} yet, so its fields stay empty.", [__(doctype)]),
				onchange: () => draw(),
			},
			{ fieldtype: "HTML", fieldname: "shown" },
		],
	});
	const draw = async () => {
		const values = form.get_values(true) || {};
		const said = await frappe.xcall(onedesk.mail_templates.API + "preview", {
			subject: values.subject,
			response: values.response,
			response_html: values.response_html,
			use_html: values.use_html ? 1 : 0,
			doctype,
			name: dialog.get_value("record") || null,
			template,
		});
		const $shown = dialog.fields_dict.shown.$wrapper.empty();
		if (said.error) {
			$shown.append(onedesk.alert({ text: said.error, colour: "red" }));
			return;
		}
		$(`<div class="one-tpl-subject"></div>`).text(said.subject || "").appendTo($shown);
		$(`<iframe class="one-tpl-frame" sandbox="allow-same-origin"></iframe>`)
			.appendTo($shown)
			.on("load", function () {
				this.style.height = `${Math.min(this.contentDocument.body.scrollHeight + 24, 600)}px`;
			})
			.attr("srcdoc", `<style>body{margin:0;padding:12px;font:14px/1.5 -apple-system,system-ui,sans-serif}</style>${said.message || ""}`);
	};
	dialog.show();
	draw();
};

onedesk.mail_templates.save = async (name, doc, values) => {
	const fields = {
		subject: values.subject,
		reference_doctype: values.reference_doctype || null,
		use_html: values.use_html ? 1 : 0,
		response: values.response || "",
		response_html: values.response_html || "",
	};
	if (doc) await frappe.xcall("frappe.client.save", { doc: { ...doc, ...fields } });
	else await frappe.db.insert({ doctype: "Email Template", name: values.template_name.trim(), ...fields });
	frappe.show_alert({ message: __("Saved"), indicator: "green" });
};

onedesk.mail_templates.remove = (name, done) =>
	frappe.confirm(__("Delete {0}? Nobody can start from it again.", [frappe.utils.escape_html(name)]), async () => {
		await frappe.xcall("frappe.client.delete", { doctype: "Email Template", name });
		done && done();
	});

onedesk.mail_templates.edit = async (name, { doctype = null, done = null } = {}) => {
	const doc = name ? await frappe.db.get_doc("Email Template", name) : null;
	const dialog = new frappe.ui.Dialog({
		title: name || __("New Mail Template"),
		size: "large",
		fields: onedesk.mail_templates.fields(name, doc),
		primary_action_label: __("Save"),
		primary_action: async (values) => {
			await onedesk.mail_templates.save(name, doc, values);
			dialog.hide();
			done && done();
		},
	});
	const filled = doc ? dialog.set_values(doc) : null;
	if (doc) {
		dialog.set_secondary_action_label(__("Delete"));
		dialog.set_secondary_action(() =>
			onedesk.mail_templates.remove(name, () => {
				dialog.hide();
				done && done();
			})
		);
	}
	dialog.add_custom_action(__("Preview"), () => onedesk.mail_templates.preview(dialog, name));
	dialog.onhide = () => dialog.one_slash_close && dialog.one_slash_close();
	dialog.show();
	Promise.resolve(filled).then(() => onedesk.mail_templates.slash(dialog));
	if (!doc && doctype) dialog.set_value("reference_doctype", doctype);
};
