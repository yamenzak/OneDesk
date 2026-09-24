// OneMail: every mailbox a person holds, in one place.
//
// Three panes, as every mail client has them: the mailboxes and their
// folders, the conversations in the folder that is open, and the
// conversation that is open. Nothing here decides anything. Lists are
// one_mail/api.py, changes are one_mail/actions.py, and both refuse
// whoever does not hold the mailbox.
//
// Writing, replying and forwarding use the desk's own email composer, so a
// message sent from here is queued, retried, undoable and filed exactly as
// one sent from a record.
//
// A message is drawn in a sandboxed frame with no scripts. Pictures from
// elsewhere are not fetched until asked for, because fetching one tells its
// sender the message was opened.
//
// Where you are is in the address (?box=…&folder=…&thread=…), so back, a
// bookmark and a pasted link all land in the same place.

frappe.provide("onedesk");

onedesk.OneMail = class OneMail {
	static API = "onedesk.one_mail.api.";
	static ACT = "onedesk.one_mail.actions.";
	// How a conversation came to be on a record (one_mail/linking.py).
	static FILED_BY = {
		contact: __("Filed by its contact"),
		address: __("Filed by address"),
		thread: __("Filed with its conversation"),
		text: __("Named in the message"),
		manual: __("Filed by hand"),
	};
	static KINDS = {
		Inbox: ["inbox", __("Inbox")],
		Drafts: ["file-pen-line", __("Drafts")],
		Sent: ["send", __("Sent")],
		Archive: ["archive", __("Archive")],
		Junk: ["shield-alert", __("Junk")],
		Trash: ["trash-2", __("Trash")],
		Other: ["folder", null],
	};

	constructor(page) {
		this.page = page;
		this.boxes = [];
		this.box = null;
		this.folder = null;
		this.thread = null;
		this.items = [];
		this.more = 0;
		this.search = "";
		this.selected = new Set();
		this.pictures = new Set();
		this.closed = new Set();
		this.build();
		this.bind();
		this.listen();
		$(window).on("resize.onemail", frappe.utils.debounce(() => this.fit(), 100));
		this.load();
	}

	// ---------------------------------------------------------------- frame

	build() {
		const icon = (name) => frappe.utils.icon(name, "sm");
		const bare = (act, name, label) =>
			`<button class="es-button" data-variant="ghost" data-icon-button="true" data-act="${act}" title="${label}" aria-label="${label}">${icon(name)}</button>`;
		this.$root = $(`<div class="om" tabindex="-1">
			<nav class="om-side" aria-label="${__("Mailboxes")}">
				<button class="es-button om-write" data-variant="solid" data-act="write">${icon("pencil")}<span class="es-button__label">${__("Write")}</span></button>
				<div class="om-boxes"></div>
				<button class="es-button om-connect" data-variant="ghost" data-act="connect">${icon("plug")}<span class="es-button__label">${__("Connect a mailbox")}</span></button>
			</nav>
			<section class="om-list" aria-label="${__("Conversations")}">
				<div class="om-list-head">
					<label class="om-search">${icon("search")}<input type="search" spellcheck="false" placeholder="${__("Search this mailbox")}"></label>
					${bare("box-files", "paperclip", __("This mailbox's attachments, in OneCloud"))}
					${bare("refresh", "refresh-cw", __("Refresh"))}
				</div>
				<div class="om-picked" hidden>
					<span class="om-picked-count"></span>
					<span class="om-grow"></span>
					${bare("read", "mail-open", __("Mark as read"))}
					${bare("unread", "mail", __("Mark as unread"))}
					${bare("star", "star", __("Star"))}
					${bare("move", "folder-input", __("Move to"))}
					${bare("archive", "archive", __("Archive"))}
					${bare("delete", "trash-2", __("Delete"))}
					${bare("clear", "x", __("Clear selection"))}
				</div>
				<div class="om-folder-name"></div>
				<div class="om-items" tabindex="0" role="listbox" aria-multiselectable="true"></div>
			</section>
			<article class="om-read" aria-live="polite"></article>
		</div>`).appendTo(this.page.main);
		this.$boxes = this.$root.find(".om-boxes");
		this.$items = this.$root.find(".om-items");
		this.$read = this.$root.find(".om-read");
		this.$search = this.$root.find(".om-search input");
		this.fit();
	}

	fit() {
		const el = this.$root && this.$root[0];
		if (!el || !el.offsetParent) return;
		const top = el.getBoundingClientRect().top + window.scrollY;
		el.style.height = `${Math.max(420, window.innerHeight - top)}px`;
	}

	show() {
		this.fit();
		if (this.stale) {
			this.stale = false;
			this.refresh();
		}
	}

	// ---------------------------------------------------------------- state

	wanted() {
		const query = frappe.utils.get_query_params();
		return { box: query.box || null, folder: query.folder || null, thread: query.thread || null };
	}

	place(push = false) {
		const query = new URLSearchParams();
		if (this.box) query.set("box", this.box.name);
		if (this.folder) query.set("folder", this.folder.name);
		if (this.thread) query.set("thread", this.thread);
		const url = `${location.pathname}?${query}`;
		if (url === location.pathname + location.search) return;
		history[push ? "pushState" : "replaceState"](null, "", url);
	}

	async load() {
		this.boxes = (await frappe.xcall(OneMail.API + "mailboxes")) || [];
		const want = this.wanted();
		this.box = this.boxes.find((one) => one.name === want.box) || this.boxes[0] || null;
		const folders = (this.box && this.box.folders) || [];
		this.folder = folders.find((one) => one.name === want.folder) || folders.find((one) => one.kind === "Inbox") || folders[0] || null;
		this.draw_boxes();
		if (!this.box) return this.draw_nothing();
		await this.list();
		if (want.thread) this.open(want.thread);
		else this.draw_reading();
	}

	async refresh() {
		const thread = this.thread;
		this.boxes = (await frappe.xcall(OneMail.API + "mailboxes")) || [];
		if (this.box) this.box = this.boxes.find((one) => one.name === this.box.name) || this.boxes[0] || null;
		if (this.box && this.folder) {
			this.folder = this.box.folders.find((one) => one.name === this.folder.name) || this.box.folders[0] || null;
		}
		this.draw_boxes();
		if (!this.box) return this.draw_nothing();
		await this.list({ keep: true });
		if (thread) this.open(thread, { quiet: true });
	}

	// ---------------------------------------------------------------- live

	listen() {
		const again = frappe.utils.debounce(() => this.refresh(), 800);
		frappe.realtime.on("onemail_change", (data) => {
			if (!data || !this.boxes.some((one) => one.name === data.account)) return;
			if (!this.$root.is(":visible")) return (this.stale = true);
			// Not while somebody is choosing a folder to move to.
			if (this.$menu) return setTimeout(again, 1500);
			again();
		});
	}

	// ---------------------------------------------------------------- mailboxes

	folder_label(folder) {
		const [, label] = OneMail.KINDS[folder.kind] || OneMail.KINDS.Other;
		if (label && folder.kind !== "Other") return label;
		return folder.label || folder.path;
	}

	depth(folder) {
		if (!folder.delimiter || folder.kind !== "Other") return 0;
		return folder.path.split(folder.delimiter).length - 1;
	}

	draw_boxes() {
		const esc = frappe.utils.escape_html;
		const html = this.boxes
			.map((box) => {
				const closed = this.closed.has(box.name);
				const kind = box.workspace ? "building-2" : box.shared ? "users" : "at-sign";
				const folders = closed
					? ""
					: box.folders
							.map((folder) => {
								const [name] = OneMail.KINDS[folder.kind] || OneMail.KINDS.Other;
								const on = this.folder && this.folder.name === folder.name && !this.search;
								const count = folder.unread && folder.kind !== "Sent" && folder.kind !== "Trash" ? `<span class="om-count">${folder.unread}</span>` : "";
								return `<button class="om-folder${on ? " om-on" : ""}${folder.unread ? " om-has-unread" : ""}" data-box="${esc(box.name)}" data-folder="${esc(folder.name)}" style="--depth:${this.depth(folder)}">
									${frappe.utils.icon(name, "sm")}<span class="om-folder-label">${esc(this.folder_label(folder))}</span>${count}
								</button>`;
							})
							.join("");
				const trouble = box.error ? `<span class="om-trouble" title="${esc(box.error)}">${frappe.utils.icon("triangle-alert", "sm")}</span>` : "";
				return `<div class="om-box" data-box="${esc(box.name)}">
					<button class="om-box-head" data-toggle="${esc(box.name)}" aria-expanded="${closed ? "false" : "true"}">
						${frappe.utils.icon(closed ? "chevron-right" : "chevron-down", "xs")}
						${frappe.utils.icon(kind, "sm")}
						<span class="om-box-name" title="${esc(box.email)}">${esc(box.workspace ? __("Workspace") : box.email)}</span>
						${trouble}
					</button>
					${box.workspace ? `<div class="om-box-address">${esc(box.email)}</div>` : ""}
					<div class="om-folders">${folders}</div>
				</div>`;
			})
			.join("");
		this.$boxes.html(html || `<div class="om-none">${__("You hold no mailbox yet.")}</div>`);
		// A person's own address that only receives cannot be written from.
		this.$root.find("[data-act=write]").prop("disabled", !this.sender());
	}

	draw_nothing() {
		this.$items.empty();
		this.$root.find(".om-folder-name").empty();
		this.$read.html(`<div class="om-empty">${frappe.utils.icon("mail", "lg")}
			<p>${__("Connect a mailbox to read and write your mail here.")}</p></div>`);
	}

	choose(boxname, foldername) {
		const box = this.boxes.find((one) => one.name === boxname);
		if (!box) return;
		this.box = box;
		this.folder = box.folders.find((one) => one.name === foldername) || box.folders[0];
		this.thread = null;
		this.search = "";
		this.$search.val("");
		this.selected.clear();
		this.draw_boxes();
		this.place(true);
		this.list();
		this.draw_reading();
	}

	// ---------------------------------------------------------------- the list

	async list({ keep = false, more = false } = {}) {
		if (!this.box) return;
		const start = more ? this.items.length : 0;
		const asked = (this.asked = {});
		const answer = await frappe.xcall(OneMail.API + "conversations", {
			account: this.box.name,
			folder: this.folder ? this.folder.name : null,
			search: this.search || null,
			start,
		});
		if (asked !== this.asked) return; // a newer list was asked for
		this.items = more ? this.items.concat(answer.items) : answer.items;
		this.more = answer.more;
		if (!keep) this.selected.clear();
		const here = new Set(this.items.map((one) => one.thread));
		for (const one of [...this.selected]) if (!here.has(one)) this.selected.delete(one);
		this.draw_list();
	}

	when(value, long = false) {
		if (!value) return "";
		if (long) return frappe.datetime.str_to_user(value);
		// Today's by the time, anything older by the date.
		if (value.slice(0, 10) === frappe.datetime.get_today()) return frappe.datetime.str_to_user(value, true).replace(/(\d{1,2}:\d{2}):\d{2}/, "$1");
		return frappe.datetime.str_to_user(value.slice(0, 10));
	}

	// As the explorer writes a size.
	size_text(bytes) {
		if (!bytes) return "";
		const units = [__("B"), __("KB"), __("MB"), __("GB")];
		let at = 0;
		while (bytes >= 1024 && at < units.length - 1) {
			bytes /= 1024;
			at++;
		}
		return `${at ? bytes.toFixed(bytes < 10 ? 1 : 0) : bytes} ${units[at]}`;
	}

	face(name, email, picture) {
		if (picture) return `<img class="om-face" src="${frappe.utils.escape_html(picture)}" alt="" loading="lazy">`;
		const text = (name || email || "?").trim();
		const parts = text.replace(/[<>"']/g, "").split(/[\s@._-]+/).filter(Boolean);
		const initials = ((parts[0] || "?")[0] + ((parts[1] || "")[0] || "")).toUpperCase();
		let hue = 0;
		for (const char of email || text) hue = (hue * 31 + char.charCodeAt(0)) % 360;
		return `<span class="om-face" style="--hue:${hue}" aria-hidden="true">${frappe.utils.escape_html(initials)}</span>`;
	}

	who(item) {
		// In Sent, a conversation is shown by who it went to.
		if (item.sent && item.recipients) {
			const first = item.recipients.split(",")[0].trim();
			return __("To {0}", [first.replace(/<.*>/, "").trim() || first]);
		}
		return item.sender_name || item.sender || __("Unknown sender");
	}

	draw_list() {
		const esc = frappe.utils.escape_html;
		const title = this.search ? __("Results for {0}", [this.search]) : this.folder ? this.folder_label(this.folder) : "";
		this.$root.find(".om-folder-name").text(title);
		if (!this.items.length) {
			this.$items.html(`<div class="om-none">${this.search ? __("Nothing matches.") : __("Nothing here.")}</div>`);
			return this.draw_picked();
		}
		const rows = this.items
			.map((item) => {
				const classes = ["om-row"];
				if (item.unread) classes.push("om-unread");
				if (item.thread === this.thread) classes.push("om-open");
				if (this.selected.has(item.thread)) classes.push("om-picked-row");
				const count = item.count > 1 ? `<span class="om-thread-count">${item.count}</span>` : "";
				const clip = item.attachments ? frappe.utils.icon("paperclip", "xs") : "";
				return `<div class="${classes.join(" ")}" role="option" data-thread="${esc(item.thread)}" aria-selected="${this.selected.has(item.thread)}">
					<label class="om-pick" title="${__("Select")}"><input type="checkbox" ${this.selected.has(item.thread) ? "checked" : ""}></label>
					${this.face(item.sender_name, item.sender, item.face)}
					<div class="om-row-text">
						<div class="om-row-top"><span class="om-who">${esc(this.who(item))}</span>${count}<span class="om-when">${clip}${esc(this.when(item.date))}</span></div>
						<div class="om-subject">${esc(item.subject || __("(no subject)"))}</div>
						<div class="om-snippet">${esc(item.snippet || "")}</div>
					</div>
					<button class="om-star${item.flagged ? " om-starred" : ""}" data-star title="${item.flagged ? __("Unstar") : __("Star")}">${frappe.utils.icon("star", "sm")}</button>
				</div>`;
			})
			.join("");
		const more = this.more ? `<button class="es-button om-more" data-variant="subtle" data-act="more">${__("Show older")}</button>` : "";
		this.$items.html(rows + more);
		this.draw_picked();
	}

	draw_picked() {
		const count = this.selected.size;
		this.$root.find(".om-picked").prop("hidden", !count);
		this.$root.find(".om-list-head").prop("hidden", !!count);
		this.$root.find(".om-picked-count").text(__("{0} selected", [count]));
	}

	// ---------------------------------------------------------------- reading

	draw_reading() {
		if (this.thread) return;
		this.$read.html(`<div class="om-empty">${frappe.utils.icon("mail-open", "lg")}<p>${__("Choose a conversation to read it.")}</p></div>`);
	}

	async open(thread, { quiet = false } = {}) {
		if (!this.box) return;
		this.thread = thread;
		this.$items.find(".om-open").removeClass("om-open");
		this.$items.find(`.om-row[data-thread="${CSS.escape(thread)}"]`).addClass("om-open");
		if (!quiet) this.place();
		const answer = await frappe.xcall(OneMail.API + "conversation", { account: this.box.name, thread });
		if (this.thread !== thread) return;
		this.messages = answer.messages || [];
		if (!this.messages.length) {
			this.thread = null;
			this.place();
			return this.draw_reading();
		}
		this.draw_conversation();
		const unread = this.messages.filter((one) => !one.seen).map((one) => one.name);
		if (unread.length && !quiet) {
			await frappe.xcall(OneMail.ACT + "mark", { names: unread, seen: 1 });
			this.messages.forEach((one) => (one.seen = 1));
			const item = this.items.find((one) => one.thread === thread);
			if (item) item.unread = 0;
			this.$items.find(`.om-row[data-thread="${CSS.escape(thread)}"]`).removeClass("om-unread");
		}
	}

	draw_conversation() {
		const esc = frappe.utils.escape_html;
		// A conversation is called what it was first called.
		const first = this.messages[0];
		const flagged = this.messages.some((one) => one.one_flagged);
		const bare = (act, name, label, more = "") =>
			`<button class="es-button" data-variant="ghost" data-icon-button="true" data-act="${act}" title="${label}" aria-label="${label}" ${more}>${frappe.utils.icon(name, "sm")}</button>`;
		const messages = this.messages
			.map((message, at) => {
				const folded = at < this.messages.length - 1 && message.seen && !this.unfolded?.has(message.name);
				return folded ? this.draw_folded(message) : this.draw_message(message);
			})
			.join("");
		this.$read.html(`<div class="om-conv-head">
				<h2 class="om-conv-subject">${esc(first.subject || __("(no subject)"))}</h2>
				<div class="om-conv-actions">
					${bare("reply", "reply", __("Reply"))}
					${bare("reply-all", "reply-all", __("Reply all"))}
					${bare("forward", "forward", __("Forward"))}
					<span class="om-sep"></span>
					${bare("conv-star", "star", flagged ? __("Unstar") : __("Star"), flagged ? 'data-state="on"' : "")}
					${bare("conv-unread", "mail", __("Mark as unread"))}
					${bare("conv-move", "folder-input", __("Move to"))}
					${bare("conv-archive", "archive", __("Archive"))}
					${bare("conv-delete", "trash-2", __("Delete"))}
					<span class="om-sep"></span>
					${bare("file-on", "link", __("File on a record"))}
				</div>
				<div class="om-records"></div>
			</div>
			<div class="om-messages">${messages}</div>
			<div class="om-answer">
				<button class="es-button" data-variant="subtle" data-act="reply">${frappe.utils.icon("reply", "sm")}<span class="es-button__label">${__("Reply")}</span></button>
				<button class="es-button" data-variant="subtle" data-act="reply-all">${frappe.utils.icon("reply-all", "sm")}<span class="es-button__label">${__("Reply all")}</span></button>
				<button class="es-button" data-variant="subtle" data-act="forward">${frappe.utils.icon("forward", "sm")}<span class="es-button__label">${__("Forward")}</span></button>
			</div>`);
		this.$read.find(".om-body").each((_, frame) => this.fill(frame));
		this.draw_records();
		this.$read.scrollTop(0);
		const open = this.$read.find(".om-message:not(.om-folded)").first()[0];
		if (open && this.messages.length > 1) open.scrollIntoView({ block: "start" });
	}

	// The records the conversation is filed on, but its contacts, each with
	// a way to take it off.
	async draw_records() {
		const thread = this.thread;
		const rows = await frappe.xcall("onedesk.one_mail.linking.links_of", { names: this.messages.map((one) => one.name) });
		if (thread !== this.thread) return;
		const esc = frappe.utils.escape_html;
		this.$read.find(".om-records").html(
			rows
				.map(
					(row) => `<span class="om-record-chip" title="${esc([row.link_title, OneMail.FILED_BY[row.one_linked_by || "contact"]].filter(Boolean).join(" · "))}">
						<a href="/app/${frappe.router.slug(row.link_doctype)}/${encodeURIComponent(row.link_name)}">${esc(__(row.link_doctype))} ${esc(row.link_name)}</a>
						<button data-act="unfile" data-doctype="${esc(row.link_doctype)}" data-name="${esc(row.link_name)}" title="${__("Take off this record")}" aria-label="${__("Take off this record")}">${frappe.utils.icon("x", "xs")}</button>
					</span>`
				)
				.join("")
		);
	}

	file_on() {
		const dialog = new frappe.ui.Dialog({
			title: __("File on a record"),
			fields: [
				{
					fieldname: "doctype",
					fieldtype: "Autocomplete",
					label: __("Kind of record"),
					reqd: 1,
					options: (onedesk.record_mail ? onedesk.record_mail.DOCTYPES : ["Customer", "Supplier", "Lead"]).map((one) => ({ value: one, label: __(one) })),
				},
				{ fieldname: "docname", fieldtype: "Dynamic Link", options: "doctype", label: __("Record"), reqd: 1 },
			],
			primary_action_label: __("File"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one_mail.linking.file", {
					names: this.messages.map((one) => one.name),
					doctype: values.doctype,
					docname: values.docname,
				});
				dialog.hide();
				this.draw_records();
			},
		});
		dialog.show();
	}

	draw_folded(message) {
		const esc = frappe.utils.escape_html;
		return `<div class="om-message om-folded" data-message="${esc(message.name)}" tabindex="0">
			${this.face(message.sender_full_name, message.sender, message.face)}
			<span class="om-from-name">${esc(message.sender_full_name || message.sender)}</span>
			<span class="om-folded-text">${esc(message.snippet || "")}</span>
			<span class="om-when">${esc(this.when(message.communication_date))}</span>
		</div>`;
	}

	draw_message(message) {
		const esc = frappe.utils.escape_html;
		const people = (label, list) => (list ? `<div class="om-to"><span>${label}</span> ${esc(list)}</div>` : "");
		const files = (message.attachments || [])
			.map(
				(file) => `<span class="om-file">
					<a class="om-file-open" href="${esc(file.file_url)}" target="_blank" rel="noopener" title="${esc(file.file_name)}">
						${frappe.utils.icon("paperclip", "sm")}<span class="om-file-name">${esc(file.file_name)}</span>
						<span class="om-file-size">${esc(this.size_text(file.file_size))}</span>
					</a>
					<button class="om-file-save" data-act="save-file" data-file="${esc(file.name)}" title="${__("Save to My Files")}" aria-label="${__("Save to My Files")}">${frappe.utils.icon("folder-down", "sm")}</button>
				</span>`
			)
			.join("");
		return `<div class="om-message" data-message="${esc(message.name)}">
			<div class="om-message-head">
				${this.face(message.sender_full_name, message.sender, message.face)}
				<div class="om-from">
					<div><span class="om-from-name">${esc(message.sender_full_name || message.sender)}</span> <span class="om-from-address">${message.sender_full_name ? esc(`<${message.sender}>`) : ""}</span></div>
					${people(__("To"), message.recipients)}
					${people(__("Cc"), message.cc)}
				</div>
				<span class="om-when" title="${esc(this.when(message.communication_date, true))}">${esc(this.when(message.communication_date))}</span>
			</div>
			<div class="om-pictures" hidden>
				${frappe.utils.icon("image-off", "sm")}<span>${__("Pictures from elsewhere are not shown, so the sender cannot tell you opened this.")}</span>
				<button class="es-button" data-variant="subtle" data-act="pictures">${__("Show pictures")}</button>
			</div>
			<iframe class="om-body" sandbox="allow-popups allow-popups-to-escape-sandbox allow-same-origin" referrerpolicy="no-referrer" title="${__("Message")}"></iframe>
			${files ? `<div class="om-files">${files}</div>` : ""}
		</div>`;
	}

	// The message, made safe to show: no scripts, links open elsewhere, and
	// pictures from elsewhere held back until asked for.
	fill(frame) {
		const name = $(frame).closest(".om-message").attr("data-message");
		const message = this.messages.find((one) => one.name === name);
		if (!message) return;
		const doc = new DOMParser().parseFromString(message.content || "", "text/html");
		doc.querySelectorAll("script, iframe, object, embed, form, meta[http-equiv], link[rel=import]").forEach((el) => el.remove());
		doc.querySelectorAll("*").forEach((el) => {
			for (const attr of [...el.attributes]) if (/^on/i.test(attr.name)) el.removeAttribute(attr.name);
		});
		const allowed = this.pictures.has(message.name);
		let held = 0;
		doc.querySelectorAll("img[src], img[srcset], [background]").forEach((el) => {
			const src = el.getAttribute("src") || el.getAttribute("background") || "";
			if (/^(https?:)?\/\//i.test(src) && !src.startsWith(location.origin)) {
				if (!allowed) {
					el.removeAttribute("src");
					el.removeAttribute("srcset");
					el.removeAttribute("background");
					held++;
				}
			}
		});
		const pictures = allowed ? "https: http:" : "";
		const head = `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' data: ${pictures}; style-src 'unsafe-inline'; font-src 'self' data:">
			<base target="_blank">
			<style>
				html { color-scheme: light; }
				body { margin: 0; font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #171717; overflow-wrap: anywhere; }
				img { max-width: 100%; height: auto; }
				blockquote { margin: 0 0 0 .6em; padding-left: .8em; border-left: 3px solid #e2e2e2; color: #525252; }
				pre { white-space: pre-wrap; }
				table { max-width: 100%; }
			</style>`;
		frame.srcdoc = `<!doctype html><html><head>${head}</head><body dir="auto">${doc.body ? doc.body.innerHTML : ""}</body></html>`;
		$(frame).siblings(".om-pictures").prop("hidden", !held);
		frame.onload = () => {
			// As tall as the message: measured from a frame too short to hold
			// it, since a frame's document is never shorter than the frame.
			const size = () => {
				const inner = frame.contentDocument && frame.contentDocument.documentElement;
				if (!inner) return;
				frame.style.height = "1px";
				frame.style.height = `${inner.scrollHeight + 2}px`;
			};
			size();
			// Pictures that arrive later make it taller.
			frame.contentDocument?.querySelectorAll("img").forEach((img) => img.addEventListener("load", size));
		};
	}

	// ---------------------------------------------------------------- doing

	picked_items() {
		return this.items.filter((one) => this.selected.has(one.thread));
	}

	// Reading and starring are for a whole conversation; moving and deleting
	// take only its messages in the open folder, not the replies in Sent.
	names(threads, here = false) {
		return frappe.xcall(OneMail.API + "names", {
			account: this.box.name,
			threads,
			folder: here && !this.search && this.folder ? this.folder.name : null,
		});
	}

	async act(method, args, threads) {
		const names = await this.names(threads);
		if (names.length) await frappe.xcall(OneMail.ACT + method, { names, ...args });
	}

	async run(what, threads) {
		if (!threads.length || !this.box) return;
		const folder_of = (kind) => this.box.folders.find((one) => one.kind === kind);
		try {
			if (what === "read" || what === "unread") await this.act("mark", { seen: what === "read" ? 1 : 0 }, threads);
			else if (what === "star" || what === "unstar") await this.act("star", { flagged: what === "star" ? 1 : 0 }, threads);
			else if (what === "archive") {
				const archive = folder_of("Archive");
				if (!archive) return frappe.show_alert({ message: __("This mailbox has no Archive folder."), indicator: "orange" });
				await this.move_to(threads, archive.name);
			} else if (what === "delete") await this.delete(threads);
			else if (what.startsWith("move:")) await this.move_to(threads, what.slice(5));
		} finally {
			if (["archive", "delete"].includes(what) || what.startsWith("move:")) {
				if (threads.includes(this.thread)) {
					this.thread = null;
					this.place();
					this.draw_reading();
				}
				this.selected.clear();
			}
			this.refresh();
		}
	}

	async move_to(threads, folder) {
		const names = await this.names(threads, true);
		if (names.length) await frappe.xcall(OneMail.ACT + "move", { names, folder });
	}

	async delete(threads) {
		const names = await this.names(threads, true);
		if (!names.length) return;
		if (this.folder && this.folder.kind === "Trash" && !this.search) {
			const sure = await new Promise((yes) =>
				frappe.confirm(__("Delete these messages for good? This cannot be undone."), () => yes(true), () => yes(false))
			);
			if (!sure) return;
		}
		await frappe.xcall(OneMail.ACT + "delete", { names });
	}

	menu_of_folders(anchor, on_pick) {
		this.close_menu();
		const esc = frappe.utils.escape_html;
		const rows = this.box.folders
			.filter((one) => !this.folder || one.name !== this.folder.name)
			.map((one) => {
				const [name] = OneMail.KINDS[one.kind] || OneMail.KINDS.Other;
				return `<button class="om-menu-item" data-folder="${esc(one.name)}" style="--depth:${this.depth(one)}">${frappe.utils.icon(name, "sm")}<span>${esc(this.folder_label(one))}</span></button>`;
			})
			.join("");
		const rect = anchor.getBoundingClientRect();
		this.$menu = $(`<div class="om-menu" role="menu">${rows}</div>`).appendTo(document.body);
		const width = this.$menu.outerWidth();
		const left = Math.min(rect.left, window.innerWidth - width - 8);
		this.$menu.css({ top: rect.bottom + 4, left: Math.max(8, left) });
		this.$menu.on("click", ".om-menu-item", (e) => {
			const folder = e.currentTarget.dataset.folder;
			this.close_menu();
			on_pick(folder);
		});
		setTimeout(() => $(document).on("mousedown.om-menu", (e) => !$(e.target).closest(".om-menu").length && this.close_menu()));
	}

	close_menu() {
		if (!this.$menu) return;
		this.$menu.remove();
		this.$menu = null;
		$(document).off("mousedown.om-menu");
	}

	// ---------------------------------------------------------------- writing

	sender() {
		// What to write from: the open mailbox if it sends, else the
		// workspace's, else any the reader holds that sends.
		const sends = this.boxes.filter((one) => one.sends);
		const pick = (this.box && this.box.sends && this.box) || sends.find((one) => one.workspace) || sends[0];
		return pick ? pick.email : null;
	}

	write({ reply = false, all = false, forward = false } = {}) {
		const sender = this.sender();
		if (!sender) return frappe.msgprint(__("None of your mailboxes can send. Connect one that does."));
		const done = () => setTimeout(() => this.refresh(), 1500);
		if (!reply && !forward) {
			const composer = new frappe.views.CommunicationComposer({ sender, title: __("New message") });
			composer.dialog.$wrapper.on("hidden.bs.modal", done);
			return;
		}
		const message = this.messages[this.messages.length - 1];
		const subject = message.subject || "";
		const record = this.messages.find((one) => one.reference_doctype && one.reference_name);
		const doc = record ? { doctype: record.reference_doctype, name: record.reference_name } : undefined;
		let composer;
		if (forward) {
			const esc = frappe.utils.escape_html;
			const header = `<p><br></p><p>${__("Forwarded message")}<br>${__("From")}: ${esc(message.sender)}<br>${__("Date")}: ${esc(this.when(message.communication_date, true))}<br>${__("Subject")}: ${esc(subject)}<br>${__("To")}: ${esc(message.recipients || "")}</p>`;
			composer = new frappe.views.CommunicationComposer({
				sender,
				doc,
				subject: /^fwd?:/i.test(subject) ? subject : `Fwd: ${subject}`,
				forward: true,
				message: header + `<blockquote>${message.content || ""}</blockquote>`,
			});
		} else {
			const mine = this.boxes.map((one) => one.email.toLowerCase());
			const others = (list) =>
				(list || "")
					.split(",")
					.map((one) => one.trim())
					.filter((one) => one && !mine.some((me) => one.toLowerCase().includes(me)));
			const from_me = mine.includes((message.sender || "").toLowerCase());
			const recipients = from_me ? message.recipients : message.sender;
			const cc = all ? [...others(message.recipients), ...others(message.cc)].filter((one) => !recipients.includes(one)).join(", ") : "";
			composer = new frappe.views.CommunicationComposer({
				sender,
				doc,
				subject: /^re:/i.test(subject) ? subject : `Re: ${subject}`,
				recipients,
				cc,
				is_a_reply: true,
				last_email: message,
			});
		}
		composer.dialog.$wrapper.on("hidden.bs.modal", done);
	}

	connect() {
		const admin = frappe.user.has_role("Workspace Administrator");
		const dialog = new frappe.ui.Dialog({
			title: __("Connect a mailbox"),
			fields: [
				{ fieldname: "email", fieldtype: "Data", options: "Email", label: __("Address"), reqd: 1 },
				{
					fieldname: "password",
					fieldtype: "Password",
					label: __("Password"),
					reqd: 1,
					description: __("Gmail and Outlook want an app password here, made in the account's security settings."),
				},
				{ fieldname: "sends", fieldtype: "Check", label: __("Send from it too"), default: 1 },
				{
					fieldname: "shared",
					fieldtype: "Check",
					label: __("For the workspace"),
					hidden: !admin,
					description: __("A mailbox such as sales@ that belongs to the workspace. You choose who holds it."),
				},
				{ fieldtype: "Section Break", label: __("Server"), collapsible: 1 },
				{ fieldname: "login", fieldtype: "Data", label: __("Login, if not the address") },
				{ fieldname: "email_server", fieldtype: "Data", label: __("IMAP server") },
				{ fieldname: "incoming_port", fieldtype: "Int", label: __("IMAP port") },
				{ fieldname: "use_ssl", fieldtype: "Check", label: __("SSL"), default: 1 },
				{ fieldtype: "Column Break" },
				{ fieldname: "smtp_server", fieldtype: "Data", label: __("SMTP server") },
				{ fieldname: "smtp_port", fieldtype: "Int", label: __("SMTP port") },
			],
			primary_action_label: __("Connect"),
			primary_action: async (values) => {
				dialog.get_primary_btn().prop("disabled", true);
				try {
					const account = await frappe.xcall("onedesk.one_mail.connect.connect", values);
					dialog.hide();
					frappe.show_alert({ message: __("Connected. Its mail is on its way."), indicator: "green" });
					await this.load_to(account);
				} finally {
					dialog.get_primary_btn().prop("disabled", false);
				}
			},
		});
		dialog.show();
	}

	async load_to(account) {
		history.replaceState(null, "", `${location.pathname}?box=${encodeURIComponent(account)}`);
		await this.load();
	}

	// ---------------------------------------------------------------- hands

	bind() {
		const $root = this.$root;
		$root.on("click", ".om-box-head", (e) => {
			const name = e.currentTarget.dataset.toggle;
			this.closed.has(name) ? this.closed.delete(name) : this.closed.add(name);
			this.draw_boxes();
		});
		$root.on("click", ".om-folder", (e) => this.choose(e.currentTarget.dataset.box, e.currentTarget.dataset.folder));
		$root.on("click", ".om-row", (e) => {
			if ($(e.target).closest(".om-pick, [data-star]").length) return;
			const thread = e.currentTarget.dataset.thread;
			if (e.shiftKey || e.metaKey || e.ctrlKey) return this.toggle(thread, e.shiftKey);
			this.selected.clear();
			this.draw_picked();
			this.$items.find(".om-picked-row").removeClass("om-picked-row").find("input").prop("checked", false);
			this.open(thread);
		});
		$root.on("change", ".om-pick input", (e) => this.toggle($(e.target).closest(".om-row").attr("data-thread"), false));
		$root.on("click", "[data-star]", (e) => {
			const thread = $(e.target).closest(".om-row").attr("data-thread");
			const item = this.items.find((one) => one.thread === thread);
			if (item) this.run(item.flagged ? "unstar" : "star", [thread]);
		});
		$root.on("click", ".om-folded", (e) => {
			(this.unfolded = this.unfolded || new Set()).add(e.currentTarget.dataset.message);
			this.draw_conversation();
		});
		$root.on("click", "[data-act]", (e) => {
			const act = e.currentTarget.dataset.act;
			const picked = [...this.selected];
			const open = this.thread ? [this.thread] : [];
			const now = {
				write: () => this.write(),
				connect: () => this.connect(),
				refresh: () => this.refresh(),
				more: () => this.list({ more: true, keep: true }),
				clear: () => {
					this.selected.clear();
					this.draw_list();
				},
				read: () => this.run("read", picked),
				unread: () => this.run("unread", picked),
				star: () => this.run(this.picked_items().every((one) => one.flagged) ? "unstar" : "star", picked),
				archive: () => this.run("archive", picked),
				delete: () => this.run("delete", picked),
				move: () => this.menu_of_folders(e.currentTarget, (folder) => this.run(`move:${folder}`, picked)),
				reply: () => this.write({ reply: true }),
				"reply-all": () => this.write({ reply: true, all: true }),
				forward: () => this.write({ forward: true }),
				"conv-star": () => this.run(this.messages.some((one) => one.one_flagged) ? "unstar" : "star", open),
				"conv-unread": () => this.run("unread", open).then(() => {
					this.thread = null;
					this.place();
					this.draw_reading();
				}),
				"conv-move": () => this.menu_of_folders(e.currentTarget, (folder) => this.run(`move:${folder}`, open)),
				"conv-archive": () => this.run("archive", open),
				"conv-delete": () => this.run("delete", open),
				"file-on": () => this.file_on(),
				unfile: async () => {
					await frappe.xcall("onedesk.one_mail.linking.unfile", {
						names: this.messages.map((one) => one.name),
						doctype: e.currentTarget.dataset.doctype,
						docname: e.currentTarget.dataset.name,
					});
					this.draw_records();
				},
				"save-file": async () => {
					await frappe.xcall("onedesk.one_storage.api.copy", { nodes: [e.currentTarget.dataset.file], target: "@my" });
					frappe.show_alert({ message: __("Saved to My Files."), indicator: "green" });
				},
				"box-files": () => frappe.set_route("onecloud", { node: `@mail/${this.box.name}` }),
				pictures: () => {
					const name = $(e.currentTarget).closest(".om-message").attr("data-message");
					this.pictures.add(name);
					this.fill($(e.currentTarget).closest(".om-message").find(".om-body")[0]);
				},
			}[act];
			if (now) now();
		});
		this.$search.on(
			"input",
			frappe.utils.debounce(() => {
				this.search = this.$search.val().trim();
				this.draw_boxes();
				this.list();
			}, 300)
		);
		$root.on("keydown", (e) => this.key(e));
		window.addEventListener("popstate", () => {
			if (!this.$root.is(":visible")) return;
			const want = this.wanted();
			if (this.box && want.box === this.box.name && this.folder && want.folder === this.folder.name) {
				if (want.thread && want.thread !== this.thread) this.open(want.thread, { quiet: true });
				else if (!want.thread) {
					this.thread = null;
					this.draw_reading();
				}
			} else this.load();
		});
	}

	toggle(thread, range) {
		if (range && this.anchor) {
			const at = this.items.findIndex((one) => one.thread === this.anchor);
			const to = this.items.findIndex((one) => one.thread === thread);
			const [low, high] = at < to ? [at, to] : [to, at];
			this.items.slice(low, high + 1).forEach((one) => this.selected.add(one.thread));
		} else if (this.selected.has(thread)) this.selected.delete(thread);
		else this.selected.add(thread);
		this.anchor = thread;
		this.draw_list();
	}

	// j and k move, e archives, # deletes, r replies, a replies to all, f
	// forwards, s stars, u marks unread, c writes and / searches, as in most
	// mail clients.
	key(e) {
		if ($(e.target).is("input, textarea, [contenteditable]") || e.metaKey || e.ctrlKey || e.altKey) {
			if (e.key === "Escape" && $(e.target).is(this.$search)) this.$search.blur();
			return;
		}
		const at = this.items.findIndex((one) => one.thread === this.thread);
		const open = this.thread ? [this.thread] : [];
		const go = (step) => {
			const next = this.items[Math.min(this.items.length - 1, Math.max(0, at + step))];
			if (next) {
				this.open(next.thread);
				this.$items.find(`.om-row[data-thread="${CSS.escape(next.thread)}"]`)[0]?.scrollIntoView({ block: "nearest" });
			}
		};
		const keys = {
			j: () => go(1),
			k: () => go(-1),
			ArrowDown: () => go(1),
			ArrowUp: () => go(-1),
			e: () => this.run("archive", this.selected.size ? [...this.selected] : open),
			"#": () => this.run("delete", this.selected.size ? [...this.selected] : open),
			Delete: () => this.run("delete", this.selected.size ? [...this.selected] : open),
			r: () => this.thread && this.write({ reply: true }),
			a: () => this.thread && this.write({ reply: true, all: true }),
			f: () => this.thread && this.write({ forward: true }),
			s: () => this.thread && this.run(this.messages.some((one) => one.one_flagged) ? "unstar" : "star", open),
			u: () => this.thread && this.run("unread", open),
			c: () => this.write(),
			"/": () => this.$search.focus(),
			Escape: () => {
				this.selected.clear();
				this.draw_list();
			},
		};
		const run = keys[e.key];
		if (!run) return;
		e.preventDefault();
		run();
	}
};
