// The explorer: every file a person may reach, laid out the way everybody
// already knows — a folder tree on the left, an address bar with back, forward
// and up, the folder's contents as details or tiles, a preview on the right,
// and a status bar underneath.
//
// It draws and never decides. Every list and every change is a call to
// one_storage/api.py, which asks namespace.may first; a button that is shown
// but refused says why in the server's words. Uploads go from this browser to
// R2 directly (one_storage/upload.py signs them), so a large file costs this
// server two small requests.
//
// The place is in the address (?node=…), so the browser's own back button,
// a bookmark and a link somebody pastes all land in the same folder.
//
// Two hosts: the OneCloud page (page/onecloud), and a record's Files tab
// (record_files.js), which opens it on one record's room with no tree and
// no address of its own. Either loads this file when first opened.

frappe.provide("onedesk");

onedesk.OneCloud = class OneCloud {
	static API = "onedesk.one_storage.api.";
	static UPLOAD = "onedesk.one_storage.upload.";
	static KINDS = [
		[["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "heic", "avif", "ico"], "file-image", __("Image")],
		[["pdf"], "file-text", __("PDF document")],
		[["doc", "docx", "odt", "rtf"], "file-text", __("Document")],
		[["txt", "md"], "file-text", __("Text document")],
		[["xls", "xlsx", "ods", "csv", "tsv"], "file-spreadsheet", __("Spreadsheet")],
		[["ppt", "pptx", "odp", "key"], "presentation", __("Presentation")],
		[["mp4", "mov", "webm", "mkv", "avi", "m4v"], "file-play", __("Video")],
		[["mp3", "wav", "ogg", "m4a", "flac", "aac"], "file-music", __("Audio")],
		[["zip", "rar", "7z", "tar", "gz", "tgz"], "file-archive", __("Compressed folder")],
		[["js", "ts", "py", "json", "html", "css", "xml", "sh", "yml", "yaml", "sql"], "file-code", __("Code")],
	];
	static PREVIEW_IMAGE = ["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "avif", "ico"];
	static PREVIEW_FRAME = ["pdf", "txt", "md", "csv", "tsv", "json", "xml", "html", "css", "js", "py", "yml", "yaml", "sql", "sh"];
	static PREVIEW_VIDEO = ["mp4", "webm", "mov", "m4v"];
	static PREVIEW_AUDIO = ["mp3", "wav", "ogg", "m4a", "flac", "aac"];

	// `room`: a record's node, for the Files tab — the explorer opens there,
	// stays there, and draws into `parent` rather than a page of its own.
	// `picker`: the upload dialog's OneCloud (one_storage/public/js/
	// onecloud_picker.js) — it walks anywhere without the address, changes
	// nothing, and a file opened is a file chosen: {start, on_pick, on_select}.
	constructor(page, { room = null, parent = null, listed = null, picker = null } = {}) {
		this.page = page;
		this.room = room;
		this.picker = picker;
		this.parent = parent;
		this.listed = listed;
		this.node = null;
		this.items = [];
		this.trail = [];
		this.selected = new Set();
		this.anchor = null;
		this.focus_id = null;
		this.clipboard = null;
		this.search = "";
		this.past = [];
		this.ahead = [];
		this.kids = {};
		this.open_in_tree = new Set(["@my", "@company"]);
		this.settings = { view: "details", sort: "name", asc: 1, preview: 1 };
		this.build();
		this.bind();
		if (!this.room) $(window).on("resize.onecloud", frappe.utils.debounce(() => this.fit(), 100));
		this.listen();
		frappe.model.user_settings.get("File").then((kept) => {
			Object.assign(this.settings, (kept && kept.OneCloud) || {});
			this.apply_settings();
			this.ready = true;
			this.show();
		});
	}

	// ------------------------------------------------------------- the frame

	build() {
		const icon = (name) => frappe.utils.icon(name, "sm");
		const button = (act, name, label, more = "") =>
			`<button class="es-button" data-variant="ghost" data-act="${act}" title="${label}" ${more}>${icon(name)}<span class="es-button__label">${label}</span></button>`;
		const bare = (act, name, label) =>
			`<button class="es-button" data-variant="ghost" data-icon-button="true" data-act="${act}" title="${label}" aria-label="${label}">${icon(name)}</button>`;
		this.$root = $(`<div class="oc${this.room ? " oc-room" : ""}${this.picker ? " oc-pick" : ""}" tabindex="-1">
			<div class="oc-bar">
				<button class="es-button" data-variant="solid" data-act="new-menu">${icon("plus")}<span class="es-button__label">${__("New")}</span>${icon("chevron-down")}</button>
				<span class="oc-sep"></span>
				${bare("cut", "scissors", __("Cut"))}
				${bare("copy", "copy", __("Copy"))}
				${bare("paste", "clipboard-paste", __("Paste"))}
				${bare("rename", "pencil", __("Rename"))}
				${bare("share", "user-plus", __("Share"))}
				${bare("download", "download", __("Download"))}
				${bare("delete", "trash-2", __("Delete"))}
				<span class="oc-sep oc-in-bin"></span>
				${button("restore", "rotate-ccw", __("Restore"), 'data-bin="1"')}
				${button("empty-bin", "trash-2", __("Empty Recycle Bin"), 'data-bin="1"')}
				${button("open-record", "external-link", __("Open record"), 'data-record="1"')}
				${button("members", "users", __("Members"), 'data-library="1"')}
				<span class="oc-grow"></span>
				${bare("view-details", "layout-list", __("Details"))}
				${bare("view-tiles", "layout-grid", __("Tiles"))}
				${bare("toggle-preview", "panel-right", __("Preview pane"))}
			</div>
			<div class="oc-address">
				${bare("back", "arrow-left", __("Back"))}
				${bare("forward", "arrow-right", __("Forward"))}
				${bare("up", "arrow-up", __("Up"))}
				<nav class="oc-crumbs es-breadcrumbs"><ol></ol></nav>
				${bare("refresh", "refresh-cw", __("Refresh"))}
				<label class="oc-search">${icon("search")}<input type="search" spellcheck="false"></label>
			</div>
			<div class="oc-body">
				<nav class="oc-tree" aria-label="${__("Folders")}"></nav>
				<div class="oc-main">
					<div class="oc-head">
						<button data-sort="name">${__("Name")}</button>
						<button data-sort="where" class="oc-col-where">${__("Folder")}</button>
						<button data-sort="modified" class="oc-col-date">${__("Date modified")}</button>
						<button data-sort="type" class="oc-col-type">${__("Type")}</button>
						<button data-sort="size" class="oc-col-size">${__("Size")}</button>
					</div>
					<div class="oc-scope" hidden></div>
					<div class="oc-items" tabindex="0" role="listbox" aria-multiselectable="true"></div>
				</div>
				<aside class="oc-preview"></aside>
			</div>
			<div class="oc-status"></div>
			<input type="file" class="oc-pick-files" multiple hidden>
			<input type="file" class="oc-pick-folder" webkitdirectory hidden>
			<input type="file" class="oc-pick-version" hidden>
			<div class="oc-uploads" hidden></div>
		</div>`).appendTo(this.parent || this.page.main);
		this.$items = this.$root.find(".oc-items");
		this.$tree = this.$root.find(".oc-tree");
		this.$preview = this.$root.find(".oc-preview");
		this.$search = this.$root.find(".oc-search input");
	}

	// To the bottom of the window from wherever the desk's header leaves it,
	// rather than a guess at how tall that header is.
	fit() {
		if (this.room || this.picker) return; // a tab's or a dialog's height is its stylesheet's
		const el = this.$root[0];
		if (!el || !el.offsetParent) return;
		const top = el.getBoundingClientRect().top + window.scrollY;
		el.style.height = `${Math.max(420, window.innerHeight - top)}px`;
	}

	apply_settings() {
		this.$root.attr("data-view", this.settings.view);
		this.$root.toggleClass("oc-no-preview", !cint(this.settings.preview));
		this.$root.find("[data-act=view-details]").attr("data-state", this.settings.view === "details" ? "on" : null);
		this.$root.find("[data-act=view-tiles]").attr("data-state", this.settings.view === "tiles" ? "on" : null);
		this.$root.find("[data-act=toggle-preview]").attr("data-state", cint(this.settings.preview) ? "on" : null);
		this.$root.find(".oc-head button").each((_, el) => {
			const on = el.dataset.sort === this.settings.sort;
			$(el).attr("data-sorted", on ? (cint(this.settings.asc) ? "asc" : "desc") : null);
		});
	}

	remember(change) {
		Object.assign(this.settings, change);
		this.apply_settings();
		frappe.model.user_settings.save("File", "OneCloud", this.settings);
	}

	// ------------------------------------------------------------- live

	// Somebody else's change to what is open: redraw, the way a list view
	// does. The server says which folders and records changed as keys
	// (one_storage/live.py); a listing says which keys it is watching.
	listen() {
		frappe.realtime.doctype_subscribe("File");
		const redraw = frappe.utils.debounce(() => this.redraw(), 600);
		frappe.realtime.on("onecloud_change", (data) => {
			const keys = (data && data.keys) || [];
			if (this.watch !== "*" && !keys.some((one) => (this.watch || []).includes(one))) return;
			// Hidden (another page, another tab of the form): on the next look.
			if (!this.$root.is(":visible")) return (this.stale = true);
			redraw();
		});
	}

	redraw() {
		// Not under somebody's hands: a menu open, a name being typed, a drag.
		if (this.$menu || this.dragging || this.$root.find("input.oc-rename, input.oc-path").length) {
			return setTimeout(() => this.redraw(), 1500);
		}
		this.forget_tree(this.node);
		this.refresh();
	}

	// ------------------------------------------------------------ where we are

	wanted() {
		if (this.picker) return this.node || this.picker.start || "@my";
		return this.room || frappe.utils.get_query_params().node || "@my";
	}

	// The Files tab moving to another record (the form is reused).
	enter(room) {
		if (room === this.room) return this.ready && this.refresh();
		this.room = room;
		this.past = [];
		this.ahead = [];
		this.set_search("");
		if (this.ready) this.open(room);
	}

	// Coming to the page, or the address changing under it.
	show() {
		this.fit();
		if (!this.ready) return;
		const node = this.wanted();
		if (node === this.node) return this.refresh();
		// The browser's own back and forward, kept in step with ours.
		if (this.past.length && this.past[this.past.length - 1] === node) {
			this.past.pop();
			this.node && this.ahead.push(this.node);
		} else if (this.ahead.length && this.ahead[this.ahead.length - 1] === node) {
			this.ahead.pop();
			this.node && this.past.push(this.node);
		} else if (this.node) {
			this.past.push(this.node);
			this.ahead = [];
		}
		this.open(node);
	}

	go(node) {
		if (node === this.node && !this.search) return;
		// The picker keeps its own history; the page's address is not its.
		if (this.picker) {
			this.node && this.past.push(this.node);
			this.ahead = [];
			this.set_search("");
			return this.open(node);
		}
		// A room is one record's files; anywhere else is the OneCloud page.
		if (this.room && node !== this.room) return frappe.set_route("onecloud", { node });
		this.set_search("");
		if (this.room) return this.refresh();
		frappe.set_route("onecloud", { node });
	}

	async open(node) {
		this.node = node;
		this.selected.clear();
		this.anchor = this.focus_id = null;
		await this.refresh();
		this.$items.trigger("focus");
	}

	async refresh() {
		const token = (this.asking = {});
		let answer;
		try {
			answer = await frappe.xcall(OneCloud.API + "listing", {
				node: this.node,
				search: this.search || null,
				everywhere: this.search && this.everywhere ? 1 : 0,
			});
		} catch (e) {
			if (token !== this.asking) return;
			if (this.node !== "@my") return this.go("@my");
			throw e;
		}
		if (token !== this.asking) return;
		this.items = answer.items || [];
		this.trail = answer.trail || [];
		this.watch = answer.watch || [];
		this.stale = false;
		this.can_add = !!answer.can_add;
		this.can_make_folder = !!answer.can_make_folder;
		this.can_make_library = !!answer.can_make_library;
		this.can_make_mount = !!answer.can_make_mount;
		const live = new Set(this.items.map((one) => one.id));
		this.selected = new Set([...this.selected].filter((id) => live.has(id)));
		this.draw();
		if (!this.room) this.draw_tree();
		if (this.listed) this.listed(this.items.length);
		if (this.reveal && live.has(this.reveal)) {
			this.pick(this.reveal, {});
			const el = this.$items.find(`.oc-item[data-id="${CSS.escape(this.reveal)}"]`)[0];
			el && el.scrollIntoView({ block: "nearest" });
		}
		this.reveal = null;
	}

	kind() {
		const node = this.node || "";
		if (node === "@bin") return "bin";
		if (node === "@shared") return "shared";
		if (node === "@root") return "root";
		if (node.startsWith("@records")) return node.split("/").length === 3 ? "record" : "records";
		if (node === "@libraries") return "libraries";
		if (node === "@recent") return "recent";
		if (node === "@starred") return "starred";
		if (node === "@mounts") return "network";
		if (node === "@requests") return "requests";
		if (node.startsWith("@request/")) return "request";
		if (node.startsWith("@mount/")) return "mount";
		return "folder";
	}

	// ------------------------------------------------------------- drawing

	draw() {
		const here = this.trail[this.trail.length - 1];
		this.draw_crumbs();
		this.fit();
		const global = this.everywhere || this.kind() === "root";
		this.$search.attr("placeholder", global ? __("Search everywhere") : __("Search {0}", [here ? here.name : __("Files")]));
		this.draw_scope(here);
		this.$root.attr("data-kind", this.kind());
		// Search results say which folder each is in; Shared with Me says who from.
		const where_head = { shared: __("Shared by"), libraries: __("Your role"), recent: __("Folder"), starred: __("Folder"), network: __("Kind"), requests: __("Progress"), request: __("File · From") }[this.kind()];
		this.$root.toggleClass("oc-searching", !!this.search || !!where_head);
		this.$root.find(".oc-head .oc-col-where").text(where_head && !this.search ? where_head : __("Folder"));
		if (this.kind() === "libraries") this.items.forEach((one) => (one.where = one.role ? __(one.role) : ""));
		this.$root.find(".oc-head .oc-col-date").text(this.kind() === "bin" ? __("Date deleted") : __("Date modified"));
		const sorted = this.sorted();
		if (!sorted.length) {
			this.$items.html(`<div class="oc-empty">${this.empty_text()}</div>`);
		} else {
			this.$items.html(sorted.map((item) => this.item_html(item)).join(""));
		}
		this.mark();
		this.draw_bar();
	}

	// While searching: where the results are from, and a way to widen or
	// narrow that, the way an explorer offers "search again in".
	draw_scope(here) {
		const $scope = this.$root.find(".oc-scope");
		const scoped = !!this.search && this.kind() !== "root" && !this.room;
		$scope.prop("hidden", !scoped);
		if (!scoped) return;
		const esc = frappe.utils.escape_html;
		const name = here ? here.name : __("Files");
		const said = this.everywhere ? __("Results from everywhere") : __("Results in {0}", [name]);
		const other = this.everywhere ? __("Only in {0}", [name]) : __("Search everywhere");
		$scope.html(`${frappe.utils.icon(this.everywhere ? "globe" : "folder-search", "sm")}<span>${esc(said)}</span><button type="button">${esc(other)}</button>`);
		$scope.find("button").on("click", () => {
			this.everywhere = !this.everywhere;
			this.refresh();
			this.$search.trigger("focus");
		});
	}

	empty_text() {
		if (this.search) return __("No items match your search.");
		const text = {
			bin: __("The Recycle Bin is empty."),
			shared: __("Files and folders people share with you will appear here."),
			records: __("No record has files yet."),
			recent: __("Files you open or add will appear here."),
			network: __("Connect an SFTP or WebDAV server to open its files here. Use New."),
			requests: __("Ask people for files by name, each landing in a folder or on a record. Use New › File request in any folder or record."),
			request: __("Nothing has arrived yet."),
			starred: __("Star a file or folder to find it here. Right-click it and choose Star."),
			libraries: __("You are not in any library yet. A library is a folder a team shares, with members who can read or edit it. Use New to make one."),
			root: "",
		}[this.kind()];
		if (text !== undefined) return text;
		return this.can_add
			? __("This folder is empty. Drop files here, or use New.")
			: __("This folder is empty.");
	}

	draw_crumbs() {
		const $ol = this.$root.find(".oc-crumbs ol").empty();
		this.trail.forEach((one) => {
			$(`<li><button class="es-breadcrumbs__item" data-node=""></button></li>`)
				.find("button")
				.attr("data-node", one.id)
				.text(one.name)
				.end()
				.appendTo($ol);
		});
		this.$root.find("[data-act=back]").prop("disabled", !this.past.length);
		this.$root.find("[data-act=forward]").prop("disabled", !this.ahead.length);
		this.$root.find("[data-act=up]").prop("disabled", this.trail.length < 2);
	}

	type_path() {
		const $crumbs = this.$root.find(".oc-crumbs");
		if ($crumbs.find("input").length) return;
		const path = this.trail
			.slice(1)
			.map((one) => one.name)
			.join("/");
		const $box = $(`<input class="oc-path" spellcheck="false">`).val(path);
		$crumbs.find("ol").hide();
		$crumbs.append($box);
		$box.trigger("focus").trigger("select");
		const done = () => {
			$box.remove();
			$crumbs.find("ol").show();
		};
		$box.on("keydown", async (e) => {
			e.stopPropagation();
			if (e.key === "Escape") return done();
			if (e.key !== "Enter") return;
			const typed = $box.val().trim();
			try {
				const node = await frappe.xcall(OneCloud.API + "resolve", { path: typed });
				done();
				this.go(node);
			} catch (error) {
				$box.trigger("select");
			}
		});
		$box.on("blur", done);
	}

	sorted() {
		const { sort } = this.settings;
		const way = cint(this.settings.asc) ? 1 : -1;
		const value = (item) => {
			if (sort === "size") return item.folder ? -1 : item.size || 0;
			if (sort === "modified") return (this.kind() === "bin" ? item.deleted : item.modified) || "";
			if (sort === "type") return this.type_of(item);
			if (sort === "where") return (item.where || "").toLowerCase();
			return (item.name || "").toLowerCase();
		};
		// The server's own order is kept where it means something: the roots,
		// and the records, newest file first.
		if (["root", "records"].includes(this.kind()) && sort === "name" && way === 1) return this.items.slice();
		return this.items.slice().sort((a, b) => {
			if (a.folder !== b.folder) return a.folder ? -1 : 1;
			const x = value(a),
				y = value(b);
			if (x < y) return -way;
			if (x > y) return way;
			return (a.name || "").localeCompare(b.name || "") * way;
		});
	}

	extension(item) {
		const name = item.name || "";
		const dot = name.lastIndexOf(".");
		return dot > 0 ? name.slice(dot + 1).toLowerCase() : "";
	}

	icon_of(item) {
		if (item.icon) return item.icon;
		if (item.folder) return item.record ? "folder-open" : "folder";
		const ext = this.extension(item);
		const found = OneCloud.KINDS.find(([exts]) => exts.includes(ext));
		return found ? found[1] : "file";
	}

	type_of(item) {
		if (item.virtual && item.doctype) return __("Record type");
		if (item.record && item.folder) return __("Record");
		if (String(item.id).startsWith("@request/")) return __("File request");
		if (item.folder) return __("File folder");
		const ext = this.extension(item);
		const found = OneCloud.KINDS.find(([exts]) => exts.includes(ext));
		if (found) return found[2];
		return ext ? __("{0} file", [ext.toUpperCase()]) : __("File");
	}

	size_text(bytes) {
		if (!bytes) return "";
		const units = [__("B"), __("KB"), __("MB"), __("GB"), __("TB")];
		let at = 0,
			value = bytes;
		while (value >= 1024 && at < units.length - 1) {
			value /= 1024;
			at++;
		}
		return `${value >= 10 || at === 0 ? Math.round(value) : value.toFixed(1)} ${units[at]}`;
	}

	// One of two sentences, the second with the number put in.
	count(n, one, many) {
		return n === 1 ? one : many.replace("{0}", n);
	}

	date_text(value) {
		if (!value) return "";
		const [day, time] = String(value).split(" ");
		return `${frappe.datetime.str_to_user(day)} ${(time || "").slice(0, 5)}`.trim();
	}

	item_html(item) {
		const esc = frappe.utils.escape_html;
		const when = this.kind() === "bin" ? item.deleted : item.modified;
		const picture =
			item.thumbnail || (!item.folder && OneCloud.PREVIEW_IMAGE.includes(this.extension(item)) && item.url && !item.url.startsWith("/api/"))
				? `<img loading="lazy" alt="" src="${esc(item.thumbnail || item.url)}">`
				: frappe.utils.icon(this.icon_of(item), "lg");
		const count = item.count ? `<span class="oc-count">${item.count}</span>` : "";
		const public_note = __("Anyone with the link can open this file");
		const open =
			item.private === false && !item.folder
				? `<span class="oc-public" title="${public_note}">${frappe.utils.icon("globe", "xs")}</span>`
				: "";
		const shared_note = __("Shared");
		const shared = item.shared ? `<span class="oc-shared" title="${shared_note}">${frappe.utils.icon("users", "xs")}</span>` : "";
		const star_note = __("Starred");
		const star = item.starred ? `<span class="oc-starred" title="${star_note}">${frappe.utils.icon("star", "xs")}</span>` : "";
		return `<div class="oc-item" role="option" draggable="true" data-id="${esc(item.id)}" data-folder="${item.folder ? 1 : 0}">
			<span class="oc-name"><span class="oc-picture">${picture}</span><span class="oc-label">${esc(item.name)}</span>${count}${star}${shared}${open}</span>
			<span class="oc-col-where">${esc(item.where || "")}</span>
			<span class="oc-col-date">${this.date_text(when)}</span>
			<span class="oc-col-type">${esc(this.type_of(item))}</span>
			<span class="oc-col-size">${item.folder ? "" : this.size_text(item.size)}</span>
		</div>`;
	}

	// Selection, focus and what was cut, drawn onto rows already there.
	mark() {
		const cut = this.clipboard && this.clipboard.mode === "cut" ? new Set(this.clipboard.ids) : new Set();
		this.$items.find(".oc-item").each((_, el) => {
			const id = el.dataset.id;
			el.setAttribute("aria-selected", this.selected.has(id) ? "true" : "false");
			el.classList.toggle("oc-focus", id === this.focus_id);
			el.classList.toggle("oc-cut", cut.has(id));
		});
		this.draw_status();
		this.draw_preview();
		this.draw_bar();
		if (this.picker && this.picker.on_select) this.picker.on_select(this.chosen().filter((one) => !one.folder));
	}

	chosen() {
		return this.items.filter((one) => this.selected.has(one.id));
	}

	// Backed by a File of ours: can be shared, starred, versioned. A server's
	// file is stored somewhere else, and only moved, copied and renamed.
	filed(item) {
		return this.stored(item) && !item.remote;
	}

	stored(item) {
		return item && !item.virtual;
	}

	draw_bar() {
		const chosen = this.chosen();
		const kind = this.kind();
		const all_stored = chosen.length && chosen.every((one) => this.stored(one));
		const set = (act, on) => this.$root.find(`[data-act=${act}]`).prop("disabled", !on);
		set("new-menu", this.can_add || this.can_make_library || this.can_make_mount || kind === "requests");
		this.$root.find("[data-library]").toggle(!!this.library_here());
		set("cut", all_stored && kind !== "bin");
		set("copy", all_stored && kind !== "bin");
		set("paste", this.can_add && !!this.clipboard);
		set("share", chosen.length === 1 && this.shareable(chosen[0]) && kind !== "bin");
		set("rename", chosen.length === 1 && this.stored(chosen[0]) && kind !== "bin" && kind !== "record");
		set("download", chosen.length && chosen.every((one) => !one.folder && one.url));
		set("delete", all_stored);
		set("restore", kind === "bin" && chosen.length);
		set("empty-bin", kind === "bin" && this.items.length);
		set("open-record", !!this.record_of(chosen[0]) || kind === "record");
		this.$root.find("[data-bin]").toggle(kind === "bin");
		this.$root.find("[data-record]").toggle(!this.room && (kind === "record" || kind === "records" || chosen.some((one) => one.record)));
	}

	draw_status() {
		const chosen = this.chosen();
		const count = this.items.length;
		let text = this.count(count, __("1 item"), __("{0} items"));
		if (chosen.length) {
			const bytes = chosen.reduce((sum, one) => sum + (one.folder ? 0 : one.size || 0), 0);
			text += "  ·  " + this.count(chosen.length, __("1 item selected"), __("{0} items selected"));
			if (bytes) text += "  " + this.size_text(bytes);
		}
		this.$root.find(".oc-status").text(text);
	}

	// ------------------------------------------------------------- preview

	draw_preview() {
		if (!cint(this.settings.preview)) return;
		const chosen = this.chosen();
		const esc = frappe.utils.escape_html;
		if (chosen.length !== 1) {
			const text = chosen.length
				? __("{0} items selected", [chosen.length])
				: __("Select a file to preview it.");
			this.$preview.html(`<div class="oc-preview-none">${text}</div>`);
			this.previewing = null;
			return;
		}
		const item = chosen[0];
		if (this.previewing === item.id) return;
		this.previewing = item.id;
		const ext = this.extension(item);
		let shown = `<div class="oc-preview-icon">${frappe.utils.icon(this.icon_of(item), "xl")}</div>`;
		if (!item.folder && item.url) {
			const src = esc(item.url);
			if (OneCloud.PREVIEW_IMAGE.includes(ext)) shown = `<img class="oc-preview-image" alt="" src="${src}">`;
			else if (OneCloud.PREVIEW_VIDEO.includes(ext)) shown = `<video controls preload="metadata" src="${src}"></video>`;
			else if (OneCloud.PREVIEW_AUDIO.includes(ext)) shown = `<audio controls preload="metadata" src="${src}"></audio>`;
			else if (OneCloud.PREVIEW_FRAME.includes(ext)) shown = `<iframe title="${esc(item.name)}" src="${src}" sandbox="allow-same-origin"></iframe>`;
		}
		const rows = [
			[__("Type"), this.type_of(item)],
			[__("Size"), item.folder ? "" : this.size_text(item.size)],
			[__("Modified"), this.date_text(item.modified)],
			[__("Deleted"), this.date_text(item.deleted)],
			[String(item.id).startsWith("@request/") ? __("Progress") : __("Folder"), item.where],
			[__("Owner"), item.owner ? frappe.user.full_name(item.owner) : ""],
			[__("Record"), item.record ? `${__(item.record[0])} ${item.record[1]}` : ""],
		].filter(([, value]) => value);
		this.$preview.html(`
			<div class="oc-preview-shown">${shown}</div>
			<div class="oc-preview-name">${esc(item.name)}</div>
			<dl>${rows.map(([key, value]) => `<dt>${key}</dt><dd>${esc(String(value))}</dd>`).join("")}</dl>
			<div class="oc-history"></div>`);
		if (this.filed(item)) this.draw_history(item);
	}

	// A file's versions and what was done to it, under its preview.
	async draw_history(item) {
		let found;
		try {
			found = await frappe.xcall("onedesk.one_storage.history.activity", { node: item.id });
		} catch (e) {
			return;
		}
		if (this.previewing !== item.id) return;
		const esc = frappe.utils.escape_html;
		const versions_head = __("Versions");
		const activity_head = __("Activity");
		const current = __("Current");
		const open = __("Open");
		const restore = __("Restore");
		const versions = found.versions.length
			? `<div class="oc-history-head">${versions_head}</div>
				<div class="oc-version"><span>${current}</span><span>${this.size_text(item.size)}</span></div>
				${found.versions
					.map(
						(one) => `<div class="oc-version" data-version="${esc(one.name)}">
							<span>${esc(__("Version {0}", [one.version]))} · ${esc(one.by)} · ${this.date_text(one.on)}</span>
							<span>${this.size_text(one.size)}</span>
							<a href="${esc(one.url)}" target="_blank" rel="noopener">${open}</a>
							<a href="#" data-restore>${restore}</a>
						</div>`
					)
					.join("")}`
			: "";
		const done = found.done
			.map((one) => `<div class="oc-done"><b>${esc(one.who)}</b> ${esc(one.what)}<small>${this.date_text(one.when)}</small></div>`)
			.join("");
		const $history = this.$preview.find(".oc-history").html(`${versions}<div class="oc-history-head">${activity_head}</div>${done}`);
		$history.find("[data-restore]").on("click", async (e) => {
			e.preventDefault();
			const version = $(e.currentTarget).closest(".oc-version").attr("data-version");
			await frappe.xcall("onedesk.one_storage.history.restore", { node: item.id, version });
			this.previewing = null;
			this.refresh();
		});
	}

	// ------------------------------------------------------------- the tree

	async draw_tree() {
		if (!this.kids["@root"]) this.kids["@root"] = await frappe.xcall(OneCloud.API + "folders", { node: "@root" });
		// Everything on the way to where we are is opened, so the tree shows it.
		for (const one of this.trail.slice(1, -1)) this.open_in_tree.add(one.id);
		for (const id of this.open_in_tree) {
			if (!this.kids[id]) {
				try {
					this.kids[id] = await frappe.xcall(OneCloud.API + "folders", { node: id });
				} catch (e) {
					this.open_in_tree.delete(id);
				}
			}
		}
		const esc = frappe.utils.escape_html;
		const draw = (list, depth) =>
			list
				.map((one) => {
					const open = this.open_in_tree.has(one.id);
					const leaf = one.id === "@bin" || (one.record && !one.doctype);
					return `<div class="oc-node${one.id === this.node ? " oc-here" : ""}" data-node="${esc(one.id)}" style="--depth:${depth}">
						<button class="oc-twisty" ${leaf ? "disabled" : ""} aria-label="${open ? __("Collapse") : __("Expand")}">${leaf ? "" : frappe.utils.icon(open ? "chevron-down" : "chevron-right", "xs")}</button>
						${frappe.utils.icon(this.icon_of(one), "sm")}<span>${esc(one.name)}</span>
					</div>${open && this.kids[one.id] ? draw(this.kids[one.id], depth + 1) : ""}`;
				})
				.join("");
		this.$tree.html(draw(this.kids["@root"], 0));
	}

	forget_tree(...ids) {
		ids.filter(Boolean).forEach((id) => delete this.kids[id]);
		if (!ids.length) this.kids = {};
	}

	// ------------------------------------------------------------- events

	bind() {
		const $r = this.$root;
		$r.on("click", "[data-act]", (e) => {
			e.stopPropagation();
			this.act(e.currentTarget.dataset.act, e);
		});
		$r.on("click", ".oc-crumbs [data-node]", (e) => {
			e.stopPropagation();
			this.go(e.currentTarget.dataset.node);
		});
		// The empty part of the address bar turns it into a path to type.
		$r.on("click", ".oc-crumbs", () => this.type_path());
		$r.on("click", ".oc-head [data-sort]", (e) => {
			const key = e.currentTarget.dataset.sort;
			this.remember({ sort: key, asc: this.settings.sort === key ? (cint(this.settings.asc) ? 0 : 1) : 1 });
			this.draw();
		});

		// The tree.
		this.$tree.on("click", ".oc-twisty", async (e) => {
			e.stopPropagation();
			const id = $(e.currentTarget).closest(".oc-node").attr("data-node");
			if (this.open_in_tree.has(id)) this.open_in_tree.delete(id);
			else this.open_in_tree.add(id);
			this.draw_tree();
		});
		this.$tree.on("click", ".oc-node", (e) => this.go(e.currentTarget.dataset.node));

		// The items.
		this.$items.on("mousedown", ".oc-item", (e) => {
			if (e.button === 2 && this.selected.has(e.currentTarget.dataset.id)) return;
			if (e.button > 2) return;
			this.pick(e.currentTarget.dataset.id, e);
		});
		this.$items.on("mousedown", (e) => {
			if (!$(e.target).closest(".oc-item").length && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
				this.selected.clear();
				this.focus_id = null;
				this.mark();
			}
		});
		this.$items.on("dblclick", ".oc-item", (e) => this.open_items([this.find(e.currentTarget.dataset.id)]));
		this.$items.on("contextmenu", (e) => {
			e.preventDefault();
			if (this.picker) return; // choosing, not changing
			const $item = $(e.target).closest(".oc-item");
			if ($item.length && !this.selected.has($item.attr("data-id"))) this.pick($item.attr("data-id"), {});
			if (!$item.length) {
				this.selected.clear();
				this.mark();
			}
			this.menu(e.clientX, e.clientY, $item.length ? this.item_menu() : this.space_menu());
		});
		$r.on("keydown", (e) => this.key(e));

		// Search, as you type.
		this.$search.on(
			"input",
			frappe.utils.debounce(() => {
				this.search = this.$search.val().trim();
				this.refresh();
			}, 300)
		);
		this.$search.on("keydown", (e) => {
			if (e.key === "Escape") {
				this.set_search("");
				this.refresh();
				this.$items.trigger("focus");
			}
			if (e.key === "ArrowDown") this.$items.trigger("focus");
			e.stopPropagation();
		});

		// Uploading by picking.
		$r.find(".oc-pick-files, .oc-pick-folder").on("change", (e) => {
			const list = [...e.target.files].map((file) => ({ file, path: file.webkitRelativePath || file.name }));
			e.target.value = "";
			this.upload(list, this.node);
		});

		$r.find(".oc-pick-version").on("change", (e) => {
			const file = e.target.files[0];
			e.target.value = "";
			const of = this.version_of;
			this.version_of = null;
			if (file && of) this.upload([{ file, path: file.name, version_of: of.id }], this.node);
		});

		this.bind_drag();
		$(document).on("mousedown.onecloud-menu keydown.onecloud-menu", (e) => {
			if (e.type === "keydown" && e.key !== "Escape") return;
			if (this.$menu && !$(e.target).closest(".es-menu").length) this.close_menu();
		});
	}

	set_search(value) {
		this.search = value;
		if (!value) this.everywhere = false;
		this.$search.val(value);
	}

	find(id) {
		return this.items.find((one) => one.id === id);
	}

	// Click, Ctrl+click and Shift+click, as everywhere.
	pick(id, e) {
		const order = this.sorted().map((one) => one.id);
		if (e.shiftKey && this.anchor && order.includes(this.anchor)) {
			const [a, b] = [order.indexOf(this.anchor), order.indexOf(id)].sort((x, y) => x - y);
			if (!(e.ctrlKey || e.metaKey)) this.selected.clear();
			order.slice(a, b + 1).forEach((one) => this.selected.add(one));
		} else if (e.ctrlKey || e.metaKey) {
			if (this.selected.has(id)) this.selected.delete(id);
			else this.selected.add(id);
			this.anchor = id;
		} else {
			this.selected = new Set([id]);
			this.anchor = id;
		}
		this.focus_id = id;
		this.mark();
	}

	key(e) {
		if ($(e.target).is("input, textarea, [contenteditable]")) return;
		const ctrl = e.ctrlKey || e.metaKey;
		const k = e.key;
		const handled = () => {
			e.preventDefault();
			e.stopPropagation();
		};
		if (k === "F5" || (ctrl && k === "r")) return handled(), this.act("refresh");
		if ((e.altKey && k === "ArrowLeft") || k === "Backspace") return handled(), this.act("back");
		if (e.altKey && k === "ArrowRight") return handled(), this.act("forward");
		if (e.altKey && k === "ArrowUp") return handled(), this.act("up");
		// Choosing a file changes nothing: none of the keys that would.
		const changes = (ctrl && ["c", "x", "v"].includes(k)) || ["F2", "Delete"].includes(k) || (ctrl && e.shiftKey && k.toLowerCase() === "n");
		if (this.picker && changes) return;
		if (ctrl && e.shiftKey && (k === "N" || k === "n")) return handled(), this.act("new-folder");
		if (ctrl && e.shiftKey && k.toLowerCase() === "f" && !this.room) {
			handled();
			this.everywhere = true;
			if (this.search) this.refresh();
			else this.draw();
			return this.$search.trigger("focus").trigger("select");
		}
		if ((ctrl && k === "f") || k === "F3") return handled(), this.$search.trigger("focus").trigger("select");
		if (ctrl && k === "a") {
			handled();
			this.items.forEach((one) => this.selected.add(one.id));
			return this.mark();
		}
		if (ctrl && k === "c") return handled(), this.act("copy");
		if (ctrl && k === "x") return handled(), this.act("cut");
		if (ctrl && k === "v") return handled(), this.act("paste");
		if (k === "F2") return handled(), this.act("rename");
		if (k === "Delete") return handled(), this.act(e.shiftKey || this.kind() === "bin" ? "purge" : "delete");
		if (k === "Enter") return handled(), this.open_items(this.chosen());
		if (k === "Escape") {
			handled();
			if (this.$menu) return this.close_menu();
			if (this.clipboard) this.clipboard = null;
			this.selected.clear();
			return this.mark();
		}
		const moves = { ArrowDown: 1, ArrowUp: -1, ArrowRight: 1, ArrowLeft: -1, Home: "first", End: "last" };
		if (k in moves && !e.altKey) {
			handled();
			const order = this.sorted().map((one) => one.id);
			if (!order.length) return;
			let at = order.indexOf(this.focus_id);
			const across = this.settings.view === "tiles" ? this.columns() : 1;
			if (moves[k] === "first") at = 0;
			else if (moves[k] === "last") at = order.length - 1;
			else if (at < 0) at = 0;
			else if (this.settings.view === "details" && (k === "ArrowLeft" || k === "ArrowRight")) return;
			else at += moves[k] * (k === "ArrowDown" || k === "ArrowUp" ? across : 1);
			at = Math.max(0, Math.min(order.length - 1, at));
			this.pick(order[at], { shiftKey: e.shiftKey, ctrlKey: false });
			const el = this.$items.find(`.oc-item[data-id="${CSS.escape(order[at])}"]`)[0];
			el && el.scrollIntoView({ block: "nearest" });
		}
	}

	columns() {
		const tiles = this.$items.find(".oc-item").toArray();
		if (!tiles.length) return 1;
		const top = tiles[0].offsetTop;
		return Math.max(1, tiles.filter((el) => el.offsetTop === top).length);
	}

	// ------------------------------------------------------------- verbs

	async act(act, e) {
		const chosen = this.chosen();
		const call = (method, args) => frappe.xcall(OneCloud.API + method, args);
		const ids = chosen.filter((one) => this.stored(one)).map((one) => one.id);
		switch (act) {
			case "back":
				if (this.picker && this.past.length) return this.ahead.push(this.node), this.open(this.past.pop());
				if (this.past.length) window.history.back();
				return;
			case "forward":
				if (this.picker && this.ahead.length) return this.past.push(this.node), this.open(this.ahead.pop());
				if (this.ahead.length) window.history.forward();
				return;
			case "up":
				if (this.trail.length > 1) this.go(this.trail[this.trail.length - 2].id);
				return;
			case "refresh":
				this.forget_tree();
				return this.refresh();
			case "view-details":
				return this.remember({ view: "details" });
			case "view-tiles":
				return this.remember({ view: "tiles" });
			case "toggle-preview":
				this.previewing = null;
				this.remember({ preview: cint(this.settings.preview) ? 0 : 1 });
				return this.draw_preview();
			case "new-menu": {
				const at = e.currentTarget.getBoundingClientRect();
				return this.menu(at.left, at.bottom + 4, this.new_menu());
			}
			case "new-folder":
				if (!this.can_make_folder) return;
				return this.new_folder();
			case "new-library":
				return this.new_library();
			case "new-mount":
				return this.mount_dialog(null);
			case "new-request":
				return this.request_dialog();
			case "request-progress":
				return this.request_progress(chosen[0].id.split("/")[1]);
			case "mount-edit":
				return this.mount_dialog(chosen[0]);
			case "mount-drop":
				return frappe.confirm(__("Disconnect {0}? Nothing on the server is touched.", [chosen[0].name]), async () => {
					await frappe.xcall("onedesk.one_storage.mounts.disconnect", { node: chosen[0].id });
					this.forget_tree("@mounts");
					this.refresh();
				});
			case "members": {
				const here = this.library_here();
				if (here) this.members({ id: here.id, name: here.name });
				return;
			}
			case "upload-files":
				return this.$root.find(".oc-pick-files").trigger("click");
			case "upload-folder":
				return this.$root.find(".oc-pick-folder").trigger("click");
			case "cut":
			case "copy":
				if (!ids.length || this.kind() === "bin") return;
				this.clipboard = { mode: act, ids, from: this.node };
				frappe.show_alert({
					message: act === "cut" ? this.count(ids.length, __("Cut 1 item"), __("Cut {0} items")) : this.count(ids.length, __("Copied 1 item"), __("Copied {0} items")),
					indicator: "blue",
				});
				return this.mark();
			case "paste":
				return this.paste(this.node);
			case "paste-into":
				return this.paste(chosen[0].id);
			case "rename":
				if (chosen.length === 1 && this.stored(chosen[0]) && !["bin", "record"].includes(this.kind())) this.rename(chosen[0]);
				return;
			case "share":
				if (chosen.length === 1 && this.shareable(chosen[0])) this.share(chosen[0]);
				return;
			case "drive":
				return this.drive(chosen[0].id, chosen[0].name);
			case "storage-check":
				return frappe.set_route("query-report", "Storage Check");
			case "drive-here": {
				const here = this.trail[this.trail.length - 1];
				return this.drive(this.node, here ? here.name : __("Files"));
			}
			case "star":
			case "unstar":
				await frappe.xcall("onedesk.one_storage.history.star", { nodes: ids, on: act === "star" ? 1 : 0 });
				this.previewing = null;
				return this.refresh();
			case "new-version":
				if (chosen.length !== 1 || chosen[0].folder) return;
				this.version_of = chosen[0];
				return this.$root.find(".oc-pick-version").trigger("click");
			case "download":
				return this.download(chosen.filter((one) => !one.folder && one.url));
			case "copy-link":
				return frappe.utils.copy_to_clipboard(chosen.map((one) => window.location.origin + one.url).join("\n"));
			case "open":
				return this.open_items(chosen);
			case "open-location":
				this.reveal = chosen[0].id;
				return this.go(chosen[0].parent);
			case "open-record": {
				const record = this.record_of(chosen[0]) || this.record_here();
				if (record) frappe.set_route("Form", record[0], record[1]);
				return;
			}
			case "delete":
				if (!ids.length) return;
				if (this.kind() === "bin") return this.act("purge");
				return this.remove(chosen);
			case "restore":
				if (!ids.length) return;
				await call("restore", { nodes: ids });
				frappe.show_alert({ message: this.count(ids.length, __("Restored 1 item"), __("Restored {0} items")), indicator: "green" });
				this.forget_tree();
				return this.refresh();
			case "purge":
				if (!ids.length) return;
				return frappe.confirm(
					ids.length === 1
						? __("Delete {0} for good? This cannot be undone.", [chosen[0].name])
						: __("Delete these {0} items for good? This cannot be undone.", [ids.length]),
					async () => {
						await call("purge", { nodes: ids });
						this.forget_tree();
						this.refresh();
					}
				);
			case "empty-bin":
				return frappe.confirm(__("Delete everything in the Recycle Bin for good? This cannot be undone."), async () => {
					await call("empty_bin");
					this.refresh();
				});
			case "sort-name":
			case "sort-modified":
			case "sort-type":
			case "sort-size":
				this.remember({ sort: act.slice(5), asc: act === "sort-modified" || act === "sort-size" ? 0 : 1 });
				return this.draw();
		}
	}

	record_of(item) {
		if (!item || !item.record) return null;
		return item.record;
	}

	record_here() {
		const parts = (this.node || "").split("/");
		return parts[0] === "@records" && parts.length === 3 ? [parts[1], parts[2]] : null;
	}

	open_items(items) {
		items = items.filter(Boolean);
		if (!items.length) return;
		const folder = items.find((one) => one.folder);
		if (folder && items.length === 1) return this.go(folder.id);
		if (this.picker) return this.picker.on_pick(items.filter((one) => !one.folder));
		items.filter((one) => !one.folder && one.url).forEach((one) => window.open(one.url, "_blank", "noopener"));
	}

	download(items) {
		items.forEach((one, at) => {
			setTimeout(() => {
				const a = document.createElement("a");
				a.href = one.url.startsWith("/api/") ? `${one.url}&download=1` : one.url;
				a.download = one.name;
				document.body.appendChild(a);
				a.click();
				a.remove();
			}, at * 400);
		});
	}

	async new_folder() {
		const made = await frappe.xcall(OneCloud.API + "make_folder", { parent: this.node, name: __("New folder") });
		this.forget_tree(this.node);
		await this.refresh();
		this.selected = new Set([made.id]);
		this.focus_id = this.anchor = made.id;
		this.mark();
		this.rename(this.find(made.id));
	}

	// Renaming in place: the name becomes a box, the part before the extension
	// chosen, Enter keeps it and Escape does not.
	rename(item) {
		if (!item) return;
		const $label = this.$items.find(`.oc-item[data-id="${CSS.escape(item.id)}"] .oc-label`);
		if (!$label.length) return;
		const $box = $(`<input class="oc-rename" spellcheck="false">`).val(item.name);
		$label.replaceWith($box);
		const dot = item.folder ? -1 : item.name.lastIndexOf(".");
		$box.trigger("focus");
		$box[0].setSelectionRange(0, dot > 0 ? dot : item.name.length);
		let done = false;
		const finish = async (keep) => {
			if (done) return;
			done = true;
			const name = $box.val().trim();
			if (keep && name && name !== item.name) {
				try {
					await frappe.xcall(OneCloud.API + "rename", { node: item.id, name });
				} catch (e) {
					// the server said why; the old name comes back
				}
				this.forget_tree();
			}
			await this.refresh();
			this.$items.trigger("focus");
		};
		$box.on("keydown", (e) => {
			e.stopPropagation();
			if (e.key === "Enter") finish(true);
			if (e.key === "Escape") finish(false);
		});
		$box.on("blur", () => finish(true));
		$box.on("mousedown dblclick", (e) => e.stopPropagation());
	}

	async remove(items) {
		const attached = items.filter((one) => (one.record && !one.folder) || one.remote);
		const go = async () => {
			const r = await frappe.xcall(OneCloud.API + "delete", { nodes: items.map((one) => one.id) });
			const binned = (r && +r.binned) || 0;
			if (binned) frappe.show_alert({ message: this.count(binned, __("Moved 1 item to the Recycle Bin"), __("Moved {0} items to the Recycle Bin")), indicator: "blue" });
			this.forget_tree();
			this.refresh();
		};
		if (!attached.length) return go();
		if (attached.some((one) => one.remote)) {
			return frappe.confirm(
				attached.length === 1
					? __("Delete {0} from the server? This cannot be undone.", [attached[0].name])
					: __("Delete these {0} items from the server? This cannot be undone.", [attached.length]),
				go
			);
		}
		frappe.confirm(
			attached.length === 1
				? __("Remove {0} from its record? This cannot be undone.", [attached[0].name])
				: __("Remove these {0} files from their records? This cannot be undone.", [attached.length]),
			go
		);
	}

	async paste(target) {
		if (!this.clipboard) return;
		const { mode, ids } = this.clipboard;
		await this.transfer(ids, target, mode === "cut" ? "move" : "copy");
		if (mode === "cut") this.clipboard = null;
	}

	async transfer(ids, target, how) {
		if (!ids.length || ids.includes(target)) return;
		const done = await frappe.xcall(how === "move" ? OneCloud.API + "move" : OneCloud.API + "copy", { nodes: ids, target });
		const n = (done && done.length) || 0;
		frappe.show_alert({
			message: how === "move" ? this.count(n, __("Moved 1 item"), __("Moved {0} items")) : this.count(n, __("Copied 1 item"), __("Copied {0} items")),
			indicator: "green",
		});
		this.forget_tree();
		this.refresh();
	}

	// ------------------------------------------------------------- sharing

	// Anything stored can be opened in the Share dialog; the server says
	// whether people or links can be added to it.
	shareable(item) {
		return this.filed(item);
	}

	share(item) {
		if (item.library) return this.members(item);
		const call = (method, args) => frappe.xcall("onedesk.one_storage.share." + method, args);
		const dialog = new frappe.ui.Dialog({
			title: __("Share {0}", [item.name]),
			// The people picker opens its list on focus, over everything else.
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
					label: __("They can"),
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
				this.refresh();
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
						<button class="es-button" data-variant="ghost" data-icon-button="true" data-size="sm" data-remove title="${__("Remove")}">${frappe.utils.icon("x", "sm")}</button>`
					: `<span class="oc-person-right">${person.edit ? __("Can edit") : __("Can view")}</span>`;
			const inherited = (person) => `<span class="oc-person-right">${person.edit ? __("Can edit") : __("Can view")} · ${esc(__("from {0}", [person.from]))}</span>`;
			const owner_note = __("Owner");
			const people_head = who.can_share || who.people.length ? __("People with access") : "";
			const record_note = item.record && !item.folder ? __("This file is attached to a record, and goes to whoever may open the record.") : "";
			const found = who.can_link ? await frappe.xcall("onedesk.one_storage.links.links", { node: item.id }) : [];
			$people.html(`
				${people_head ? `<div class="oc-people-head">${people_head}</div>` : ""}
				${record_note ? `<p class="oc-people-note">${record_note}</p>` : ""}
				${people_head ? row(who.owner, `<span class="oc-person-right">${owner_note}</span>`) : ""}
				${who.people.map((person) => row(person, choose(person))).join("")}
				${who.inherited.map((person) => row(person, inherited(person))).join("")}
				${who.can_link ? this.links_html(found) : ""}`);
			$people.find("[data-new-link]").on("click", () => this.new_link(item, draw));
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
				this.refresh();
			});
			dialog.fields_dict.users.$wrapper.toggle(!!who.can_share);
			dialog.set_title(who.can_share ? __("Share {0}", [item.name]) : __("Links to {0}", [item.name]));
			dialog.fields_dict.access.$wrapper.toggle(!!who.can_share);
			dialog.get_primary_btn().toggle(!!who.can_share);
		};
		dialog.show();
		draw();
	}

	links_html(found) {
		const esc = frappe.utils.escape_html;
		const head = __("Links");
		const make = __("Create link");
		const copy = __("Copy link");
		const remove = __("Remove");
		const rows = found
			.map((one) => {
				const said = [
					one.audience === "Invited people" ? __("Only {0}", [one.invitees.join(", ")]) : __("Anyone with the link"),
					one.allow_upload ? __("can upload") : one.allow_download ? __("can download") : __("can view"),
					one.expires_on ? (one.expired ? __("ran out {0}", [this.date_text(one.expires_on)]) : __("until {0}", [this.date_text(one.expires_on)])) : "",
					one.has_password ? __("password") : "",
					one.opened ? __("opened {0} times", [one.opened]) : "",
				].filter(Boolean);
				return `<div class="oc-link" data-name="${esc(one.name)}" data-url="${esc(one.url)}">
					${frappe.utils.icon("link", "sm")}
					<span class="oc-link-said">${esc(said.join(" · "))}</span>
					<button class="es-button" data-variant="ghost" data-icon-button="true" data-size="sm" data-copy-link title="${copy}">${frappe.utils.icon("copy", "sm")}</button>
					<button class="es-button" data-variant="ghost" data-icon-button="true" data-size="sm" data-drop-link title="${remove}">${frappe.utils.icon("x", "sm")}</button>
				</div>`;
			})
			.join("");
		return `<div class="oc-people-head">${head}</div>${rows}
			<button class="es-button" data-variant="subtle" data-new-link>${frappe.utils.icon("link", "sm")}<span class="es-button__label">${make}</span></button>`;
	}

	// A link for people outside the team: who, what they can do, until when.
	new_link(item, after) {
		const dialog = new frappe.ui.Dialog({
			title: __("Create link"),
			fields: [
				{
					fieldtype: "Select",
					fieldname: "audience",
					label: __("Who can open it"),
					options: [
						{ value: "Anyone with the link", label: __("Anyone with the link") },
						{ value: "Invited people", label: __("Only people I invite by email") },
					],
					default: "Anyone with the link",
				},
				{
					fieldtype: "Small Text",
					fieldname: "invitees",
					label: __("Email addresses"),
					description: __("One per line. Each is sent the link, and a code when they open it."),
					depends_on: "eval:doc.audience=='Invited people'",
					mandatory_depends_on: "eval:doc.audience=='Invited people'",
				},
				{ fieldtype: "Check", fieldname: "allow_download", label: __("Can download"), default: 1 },
				{ fieldtype: "Check", fieldname: "allow_upload", label: __("Can upload files into it"), default: 0, hidden: item.folder ? 0 : 1 },
				{ fieldtype: "Datetime", fieldname: "expires_on", label: __("Expires on") },
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
	}

	// ------------------------------------------------------------- libraries

	// The library the reader is somewhere inside, from the trail.
	library_here() {
		return this.trail.length > 2 && this.trail[1].id === "@libraries" ? this.trail[2] : null;
	}

	new_library() {
		frappe.prompt(
			{ fieldtype: "Data", fieldname: "name", label: __("Library name"), reqd: 1 },
			async ({ name }) => {
				const made = await frappe.xcall("onedesk.one_storage.library.make", { name });
				this.forget_tree("@libraries");
				this.go(made.id);
			},
			__("New library"),
			__("Create")
		);
	}

	members(item) {
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
					label: __("As"),
					options: roles,
					default: "Member",
					description: __("Readers open and download. Members also add, change and delete. Owners also rename the library and say who is in it."),
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
						<button class="es-button" data-variant="ghost" data-icon-button="true" data-size="sm" data-remove>${frappe.utils.icon("x", "sm")}</button>`
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
	}

	// ------------------------------------------------------------- servers

	// Between a server and OneCloud, or two servers, is a copy.
	across(target) {
		const server = (id) => (id.startsWith("@mount/") ? id.split("/")[1] : null);
		return server(target) !== server(this.node);
	}

	async mount_dialog(item) {
		const found = item ? await frappe.xcall("onedesk.one_storage.mounts.settings", { node: item.id }) : null;
		const values = (found && found.values) || {};
		const admin = frappe.user.has_role("Workspace Administrator");
		const dialog = new frappe.ui.Dialog({
			title: item ? __("Edit {0}", [item.name]) : __("Connect a server"),
			fields: [
				{ fieldtype: "Data", fieldname: "title", label: __("Name"), reqd: 1, default: values.title },
				{ fieldtype: "Select", fieldname: "protocol", label: __("Kind"), options: ["SFTP", "WebDAV"], default: values.protocol || "SFTP" },
				{ fieldtype: "Data", fieldname: "host", label: __("Server"), default: values.host, depends_on: "eval:doc.protocol=='SFTP'" },
				{ fieldtype: "Int", fieldname: "port", label: __("Port"), default: values.port || 22, depends_on: "eval:doc.protocol=='SFTP'" },
				{
					fieldtype: "Data",
					fieldname: "url",
					label: __("Address"),
					default: values.url,
					depends_on: "eval:doc.protocol=='WebDAV'",
					description: __("The WebDAV address, starting https://."),
				},
				{ fieldtype: "Data", fieldname: "username", label: __("User Name"), default: values.username },
				{
					fieldtype: "Password",
					fieldname: "password",
					label: __("Password"),
					description: item ? __("Leave it empty to keep the one saved.") : "",
				},
				{
					fieldtype: "Small Text",
					fieldname: "private_key",
					label: __("Private Key"),
					depends_on: "eval:doc.protocol=='SFTP'",
					description: __("Instead of a password, for a server that signs in with a key."),
				},
				{ fieldtype: "Data", fieldname: "root_path", label: __("Folder on the Server"), default: values.root_path || "/" },
				{
					fieldtype: "Check",
					fieldname: "shared",
					label: __("Everyone on the team can open it"),
					default: values.shared || 0,
					hidden: admin ? 0 : 1,
				},
			],
			primary_action_label: item ? __("Save") : __("Connect"),
			primary_action: async (entered) => {
				const made = await frappe.xcall("onedesk.one_storage.mounts.save", { values: entered, name: found ? found.name : null });
				dialog.hide();
				this.forget_tree("@mounts");
				this.go(made.id);
			},
		});
		dialog.show();
	}

	// ------------------------------------------------------------- file requests

	// Ask people for files by name. On a record, each file can fill one of
	// its attachment fields; anywhere else, they land in this folder.
	async request_dialog() {
		const parts = this.node.split("/");
		const record = parts[0] === "@records" && parts.length === 3 ? { doctype: parts[1], name: parts[2] } : null;
		const fields = record ? await frappe.xcall("onedesk.one_storage.file_requests.fields", { doctype: record.doctype }) : [];
		const by_label = Object.fromEntries(fields.map((one) => [one.label, one.value]));
		const here = this.trail[this.trail.length - 1];
		const dialog = new frappe.ui.Dialog({
			title: __("Ask for files"),
			size: "large",
			fields: [
				{ fieldtype: "Data", fieldname: "title", label: __("What they are for"), reqd: 1 },
				{ fieldtype: "Small Text", fieldname: "recipients", label: __("People to ask"), reqd: 1, description: __("Email addresses, one per line.") },
				{ fieldtype: "Column Break" },
				{ fieldtype: "Date", fieldname: "due_date", label: __("Due Date") },
				{ fieldtype: "Small Text", fieldname: "message", label: __("Message") },
				{ fieldtype: "Section Break" },
				{
					fieldtype: "Table",
					fieldname: "items",
					label: __("Files to ask for"),
					cannot_add_rows: false,
					in_place_edit: true,
					data: [{ required: 1 }],
					fields: [
						{ fieldtype: "Data", fieldname: "label", label: __("File"), in_list_view: 1, reqd: 1, columns: 3 },
						{ fieldtype: "Check", fieldname: "required", label: __("Required"), in_list_view: 1, default: 1, columns: 1 },
						{ fieldtype: "Check", fieldname: "several", label: __("Several"), in_list_view: 1, columns: 1 },
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
							? __("Files land on {0}; one with a record field fills that field.", [here ? here.name : ""])
							: __("Files land in {0}, in a folder per person when you ask several.", [here ? here.name : __("a folder of their own in My Files")])
					)}</p>`,
				},
			],
			primary_action_label: __("Ask"),
			primary_action: async (values) => {
				const items = (values.items || []).map((one) => ({ ...one, fieldname: by_label[one.field] || null }));
				const made = await frappe.xcall("onedesk.one_storage.file_requests.make", {
					node: this.kind() === "requests" ? "@requests" : this.node,
					values: { ...values, items },
				});
				dialog.hide();
				this.forget_tree("@requests");
				if (!made.mailed) this.request_links(made.links);
				else frappe.show_alert({ message: __("Asked. Each person has their link by email."), indicator: "green" });
				this.go(made.node);
			},
		});
		dialog.show();
	}

	request_links(links) {
		const esc = frappe.utils.escape_html;
		const copy = __("Copy");
		const dialog = new frappe.ui.Dialog({
			title: __("Send each person their link"),
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "links",
					options: `<p class="oc-people-note">${esc(__("This workspace cannot send email yet, so pass each link on yourself. Each link is that person's own."))}</p>
						${links
							.map(
								(one) => `<div class="oc-drive-row"><span>${esc(one.email)}</span><code>${esc(one.url)}</code><button class="es-button" data-variant="ghost" data-size="sm" data-copy="${esc(one.url)}">${copy}</button></div>`
							)
							.join("")}`,
				},
			],
		});
		dialog.fields_dict.links.$wrapper.find("[data-copy]").on("click", (e) => frappe.utils.copy_to_clipboard(e.currentTarget.dataset.copy));
		dialog.show();
	}

	async request_progress(name) {
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
					<td><button class="es-button" data-variant="ghost" data-size="sm" data-copy="${esc(person.url)}">${copy}</button></td></tr>`
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
						<p class="oc-people-note">${esc(closed ? __("Closed. The links take nothing more.") : __("* required"))}</p>`,
				},
			],
			primary_action_label: __("Remind"),
			primary_action: async () => {
				const sent = await call("remind", { name });
				frappe.show_alert({ message: sent ? __("Reminded {0} people", [sent]) : __("Nobody to remind, or no email to remind them with"), indicator: "blue" });
			},
			secondary_action_label: closed ? __("Reopen") : __("Close request"),
			secondary_action: async () => {
				await call("close", { name, closed: closed ? 0 : 1 });
				dialog.hide();
				this.forget_tree("@requests");
				this.refresh();
			},
		});
		dialog.fields_dict.table.$wrapper.find("[data-copy]").on("click", (e) => frappe.utils.copy_to_clipboard(e.currentTarget.dataset.copy));
		dialog.get_primary_btn().toggle(!closed);
		dialog.show();
	}

	// ------------------------------------------------------------- the drive

	// A folder, or everything, as a drive in Windows, macOS or Linux: its
	// address, how each system adds one, and the password to sign in with.
	async drive(node, name) {
		const where = await frappe.xcall("onedesk.one_storage.dav.address", {
			node: ["@root", "@recent", "@starred", "@bin", "@mounts"].includes(node) || node.startsWith("@mount/") ? "@root" : node,
		});
		const esc = frappe.utils.escape_html;
		const steps = [
			[__("Windows"), __("In File Explorer, right-click This PC and choose Map network drive. Paste the address as the folder.")],
			[__("macOS"), __("In Finder, choose Go › Connect to Server and paste the address.")],
			[__("Linux"), __("In Files, choose Other Locations and paste the address after davs:// in place of https://.")],
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
						<p class="oc-people-note">${esc(__("It asks for a password: make one for each computer below. A drive password opens your drive and nothing else, and everything you can open here, you can open there."))}</p>
						<div class="oc-drive-key"></div><div class="oc-drive-list"></div>`,
				},
			],
			primary_action_label: __("Make a password"),
			primary_action: () => {
				frappe.prompt(
					{ fieldtype: "Data", fieldname: "label", label: __("Which computer is it for?"), reqd: 1 },
					async ({ label }) => {
						const made = await frappe.xcall("onedesk.one_storage.dav.make_password", { label });
						const copy = __("Copy");
						const $how = dialog.fields_dict.how.$wrapper;
						$how.find(".oc-drive-key").html(`
							<div class="oc-people-head">${esc(__("Shown once. Keep it somewhere safe."))}</div>
							<div class="oc-drive-row"><span>${esc(__("Password"))}</span><code>${esc(made.password)}</code><button class="es-button" data-variant="ghost" data-size="sm" data-copy="${esc(made.password)}">${copy}</button></div>`);
						$how.find("[data-copy]").on("click", (e) => frappe.utils.copy_to_clipboard(e.currentTarget.dataset.copy));
						list();
					},
					__("New drive password"),
					__("Make")
				);
			},
		});
		const list = async () => {
			const found = await frappe.xcall("onedesk.one_storage.dav.passwords");
			const $list = dialog.fields_dict.how.$wrapper.find(".oc-drive-list");
			if (!found.length) return $list.empty();
			const head = __("Your drive passwords");
			const never = __("Never used");
			const remove = __("Remove");
			$list.html(`<div class="oc-people-head">${head}</div>${found
				.map(
					(one) => `<div class="oc-person" data-name="${esc(one.name)}">${frappe.utils.icon("key", "sm")}
						<span class="oc-person-name">${esc(one.label)}</span>
						<span class="oc-person-right">${one.last_used ? esc(__("Used {0}", [this.date_text(one.last_used)])) : never}</span>
						<button class="es-button" data-variant="ghost" data-icon-button="true" data-size="sm" data-drop title="${remove}">${frappe.utils.icon("x", "sm")}</button></div>`
				)
				.join("")}`);
			$list.find("[data-drop]").on("click", async (e) => {
				await frappe.xcall("onedesk.one_storage.dav.drop_password", { name: $(e.currentTarget).closest(".oc-person").attr("data-name") });
				list();
			});
		};
		dialog.show();
		list();
	}

	// ------------------------------------------------------------- menus

	new_menu() {
		if (this.kind() === "libraries") return [[["new-library", "library-big", __("Library"), this.can_make_library]]];
		if (this.kind() === "network") return [[["new-mount", "server", __("Server connection"), this.can_make_mount]]];
		if (this.kind() === "requests") return [[["new-request", "inbox", __("File request"), true]]];
		return [
			[
				["new-folder", "folder-plus", __("Folder"), this.can_make_folder, "Ctrl+Shift+N"],
			],
			[
				["upload-files", "upload", __("Upload files"), this.can_add],
				["upload-folder", "folder-up", __("Upload folder"), this.can_add && this.kind() !== "record"],
			],
			[["new-request", "inbox", __("File request"), this.can_add && !this.node.startsWith("@mount")]],
		];
	}

	item_menu() {
		const chosen = this.chosen();
		const one = chosen.length === 1 ? chosen[0] : null;
		const stored = chosen.every((item) => this.stored(item));
		const files = chosen.filter((item) => !item.folder && item.url);
		if (one && one.request) {
			return [
				[
					["open", "folder-open", __("Open"), true, "Enter"],
					["request-progress", "list-checks", __("Progress…"), true],
				],
			];
		}
		if (one && one.mount) {
			return [
				[
					["open", "folder-open", __("Open"), true, "Enter"],
					["mount-edit", "settings", __("Edit connection…"), true],
					["mount-drop", "unplug", __("Disconnect"), true, null, "red"],
				],
			];
		}
		if (this.kind() === "bin") {
			return [
				[
					["restore", "rotate-ccw", __("Restore"), true],
					["purge", "trash-2", __("Delete for good"), true, "Shift+Del", "red"],
				],
			];
		}
		return [
			[
				["open", one && one.folder ? "folder-open" : "external-link", __("Open"), true, "Enter"],
				["open-location", "folder-open", __("Open file location"), !!(one && one.parent && this.search)],
				["open-record", "external-link", __("Open record"), !!(one && one.record) && !this.room],
				["download", "download", __("Download"), files.length === chosen.length],
				["copy-link", "link", __("Copy link"), files.length === chosen.length],
			].filter((row) => row[3] || row[0] === "open"),
			[
				["cut", "scissors", __("Cut"), stored, "Ctrl+X"],
				["copy", "copy", __("Copy"), stored, "Ctrl+C"],
				["paste-into", "clipboard-paste", __("Paste into folder"), !!(this.clipboard && one && one.folder)],
			],
			[
				["share", "user-plus", __("Share…"), !!(one && this.shareable(one))],
				chosen.every((item) => item.starred)
					? ["unstar", "star-off", __("Remove star"), chosen.every((item) => this.filed(item))]
					: ["star", "star", __("Star"), chosen.every((item) => this.filed(item))],
				["new-version", "upload", __("Upload new version"), !!(one && !one.folder && this.filed(one) && !one.record)],
				["drive", "hard-drive", __("Connect as a drive…"), !!(one && one.folder && !one.virtual)],
				["rename", "pencil", __("Rename"), !!(one && stored) && this.kind() !== "record", "F2"],
				["delete", "trash-2", __("Delete"), stored, "Del", "red"],
			],
		];
	}

	space_menu() {
		if (this.kind() === "libraries") return [[["new-library", "library-big", __("New library"), this.can_make_library]], [["refresh", "refresh-cw", __("Refresh"), true, "F5"]]];
		if (this.kind() === "network") return [[["new-mount", "server", __("Connect a server"), this.can_make_mount]], [["refresh", "refresh-cw", __("Refresh"), true, "F5"]]];
		return [
			[
				["new-folder", "folder-plus", __("New folder"), this.can_make_folder, "Ctrl+Shift+N"],
				["upload-files", "upload", __("Upload files"), this.can_add],
				["upload-folder", "folder-up", __("Upload folder"), this.can_add && this.kind() !== "record"],
				["paste", "clipboard-paste", __("Paste"), this.can_add && !!this.clipboard, "Ctrl+V"],
			],
			[
				["view-details", "layout-list", __("Details"), true],
				["view-tiles", "layout-grid", __("Tiles"), true],
			],
			[
				["sort-name", "arrow-up-down", __("Sort by name"), true],
				["sort-modified", "arrow-up-down", __("Sort by date"), true],
				["sort-type", "arrow-up-down", __("Sort by type"), true],
				["sort-size", "arrow-up-down", __("Sort by size"), true],
			],
			[
				["drive-here", "hard-drive", __("Connect as a drive…"), true],
				["refresh", "refresh-cw", __("Refresh"), true, "F5"],
			],
			frappe.user.has_role("Workspace Administrator") ? [["storage-check", "shield-check", __("Storage Check"), true]] : [],
		];
	}

	menu(x, y, groups) {
		this.close_menu();
		const esc = frappe.utils.escape_html;
		const html = groups
			.filter((group) => group.length)
			.map(
				(group) =>
					`<div class="es-menu__group" role="group">${group
						.map(
							([act, icon, label, on, keys, theme]) =>
								`<button class="es-menu__item" role="menuitem" data-menu="${act}" ${on ? "" : "disabled"} ${theme ? `data-theme="${theme}"` : ""}>${frappe.utils.icon(icon, "sm")}<span class="es-menu__label">${esc(label)}</span>${keys ? `<span class="oc-keys">${esc(keys)}</span>` : ""}</button>`
						)
						.join("")}</div>`
			)
			.join("");
		this.$menu = $(`<div class="es-menu oc-menu" role="menu">${html}</div>`).appendTo(document.body);
		const box = this.$menu[0].getBoundingClientRect();
		this.$menu.css({
			left: Math.min(x, window.innerWidth - box.width - 8),
			top: Math.min(y, window.innerHeight - box.height - 8),
		});
		this.$menu.on("mouseenter", ".es-menu__item", (e) => {
			this.$menu.find("[data-highlighted]").removeAttr("data-highlighted");
			e.currentTarget.setAttribute("data-highlighted", "");
		});
		this.$menu.on("click", ".es-menu__item", (e) => {
			const act = e.currentTarget.dataset.menu;
			this.close_menu();
			this.act(act, e);
		});
	}

	close_menu() {
		this.$menu && this.$menu.remove();
		this.$menu = null;
	}

	// ------------------------------------------------------------- dragging

	// Where a drag may land: a folder among the items, a node in the tree, or
	// the folder being looked at. Records take files; Shared, the Bin and the
	// lists of records take nothing.
	target_of(el) {
		const $item = $(el).closest(".oc-item[data-folder=1]");
		if ($item.length) {
			const item = this.find($item.attr("data-id"));
			if (item && this.takes(item.id)) return { id: item.id, $el: $item };
		}
		const $node = $(el).closest(".oc-node");
		if ($node.length && this.takes($node.attr("data-node"))) return { id: $node.attr("data-node"), $el: $node };
		if ($(el).closest(".oc-items").length && this.can_add) return { id: this.node, $el: this.$items };
		return null;
	}

	takes(id) {
		if (["@root", "@shared", "@bin", "@records", "@libraries", "@mounts", "@requests"].includes(id)) return false;
		if (id.startsWith("@request/")) return false;
		if (id.startsWith("@records/") && id.split("/").length !== 3) return false;
		return true;
	}

	bind_drag() {
		if (this.picker) return; // nothing is moved from inside a dialog
		const $r = this.$root;
		let over = null;
		const light = (target) => {
			if (over && (!target || over[0] !== target.$el[0])) over.removeClass("oc-drop");
			over = target ? target.$el.addClass("oc-drop") : null;
		};
		$r.on("dragstart", ".oc-item", (e) => {
			const id = e.currentTarget.dataset.id;
			if (!this.selected.has(id)) this.pick(id, {});
			const ids = this.chosen().filter((one) => this.stored(one)).map((one) => one.id);
			if (!ids.length) return e.preventDefault();
			this.dragging = ids;
			const dt = e.originalEvent.dataTransfer;
			dt.effectAllowed = "copyMove";
			dt.setData("text/plain", this.chosen().map((one) => one.name).join("\n"));
		});
		$r.on("dragend", () => {
			this.dragging = null;
			light(null);
		});
		$r.on("dragover", ".oc-items, .oc-node", (e) => {
			const dt = e.originalEvent.dataTransfer;
			const outside = !this.dragging && [...dt.types].includes("Files");
			if (!outside && !this.dragging) return;
			const target = this.target_of(e.target);
			if (!target || (this.dragging && (this.dragging.includes(target.id) || target.id === this.node))) {
				dt.dropEffect = "none";
				light(null);
				return;
			}
			e.preventDefault();
			// Across into a record, or out of one, is always a copy.
			const copying =
				outside || e.ctrlKey || e.metaKey || target.id.startsWith("@records/") || this.kind() === "record" || this.across(target.id);
			dt.dropEffect = copying ? "copy" : "move";
			light(target);
		});
		$r.on("dragleave", ".oc-items, .oc-node", (e) => {
			if (!e.currentTarget.contains(e.originalEvent.relatedTarget)) light(null);
		});
		$r.on("drop", ".oc-items, .oc-node", async (e) => {
			e.preventDefault();
			e.stopPropagation();
			light(null);
			const target = this.target_of(e.target);
			if (!target) return;
			const dt = e.originalEvent.dataTransfer;
			if (this.dragging) {
				const ids = this.dragging;
				this.dragging = null;
				const copying = e.ctrlKey || e.metaKey || target.id.startsWith("@records/") || this.kind() === "record" || this.across(target.id);
				return this.transfer(ids, target.id, copying ? "copy" : "move");
			}
			const list = await this.dropped(dt);
			if (list.length) this.upload(list, target.id);
		});
	}

	// Files and whole folders dropped from the computer, each with the path
	// it had inside what was dropped.
	async dropped(dt) {
		const entries = [...dt.items].map((one) => one.webkitGetAsEntry && one.webkitGetAsEntry()).filter(Boolean);
		if (!entries.length) return [...dt.files].map((file) => ({ file, path: file.name }));
		const out = [];
		const walk = async (entry, prefix) => {
			if (entry.isFile) {
				const file = await new Promise((ok, no) => entry.file(ok, no));
				out.push({ file, path: prefix + file.name });
			} else if (entry.isDirectory) {
				const reader = entry.createReader();
				let batch;
				do {
					batch = await new Promise((ok, no) => reader.readEntries(ok, no));
					for (const child of batch) await walk(child, `${prefix}${entry.name}/`);
				} while (batch.length);
			}
		};
		for (const entry of entries) await walk(entry, "");
		return out;
	}

	// ------------------------------------------------------------- uploads

	async upload(list, node) {
		if (!list.length) return;
		const rows = list.map((one) => ({ ...one, sent: 0, state: "waiting" }));
		this.uploads = (this.uploads || []).filter((one) => one.state !== "done").concat(rows);
		this.draw_uploads();
		for (let at = 0; at < rows.length; at += 200) {
			const batch = rows.slice(at, at + 200);
			let answer;
			try {
				answer = await frappe.xcall(OneCloud.UPLOAD + "begin", {
					node,
					files: batch.map((one) => ({ name: one.file.name, size: one.file.size, path: one.path })),
				});
			} catch (e) {
				batch.forEach((one) => (one.state = "failed"));
				this.draw_uploads();
				continue;
			}
			// Names already there: replace them, keeping the old as versions, or
			// keep both — asked once for the whole drop, the way Explorer asks.
			const clashing = new Set(answer.existing || []);
			const clash = batch.filter((one) => !one.version_of && clashing.has(one.file.name));
			const replacing = clash.length ? await this.ask_replace(clash) : false;
			batch.forEach((one, i) => {
				one.node = node;
				one.ticket = answer.direct ? answer.tickets[i] : null;
				one.replace = replacing && clashing.has(one.file.name) ? 1 : 0;
			});
			await this.pool(batch, 3, (one) => this.send(one));
		}
		this.forget_tree(node);
		if (node === this.node) this.refresh();
		else this.draw_tree();
	}

	ask_replace(clash) {
		return new Promise((answer) => {
			const names = clash.slice(0, 5).map((one) => frappe.utils.escape_html(one.file.name)).join("<br>");
			const more = clash.length > 5 ? `<br>${__("and {0} more", [clash.length - 5])}` : "";
			const dialog = new frappe.ui.Dialog({
				title: clash.length === 1 ? __("A file with this name is already here") : __("{0} files with these names are already here", [clash.length]),
				fields: [{ fieldtype: "HTML", options: `<p>${names}${more}</p><p class="text-muted">${__("Replacing keeps what they hold now as an earlier version.")}</p>` }],
				primary_action_label: __("Replace"),
				// Answered before hiding: hiding answers "keep both" for a
				// dialog closed with its cross.
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
	}

	async pool(list, most, work) {
		let next = 0;
		const lane = async () => {
			while (next < list.length) await work(list[next++]);
		};
		await Promise.all(Array.from({ length: Math.min(most, list.length) }, lane));
	}

	async send(row) {
		row.state = "sending";
		this.draw_uploads();
		try {
			if (row.ticket) {
				try {
					await this.xhr("PUT", row.ticket.url, row.file, row, { "Content-Type": row.ticket.type || row.file.type || "application/octet-stream" });
				} catch (e) {
					// R2 out of reach from this browser: through the server instead.
					row.ticket = null;
				}
			}
			if (row.ticket) {
				await frappe.xcall(OneCloud.UPLOAD + "done", {
					token: row.ticket.token,
					path: row.path,
					replace: row.replace || 0,
					version_of: row.version_of || null,
				});
			} else {
				const form = new FormData();
				form.append("node", row.node);
				form.append("path", row.path);
				form.append("replace", row.replace || 0);
				if (row.version_of) form.append("version_of", row.version_of);
				form.append("file", row.file, row.file.name);
				await this.xhr("POST", "/api/method/onedesk.one_storage.upload.here", form, row, {
					"X-Frappe-CSRF-Token": frappe.csrf_token,
					Accept: "application/json",
				});
			}
			row.state = "done";
			row.sent = row.file.size;
		} catch (e) {
			row.state = "failed";
		}
		this.draw_uploads();
	}

	xhr(method, url, body, row, headers) {
		return new Promise((ok, no) => {
			const request = new XMLHttpRequest();
			request.open(method, url, true);
			Object.entries(headers || {}).forEach(([k, v]) => request.setRequestHeader(k, v));
			request.upload.onprogress = (e) => {
				row.sent = e.loaded;
				this.draw_uploads_soon();
			};
			request.onload = () => {
				if (request.status >= 200 && request.status < 300) return ok(request);
				let why = "";
				try {
					const answer = JSON.parse(request.responseText);
					why = answer._server_messages ? JSON.parse(JSON.parse(answer._server_messages)[0]).message : answer.exception || "";
				} catch (e) {
					why = "";
				}
				row.why = why;
				no(new Error(why || String(request.status)));
			};
			request.onerror = () => no(new Error("network"));
			request.send(body);
		});
	}

	draw_uploads_soon() {
		if (this.drawing_uploads) return;
		this.drawing_uploads = requestAnimationFrame(() => {
			this.drawing_uploads = null;
			this.draw_uploads();
		});
	}

	draw_uploads() {
		const $box = this.$root.find(".oc-uploads");
		const rows = this.uploads || [];
		if (!rows.length) return $box.attr("hidden", true);
		const esc = frappe.utils.escape_html;
		const done = rows.filter((one) => one.state === "done").length;
		const failed = rows.filter((one) => one.state === "failed").length;
		const busy = rows.some((one) => one.state === "waiting" || one.state === "sending");
		const title = busy
			? __("Uploading {0} of {1}", [Math.min(done + failed + 1, rows.length), rows.length])
			: failed
			? __("{0} uploaded, {1} failed", [done, failed])
			: __("{0} uploaded", [done]);
		$box.removeAttr("hidden").html(`
			<div class="oc-uploads-head"><span>${title}</span>
				<button class="es-button" data-variant="ghost" data-icon-button="true" data-size="sm" data-close aria-label="${__("Close")}" ${busy ? "disabled" : ""}>${frappe.utils.icon("x", "sm")}</button></div>
			<div class="oc-uploads-rows">${rows
				.slice(-50)
				.map(
					(one) => `<div class="oc-upload" data-state="${one.state}" title="${esc(one.why || "")}">
						<span class="oc-upload-name">${esc(one.path || one.file.name)}</span>
						<span class="oc-upload-bar"><span style="width:${Math.round((100 * (one.sent || 0)) / (one.file.size || 1))}%"></span></span>
						<span class="oc-upload-state">${one.state === "failed" ? __("Failed") : one.state === "done" ? __("Done") : ""}</span>
					</div>`
				)
				.join("")}</div>`);
		$box.find("[data-close]").on("click", () => {
			this.uploads = [];
			$box.attr("hidden", true);
		});
	}
};
