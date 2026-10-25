frappe.provide("onedesk.cloud");

// OneCloud's frappe dialogs: sharing and its links, a library's members, a
// server connection, a file request and its progress, a drive's address and
// passwords, and the question an upload asks when a name is taken. The
// island (frontend/src/cloud) opens them; they are desk's, as any dialog is.

onedesk.cloud.date_text = (value) => {
	if (!value) return "";
	const [day, time] = String(value).split(" ");
	return `${frappe.datetime.str_to_user(day)} ${(time || "").slice(0, 5)}`.trim();
};

// The file or folder open in OneCloud, for OneAI (oneai.js, where). The
// island says it as it moves.
onedesk.cloud.where = null;
onedesk.cloud.here = () => ((frappe.get_route() || [])[0] === "onecloud" ? onedesk.cloud.where : null);

onedesk.cloud.share = (item, done = () => {}) => {
	if (item.library) return onedesk.cloud.members(item);
	const call = (method, args) => frappe.xcall("onedesk.one_storage.share." + method, args);
	const dialog = new frappe.ui.Dialog({
		title: __("Share {0}", [item.name]),
		no_focus: true,
		fields: [
			{
				fieldtype: "MultiSelectPills",
				fieldname: "users",
				label: __("Add people"),
				get_data: (txt) => frappe.db.get_link_options("User", txt, { user_type: "System User", enabled: 1 }),
			},
			{
				fieldtype: "Select",
				fieldname: "access",
				label: __("Access"),
				options: [
					{ value: "view", label: __("View") },
					{ value: "edit", label: __("Edit") },
				],
				default: "view",
			},
			{ fieldtype: "HTML", fieldname: "people" },
		],
		primary_action_label: __("Share"),
		primary_action: async (values) => {
			if (!(values.users || []).length) return;
			await call("share", { nodes: [item.id], users: values.users, edit: values.access === "edit" ? 1 : 0 });
			dialog.set_value("users", []);
			draw();
			done();
		},
	});
	const esc = frappe.utils.escape_html;
	const draw = async () => {
		const who = await call("people", { node: item.id });
		const $people = dialog.fields_dict.people.$wrapper;
		const row = (person, right) =>
			`<div class="oc-person" data-user="${esc(person.user)}">${frappe.avatar(person.user, "avatar-small")}<span class="oc-person-name">${esc(person.name)}</span>${right}</div>`;
		const choose = (person) =>
			who.can_share
				? `<select class="oc-person-access"><option value="view" ${person.edit ? "" : "selected"}>${__("Can view")}</option><option value="edit" ${person.edit ? "selected" : ""}>${__("Can edit")}</option></select>
					${frappe.ui.button.html({ variant: "ghost", size: "sm", icon: "x", title: __("Remove"), attrs: { "data-remove": true } })}`
				: `<span class="oc-person-right">${person.edit ? __("Can edit") : __("Can view")}</span>`;
		const inherited = (person) => `<span class="oc-person-right">${person.edit ? __("Can edit") : __("Can view")} · ${esc(__("from {0}", [person.from]))}</span>`;
		const owner_note = __("Owner");
		const people_head = who.can_share || who.people.length ? __("People with access") : "";
		const record_note = item.record && !item.folder ? __("Anyone who can open the record can open this file.") : "";
		const found = who.can_link ? await frappe.xcall("onedesk.one_storage.links.links", { node: item.id }) : [];
		$people.html(`
			${people_head ? `<div class="oc-people-head">${people_head}</div>` : ""}
			${record_note ? `<p class="oc-people-note">${record_note}</p>` : ""}
			${people_head ? row(who.owner, `<span class="oc-person-right">${owner_note}</span>`) : ""}
			${who.people.map((person) => row(person, choose(person))).join("")}
			${who.inherited.map((person) => row(person, inherited(person))).join("")}
			${who.can_link ? onedesk.cloud.links_html(found) : ""}`);
		$people.find("[data-new-link]").on("click", () => onedesk.cloud.new_link(item, draw));
		$people.find("[data-copy-link]").on("click", (e) => {
			frappe.utils.copy_to_clipboard($(e.currentTarget).closest(".oc-link").attr("data-url"));
		});
		$people.find("[data-drop-link]").on("click", async (e) => {
			await frappe.xcall("onedesk.one_storage.links.drop", { name: $(e.currentTarget).closest(".oc-link").attr("data-name") });
			draw();
		});
		$people.find(".oc-person-access").on("change", async (e) => {
			const user = $(e.target).closest(".oc-person").attr("data-user");
			await call("set_edit", { node: item.id, user, edit: e.target.value === "edit" ? 1 : 0 });
		});
		$people.find("[data-remove]").on("click", async (e) => {
			const user = $(e.currentTarget).closest(".oc-person").attr("data-user");
			await call("unshare", { node: item.id, user });
			draw();
			done();
		});
		dialog.fields_dict.users.$wrapper.toggle(!!who.can_share);
		dialog.set_title(who.can_share ? __("Share {0}", [item.name]) : __("Links to {0}", [item.name]));
		dialog.fields_dict.access.$wrapper.toggle(!!who.can_share);
		dialog.get_primary_btn().toggle(!!who.can_share);
	};
	dialog.show();
	draw();
};

onedesk.cloud.links_html = (found) => {
	const esc = frappe.utils.escape_html;
	const head = __("Links");
	const make = __("Create link");
	const copy = __("Copy link");
	const remove = __("Remove");
	const rows = found
		.map((one) => {
			const said = [
				one.audience === "Invited people" ? __("Only {0}", [one.invitees.join(", ")]) : __("Anyone With Link"),
				one.allow_upload ? __("can upload") : one.allow_download ? __("can download") : __("can view"),
				one.expires_on ? (one.expired ? __("expired {0}", [onedesk.cloud.date_text(one.expires_on)]) : __("until {0}", [onedesk.cloud.date_text(one.expires_on)])) : "",
				one.has_password ? __("password") : "",
				one.opened ? __("opened {0} times", [one.opened]) : "",
			].filter(Boolean);
			return `<div class="oc-link" data-name="${esc(one.name)}" data-url="${esc(one.url)}">
				${frappe.utils.icon("link", "sm")}
				<span class="oc-link-said">${esc(said.join(" · "))}</span>
				${frappe.ui.button.html({ variant: "ghost", size: "sm", icon: "copy", title: copy, attrs: { "data-copy-link": true } })}
				${frappe.ui.button.html({ variant: "ghost", size: "sm", icon: "x", title: remove, attrs: { "data-drop-link": true } })}
			</div>`;
		})
		.join("");
	return `<div class="oc-people-head">${head}</div>${rows}
		${frappe.ui.button.html({ variant: "subtle", icon: "link", label: make, attrs: { "data-new-link": true } })}`;
};

onedesk.cloud.new_link = (item, after) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Create link"),
		fields: [
			{
				fieldtype: "Select",
				fieldname: "audience",
				label: __("Access"),
				options: [
					{ value: "Anyone With Link", label: __("Anyone With Link") },
					{ value: "Invited people", label: __("Invited People Only") },
				],
				default: "Anyone With Link",
			},
			{
				fieldtype: "Small Text",
				fieldname: "invitees",
				label: __("Email addresses"),
				description: __("One per line. Each gets the link and a sign-in code."),
				depends_on: "eval:doc.audience=='Invited people'",
				mandatory_depends_on: "eval:doc.audience=='Invited people'",
			},
			{ fieldtype: "Section Break" },
			{ fieldtype: "Check", fieldname: "allow_download", label: __("Can download"), default: 1 },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Check", fieldname: "allow_upload", label: __("Can upload"), default: 0, hidden: item.folder ? 0 : 1 },
			{ fieldtype: "Section Break" },
			{ fieldtype: "Datetime", fieldname: "expires_on", label: __("Expires on") },
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Password",
				fieldname: "password",
				label: __("Password"),
				depends_on: "eval:doc.audience!='Invited people'",
			},
		],
		primary_action_label: __("Create link"),
		primary_action: async (values) => {
			const invitees = (values.invitees || "")
				.split(/[\s,;]+/)
				.map((one) => one.trim())
				.filter(Boolean);
			const made = await frappe.xcall("onedesk.one_storage.links.make", {
				node: item.id,
				audience: values.audience,
				invitees,
				allow_download: values.allow_download ? 1 : 0,
				allow_upload: values.allow_upload ? 1 : 0,
				expires_on: values.expires_on || null,
				password: values.password || null,
			});
			dialog.hide();
			frappe.utils.copy_to_clipboard(made.url);
			after();
		},
	});
	dialog.show();
};

onedesk.cloud.new_library = (go) => {
	frappe.prompt(
		{ fieldtype: "Data", fieldname: "name", label: __("Library name"), reqd: 1 },
		async ({ name }) => {
			const made = await frappe.xcall("onedesk.one_storage.library.make", { name });
			go(made.id, "@libraries");
		},
		__("New library"),
		__("Create")
	);
};

onedesk.cloud.members = (item) => {
	const call = (method, args) => frappe.xcall("onedesk.one_storage.library." + method, args);
	const roles = [
		{ value: "Reader", label: __("Reader") },
		{ value: "Member", label: __("Member") },
		{ value: "Owner", label: __("Owner") },
	];
	const dialog = new frappe.ui.Dialog({
		title: __("Members of {0}", [item.name]),
		no_focus: true,
		fields: [
			{
				fieldtype: "MultiSelectPills",
				fieldname: "users",
				label: __("Add people"),
				get_data: (txt) => frappe.db.get_link_options("User", txt, { user_type: "System User", enabled: 1 }),
			},
			{
				fieldtype: "Select",
				fieldname: "role",
				label: __("Role"),
				options: roles,
				default: "Member",
				description: __("Readers can view and download. Members can also add, change and delete. Owners can also manage members."),
			},
			{ fieldtype: "HTML", fieldname: "people" },
		],
		primary_action_label: __("Add"),
		primary_action: async (values) => {
			if (!(values.users || []).length) return;
			await call("add", { node: item.id, users: values.users, role: values.role });
			dialog.set_value("users", []);
			draw();
		},
	});
	const esc = frappe.utils.escape_html;
	const draw = async () => {
		const found = await call("members", { node: item.id });
		const choose = (one) =>
			found.can_manage
				? `<select class="oc-person-access">${roles
						.map((role) => `<option value="${role.value}" ${role.value === one.role ? "selected" : ""}>${esc(role.label)}</option>`)
						.join("")}</select>
					${frappe.ui.button.html({ variant: "ghost", size: "sm", icon: "x", title: __("Remove"), attrs: { "data-remove": true } })}`
				: `<span class="oc-person-right">${esc(__(one.role))}</span>`;
		const head = __("Members");
		dialog.fields_dict.people.$wrapper.html(`<div class="oc-people-head">${head}</div>${found.members
			.map(
				(one) =>
					`<div class="oc-person" data-user="${esc(one.user)}">${frappe.avatar(one.user, "avatar-small")}<span class="oc-person-name">${esc(one.name)}</span>${choose(one)}</div>`
			)
			.join("")}`);
		const $people = dialog.fields_dict.people.$wrapper;
		$people.find(".oc-person-access").on("change", async (e) => {
			const user = $(e.target).closest(".oc-person").attr("data-user");
			await call("add", { node: item.id, users: [user], role: e.target.value });
			draw();
		});
		$people.find("[data-remove]").on("click", async (e) => {
			const user = $(e.currentTarget).closest(".oc-person").attr("data-user");
			await call("remove", { node: item.id, user });
			draw();
		});
		dialog.fields_dict.users.$wrapper.toggle(!!found.can_manage);
		dialog.fields_dict.role.$wrapper.toggle(!!found.can_manage);
		dialog.get_primary_btn().toggle(!!found.can_manage);
	};
	dialog.show();
	draw();
};

onedesk.cloud.mount = async (item, go) => {
	const found = item ? await frappe.xcall("onedesk.one_storage.mounts.settings", { node: item.id }) : null;
	const values = (found && found.values) || {};
	const admin = frappe.user.has_role("Workspace Administrator");
	const dialog = new frappe.ui.Dialog({
		title: item ? __("Edit {0}", [item.name]) : __("Connect server"),
		fields: [
			{ fieldtype: "Data", fieldname: "title", label: __("Name"), reqd: 1, default: values.title },
			{ fieldtype: "Data", fieldname: "host", label: __("Server"), default: values.host, depends_on: "eval:doc.protocol=='SFTP'" },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Select", fieldname: "protocol", label: __("Type"), options: ["SFTP", "WebDAV"], default: values.protocol || "SFTP" },
			{ fieldtype: "Int", fieldname: "port", label: __("Port"), default: values.port || 22, depends_on: "eval:doc.protocol=='SFTP'" },
			{ fieldtype: "Section Break" },
			{
				fieldtype: "Data",
				fieldname: "url",
				label: __("Address"),
				default: values.url,
				depends_on: "eval:doc.protocol=='WebDAV'",
				description: __("Starts with https://"),
			},
			{ fieldtype: "Data", fieldname: "root_path", label: __("Server Folder"), default: values.root_path || "/" },
			{ fieldtype: "Section Break", label: __("Sign In") },
			{ fieldtype: "Data", fieldname: "username", label: __("User Name"), default: values.username },
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Password",
				fieldname: "password",
				label: __("Password"),
				description: item ? __("Leave empty to keep the saved password.") : "",
			},
			{ fieldtype: "Section Break", label: __("Key Authentication"), collapsible: 1 },
			{
				fieldtype: "Small Text",
				fieldname: "private_key",
				label: __("Private Key"),
				description: __("SFTP only. Used instead of a password."),
			},
			{ fieldtype: "Section Break" },
			{
				fieldtype: "Check",
				fieldname: "shared",
				label: __("Share With Team"),
				default: values.shared || 0,
				hidden: admin ? 0 : 1,
			},
		],
		primary_action_label: item ? __("Save") : __("Connect"),
		primary_action: async (entered) => {
			const made = await frappe.xcall("onedesk.one_storage.mounts.save", { values: entered, name: found ? found.name : null });
			dialog.hide();
			go(made.id, "@mounts");
		},
	});
	dialog.show();
};

onedesk.cloud.request = async ({ node, kind, trail }, go) => {
	const parts = node.split("/");
	const record = parts[0] === "@records" && parts.length === 3 ? { doctype: parts[1], name: parts[2] } : null;
	const fields = record ? await frappe.xcall("onedesk.one_storage.file_requests.fields", { doctype: record.doctype }) : [];
	const by_label = Object.fromEntries(fields.map((one) => [one.label, one.value]));
	const here = trail[trail.length - 1];
	const dialog = new frappe.ui.Dialog({
		title: __("New file request"),
		size: "large",
		fields: [
			{ fieldtype: "Data", fieldname: "title", label: __("Title"), reqd: 1 },
			{ fieldtype: "Small Text", fieldname: "recipients", label: __("Recipients"), reqd: 1, description: __("Email addresses, one per line.") },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Date", fieldname: "due_date", label: __("Due Date") },
			{ fieldtype: "Small Text", fieldname: "message", label: __("Message") },
			{ fieldtype: "Section Break" },
			{
				fieldtype: "Table",
				fieldname: "items",
				label: __("Files"),
				cannot_add_rows: false,
				in_place_edit: true,
				data: [{ required: 1 }],
				fields: [
					{ fieldtype: "Data", fieldname: "label", label: __("File"), in_list_view: 1, reqd: 1, columns: 3 },
					{ fieldtype: "Check", fieldname: "required", label: __("Required"), in_list_view: 1, default: 1, columns: 1 },
					{ fieldtype: "Check", fieldname: "several", label: __("Multiple"), in_list_view: 1, columns: 1 },
					{ fieldtype: "Data", fieldname: "accept", label: __("File Types"), in_list_view: 1, columns: 2 },
					{
						fieldtype: "Select",
						fieldname: "field",
						label: __("Record Field"),
						options: ["", ...fields.map((one) => one.label)].join("\n"),
						in_list_view: record ? 1 : 0,
						hidden: record ? 0 : 1,
						columns: 3,
					},
				],
			},
			{
				fieldtype: "HTML",
				fieldname: "where",
				options: `<p class="oc-people-note">${frappe.utils.escape_html(
					record
						? __("Files are attached to {0}.", [here ? here.name : ""])
						: __("Files are saved to a new folder in {0}.", [here ? here.name : __("My Files")])
				)}</p>`,
			},
		],
		primary_action_label: __("Send request"),
		primary_action: async (values) => {
			const items = (values.items || []).map((one) => ({ ...one, fieldname: by_label[one.field] || null }));
			const made = await frappe.xcall("onedesk.one_storage.file_requests.make", {
				node: kind === "requests" ? "@requests" : node,
				values: { ...values, items },
			});
			dialog.hide();
			if (!made.mailed) onedesk.cloud.request_links(made.links);
			else frappe.show_alert({ message: __("Request sent"), indicator: "green" });
			go(made.node, "@requests");
		},
	});
	dialog.show();
};

onedesk.cloud.request_links = (links) => {
	const esc = frappe.utils.escape_html;
	const copy = __("Copy");
	const dialog = new frappe.ui.Dialog({
		title: __("Request links"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "links",
				options: `<p class="oc-people-note">${esc(__("Email isn't set up, so these links weren't sent."))}</p>
					${links
						.map(
							(one) => `<div class="oc-drive-row"><span>${esc(one.email)}</span><code>${esc(one.url)}</code>${frappe.ui.button.html({ variant: "ghost", size: "sm", label: copy, attrs: { "data-copy": one.url } })}</div>`
						)
						.join("")}`,
			},
		],
	});
	dialog.fields_dict.links.$wrapper.find("[data-copy]").on("click", (e) => frappe.utils.copy_to_clipboard(e.currentTarget.dataset.copy));
	dialog.show();
};

onedesk.cloud.request_progress = async (name, done = () => {}) => {
	const call = (method, args) => frappe.xcall("onedesk.one_storage.file_requests." + method, args);
	const found = await call("progress", { name });
	const esc = frappe.utils.escape_html;
	const states = { Waiting: __("Waiting"), "Partly Sent": __("Partly Sent"), Complete: __("Complete") };
	const copy = __("Copy link");
	const head = found.items.map((one) => `<th>${esc(one.label)}${one.required ? " *" : ""}</th>`).join("");
	const rows = found.people
		.map(
			(person) => `<tr><td>${esc(person.email)}<br><small>${esc(states[person.state] || person.state)}</small></td>
				${found.items.map((one) => `<td title="${esc((person.sent[one.label] || []).join(", "))}">${(person.sent[one.label] || []).length ? "✓" : "–"}</td>`).join("")}
				<td>${frappe.ui.button.html({ variant: "ghost", size: "sm", label: copy, attrs: { "data-copy": person.url } })}</td></tr>`
		)
		.join("");
	const closed = found.status === "Closed";
	const dialog = new frappe.ui.Dialog({
		title: found.title,
		size: "large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "table",
				options: `<div class="oc-progress"><table><thead><tr><th></th>${head}<th></th></tr></thead><tbody>${rows}</tbody></table></div>
					<p class="oc-people-note">${esc(closed ? __("This request is closed.") : __("* required"))}</p>`,
			},
		],
		primary_action_label: __("Remind"),
		primary_action: async () => {
			const sent = await call("remind", { name });
			frappe.show_alert({ message: sent ? __("Reminder sent to {0} people", [sent]) : __("No reminders sent"), indicator: "blue" });
		},
		secondary_action_label: closed ? __("Reopen") : __("Close request"),
		secondary_action: async () => {
			await call("close", { name, closed: closed ? 0 : 1 });
			dialog.hide();
			done("@requests");
		},
	});
	dialog.fields_dict.table.$wrapper.find("[data-copy]").on("click", (e) => frappe.utils.copy_to_clipboard(e.currentTarget.dataset.copy));
	dialog.get_primary_btn().toggle(!closed);
	dialog.show();
};

onedesk.cloud.drive = async (node, name) => {
	const where = await frappe.xcall("onedesk.one_storage.dav.address", {
		node: ["@root", "@recent", "@starred", "@bin", "@mounts"].includes(node) || node.startsWith("@mount/") ? "@root" : node,
	});
	const esc = frappe.utils.escape_html;
	const steps = [
		[__("Windows"), __("In File Explorer, right-click This PC, choose Map network drive and paste the address.")],
		[__("macOS"), __("In Finder, choose Go › Connect to Server and paste the address.")],
		[__("Linux"), __("In Files, choose Other Locations and paste the address with davs:// in place of https://.")],
	];
	const dialog = new frappe.ui.Dialog({
		title: __("Connect {0} as a drive", [name]),
		fields: [
			{ fieldtype: "Data", fieldname: "url", label: __("Address"), read_only: 1, default: where.url },
			{ fieldtype: "Data", fieldname: "user_name", label: __("User name"), read_only: 1, default: where.user_name },
			{
				fieldtype: "HTML",
				fieldname: "how",
				options: `<dl class="oc-drive-steps">${steps.map(([os, text]) => `<dt>${esc(os)}</dt><dd>${esc(text)}</dd>`).join("")}</dl>
					<p class="oc-people-note">${esc(__("Sign in with a drive password, not your One password."))}</p>
					<div class="oc-drive-key"></div><div class="oc-drive-list"></div>`,
			},
		],
		primary_action_label: __("Create password"),
		primary_action: () => {
			frappe.prompt(
				{ fieldtype: "Data", fieldname: "label", label: __("Computer"), reqd: 1 },
				async ({ label }) => {
					const made = await frappe.xcall("onedesk.one_storage.dav.make_password", { label });
					const copy = __("Copy");
					const $how = dialog.fields_dict.how.$wrapper;
					$how.find(".oc-drive-key").html(`
						<div class="oc-people-head">${esc(__("Copy it now. It won't be shown again."))}</div>
						<div class="oc-drive-row"><span>${esc(__("Password"))}</span><code>${esc(made.password)}</code>${frappe.ui.button.html({ variant: "ghost", size: "sm", label: copy, attrs: { "data-copy": made.password } })}</div>`);
					$how.find("[data-copy]").on("click", (e) => frappe.utils.copy_to_clipboard(e.currentTarget.dataset.copy));
					list();
				},
				__("New drive password"),
				__("Create")
			);
		},
	});
	const list = async () => {
		const found = await frappe.xcall("onedesk.one_storage.dav.passwords");
		const $list = dialog.fields_dict.how.$wrapper.find(".oc-drive-list");
		if (!found.length) return $list.empty();
		const head = __("Drive passwords");
		const never = __("Never used");
		const remove = __("Remove");
		$list.html(`<div class="oc-people-head">${head}</div>${found
			.map(
				(one) => `<div class="oc-person" data-name="${esc(one.name)}">${frappe.utils.icon("key", "sm")}
					<span class="oc-person-name">${esc(one.label)}</span>
					<span class="oc-person-right">${one.last_used ? esc(__("Used {0}", [onedesk.cloud.date_text(one.last_used)])) : never}</span>
					${frappe.ui.button.html({ variant: "ghost", size: "sm", icon: "x", title: remove, attrs: { "data-drop": true } })}</div>`
			)
			.join("")}`);
		$list.find("[data-drop]").on("click", async (e) => {
			await frappe.xcall("onedesk.one_storage.dav.drop_password", { name: $(e.currentTarget).closest(".oc-person").attr("data-name") });
			list();
		});
	};
	dialog.show();
	list();
};

onedesk.cloud.read_file = (item) => {
	frappe.confirm(
		__("Read {0} with OneAI? OneAI files it and acts on it. Scans and photos use credits.", [
			`<b>${frappe.utils.escape_html(item.name)}</b>`,
		]),
		async () => {
			await frappe.xcall("onedesk.one_ai.reading.switches.read_now", { file: item.id });
			frappe.show_alert({ message: __("OneAI is reading {0}.", [item.name]), indicator: "green" });
		}
	);
};

onedesk.cloud.ask_replace = (clash) => {
	return new Promise((answer) => {
		const names = clash.slice(0, 5).map((one) => frappe.utils.escape_html(one.file.name)).join("<br>");
		const more = clash.length > 5 ? `<br>${__("and {0} more", [clash.length - 5])}` : "";
		const dialog = new frappe.ui.Dialog({
			title: clash.length === 1 ? __("A file with this name is already here") : __("{0} files with these names are already here", [clash.length]),
			fields: [{ fieldtype: "HTML", options: `<p>${names}${more}</p><p class="text-muted">${__("Replaced files are kept as earlier versions.")}</p>` }],
			primary_action_label: __("Replace"),
			primary_action: () => {
				answer(true);
				dialog.hide();
			},
			secondary_action_label: __("Keep both"),
			secondary_action: () => {
				answer(false);
				dialog.hide();
			},
		});
		dialog.onhide = () => answer(false);
		dialog.show();
	});
};
