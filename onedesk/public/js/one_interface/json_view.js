// OneInterface's JSON field (onedesk/one_interface/AGENTS.md, Fields): what a
// field holds as JSON is shown as a tree that folds by level. It is a field
// like the others, one filled box: a heading row with a search that finds a
// key or a value at any depth, what is being pointed at, and its tools as
// icons; a hairline; the tree.
//
// Read-only, the tree only reads. Editable (a JSON field, or a Code field
// whose options say JSON), the tree is where it is edited: a value or a key
// is changed where it stands, a row is removed or given a child from the
// icons it shows on hover, and every change is written back as JSON text.
// Raw shows frappe's code editor over the same text, for pasting or for
// text that is not JSON yet; going back to the tree reads it again.
onedesk.json_view = {
	// Unfolded at first: the top two levels, or all of it when it is small.
	OPEN: 2,
	SMALL: 60,
	LONG: 160,

	parse(text) {
		if (typeof text !== "string" || !/^\s*[[{]/.test(text)) return undefined;
		try {
			const value = JSON.parse(text);
			return value && typeof value === "object" ? value : undefined;
		} catch (e) {
			return undefined;
		}
	},

	kind(value) {
		if (value === null) return "null";
		if (Array.isArray(value)) return "array";
		return typeof value;
	},

	path(parent, key, in_array) {
		if (in_array) return `${parent}[${key}]`;
		return /^[A-Za-z_$][\w$]*$/.test(key) ? (parent ? `${parent}.${key}` : key) : `${parent}[${JSON.stringify(key)}]`;
	},

	// The tree as rows, parents first: each with its depth, its parent's
	// index, the object or list that holds it and, for an object or a list,
	// what it holds. What sits inside JSON kept as text is shown, never edited.
	rows(json) {
		const rows = [];
		const walk = (value, key, path, depth, parent, holder, locked) => {
			const nested = this.kind(value) === "string" ? this.parse(value) : undefined;
			const inner = nested !== undefined ? nested : value;
			const kind = this.kind(inner);
			const in_array = Array.isArray(holder);
			const row = { key, path, depth, parent, in_array, holder, value, kind, nested: nested !== undefined, locked };
			rows.push(row);
			if (kind === "object" || kind === "array") {
				const at = rows.length - 1;
				row.size = Object.keys(inner).length;
				row.inner = inner;
				for (const one of Object.keys(inner)) {
					walk(inner[one], kind === "array" ? Number(one) : one, this.path(path, one, kind === "array"), depth + 1, at, inner, locked || row.nested);
				}
			}
		};
		for (const one of Object.keys(json)) walk(json[one], Array.isArray(json) ? Number(one) : one, this.path("", one, Array.isArray(json)), 0, -1, json, false);
		return rows;
	},

	// Whether a field is edited here: a JSON field, or Code that says JSON.
	is_json(control) {
		return control.df.fieldtype === "JSON" || (control.df.fieldtype === "Code" && control.df.options === "JSON");
	},

	// A field on a form: the tree instead of frappe's read-only text, or, for
	// a JSON field that can be edited, instead of the code editor.
	field(control) {
		const value = control.value ?? (control.get_value && control.get_value());
		const status = control.get_status && control.get_status();
		const editable = status === "Write" && this.is_json(control);
		let json = status === "Read" || editable ? this.parse(value) : undefined;
		if (editable && json === undefined && !(value || "").trim()) json = {};
		let $view = control.$wrapper.find(".one-json").first();
		// Text that is not JSON yet is still this field's: it stays in Raw,
		// with the heading, until it reads as JSON again.
		if (editable && json === undefined) {
			if (!$view.length) {
				$view = this.draw({}, control, true).data("source", value);
				$(control.input_area || control.disp_area).before($view);
			}
			$view.data("source", value);
			this.raw($view, control, true);
			return;
		}
		if (json === undefined || (status !== "Read" && !editable)) {
			$view.remove();
			$(control.input_area).removeClass("hide");
			control.$expand_button && control.$expand_button.removeClass("hide");
			return;
		}
		if ($view.length && $view.data("source") === value && !!$view.data("editable") === editable) {
			this.raw($view, control, !!$view.data("raw"));
			return;
		}
		const raw = !!$view.data("raw");
		const opened = $view.data("opened");
		$view.remove();
		$view = this.draw(json, control, editable, opened).data("source", value);
		// Above frappe's own input, so Raw reads as the tree's own box going on.
		$(control.input_area || control.disp_area).before($view);
		this.raw($view, control, raw && editable);
	},

	// Tree or the stored text. Read-only, the text is laid out with two
	// spaces a level and frappe's own display and copy button stay hidden.
	// Editable, raw is frappe's code editor; back to the tree reads it again.
	raw($view, control, raw) {
		const editable = !!$view.data("editable");
		$view.data("raw", raw);
		$view.find(".one-json-search, .one-json-body, [data-action=open], [data-action=fold], [data-action=add]").toggleClass("hide", raw);
		$view.find(".one-json-text").toggleClass("hide", !raw || editable);
		$view.find("[data-action=raw]").replaceWith(this.icon(raw ? "list-tree" : "code", raw ? __("Show Tree") : __("Show Raw"), "raw"));
		$view.toggleClass("one-json-raw", raw);
		$(control.disp_area).addClass("hide");
		control.copy_button && control.copy_button.addClass("hide");
		if (editable) {
			$(control.input_area).toggleClass("hide", !raw);
			control.$expand_button && control.$expand_button.toggleClass("hide", !raw);
			if (raw && control.editor) {
				control.editor.resize();
				control.editor.focus();
			}
		}
	},

	draw(json, control, editable, opened_before) {
		const esc = frappe.utils.escape_html;
		let rows = this.rows(json);
		const words = () => (rows.length === 1 ? __("1 key") : __("{0} keys", [rows.length]));
		const find = esc(__("Find a key or a value"));
		const $view = $(`
			<div class="one-json${editable ? " one-json-editable" : ""}">
				<div class="one-json-head">
					<label class="one-json-search">${frappe.utils.icon("search", "sm")}<input type="text" class="one-json-find" placeholder="${find}" aria-label="${find}"></label>
					<div class="ellipsis one-json-where">${esc(words())}</div>
					${editable ? this.icon("plus", __("Add"), "add") : ""}
					${this.icon("chevrons-up-down", __("Expand All"), "open")}
					${this.icon("chevrons-down-up", __("Collapse All"), "fold")}
					${this.icon("code", __("Show Raw"), "raw")}
					${this.icon("copy", __("Copy"), "all")}
				</div>
				<div class="one-json-body">
					<div class="one-json-rows"></div>
					<div class="text-muted small one-json-none hide">${esc(__("Nothing matches"))}</div>
				</div>
				<pre class="one-json-text hide"></pre>
			</div>`).data("editable", editable);
		const $rows = $view.find(".one-json-rows");
		const open = rows.length <= this.SMALL ? Infinity : this.OPEN;
		// What is unfolded is kept by path, so an edit redraws the tree as it was.
		const opened = opened_before && opened_before.size ? opened_before : new Set(rows.filter((row) => row.size !== undefined && row.depth < open).map((row) => row.path));
		$view.data("opened", opened);
		let $made = [];

		const show = () => {
			const word = $view.find(".one-json-find").val().trim().toLowerCase();
			const hit = rows.map(
				(row) => !!word && (String(row.key).toLowerCase().includes(word) || (row.size === undefined && String(row.value).toLowerCase().includes(word)))
			);
			const kept = new Set();
			if (word) {
				hit.forEach((yes, at) => {
					for (let up = yes ? at : -1; up >= 0 && !kept.has(up); up = rows[up].parent) kept.add(up);
				});
			}
			rows.forEach((row, at) => {
				let shown = word ? kept.has(at) : true;
				for (let up = row.parent; shown && up >= 0; up = rows[up].parent) shown = word ? kept.has(up) : opened.has(rows[up].path);
				$made[at].toggleClass("hide", !shown).toggleClass("one-json-hit", hit[at]);
				$made[at].find(".one-json-caret").toggleClass("open", word ? true : opened.has(row.path));
			});
			$view.find(".one-json-none").toggleClass("hide", !word || kept.size > 0);
		};
		const render = () => {
			rows = this.rows(json);
			$rows.empty();
			$made = rows.map((row, at) => this.row(row, at, editable).appendTo($rows));
			$view.find(".one-json-where").text(words());
			$view.find(".one-json-text").text(JSON.stringify(json, null, 2));
			show();
		};
		render();

		// An edit is written back as JSON text, the way frappe stores JSON;
		// the view keeps the text it wrote, so frappe's refresh leaves it be.
		const save = () => {
			const text = JSON.stringify(json, null, 1);
			$view.data("source", text);
			render();
			control.set_value(text);
		};
		// The object or list a row stands for: the parsed JSON, not the text.
		const container = (row) => (row ? row.inner : json);
		const add = (row) => {
			const into = container(row);
			if (row) opened.add(row.path);
			let key;
			if (Array.isArray(into)) {
				key = into.length;
				into.push("");
			} else {
				key = "key";
				for (let n = 1; Object.hasOwn(into, key); n++) key = `key_${n}`;
				into[key] = "";
			}
			save();
			const made = rows.findIndex((one) => one.holder === into && one.key === key);
			if (made >= 0) edit(made, Array.isArray(into) ? "value" : "key");
		};
		const remove = (row) => {
			if (Array.isArray(row.holder)) row.holder.splice(row.key, 1);
			else delete row.holder[row.key];
			save();
		};
		// A value is typed as it reads: text stays text; a number, true, false
		// or null is that, and anything else becomes text.
		const typed = (row, text) => {
			if (row.kind === "string") return text;
			try {
				const value = JSON.parse(text);
				return typeof value === "object" && value !== null ? text : value;
			} catch (e) {
				return text;
			}
		};
		const rename = (row, key) => {
			if (!key || key === row.key || Object.hasOwn(row.holder, key)) return false;
			const entries = Object.entries(row.holder).map(([one, value]) => [one === row.key ? key : one, value]);
			for (const one of Object.keys(row.holder)) delete row.holder[one];
			for (const [one, value] of entries) row.holder[one] = value;
			return true;
		};
		const edit = (at, part) => {
			const row = rows[at];
			const $part = $made[at].find(part === "key" ? ".one-json-key" : ".one-json-value");
			const before = part === "key" ? String(row.key) : row.kind === "string" ? row.value : JSON.stringify(row.value);
			const $input = $(`<input type="text" class="one-json-edit" spellcheck="false">`).val(before);
			$part.addClass("hide").after($input);
			$input.trigger("focus").trigger("select");
			let done = false;
			const finish = (keep) => {
				if (done) return;
				done = true;
				const text = $input.val();
				if (keep && text !== before) {
					if (part === "key" ? rename(row, text.trim()) : ((row.holder[row.key] = typed(row, text)), true)) return save();
				}
				$input.remove();
				$part.removeClass("hide");
			};
			$input.on("keydown", (event) => {
				if (event.key === "Enter") finish(true);
				else if (event.key === "Escape") finish(false);
				else return;
				event.preventDefault();
				event.stopPropagation();
			});
			$input.on("blur", () => finish(true));
		};

		const at = (event) => Number($(event.currentTarget).closest(".one-json-row").attr("data-at"));
		$view.on("click", ".one-json-caret", (event) => {
			const row = rows[at(event)];
			opened.has(row.path) ? opened.delete(row.path) : opened.add(row.path);
			show();
		});
		$view.on("click", "[data-action=open]", () => {
			rows.forEach((row) => row.size !== undefined && opened.add(row.path));
			show();
		});
		$view.on("click", "[data-action=fold]", () => {
			opened.clear();
			show();
		});
		$view.on("click", "[data-action=raw]", () => {
			const raw = !$view.data("raw");
			if (editable && !raw) {
				const text = control.get_value() || "";
				const read = text.trim() ? this.parse(text) : {};
				if (read === undefined) return frappe.show_alert({ message: __("Invalid JSON"), indicator: "red" });
				$view.data("source", null);
				$view.data("raw", false);
				return this.field(control);
			}
			this.raw($view, control, raw);
		});
		$view.on("click", "[data-action=copy]", (event) => {
			const row = rows[at(event)];
			frappe.utils.copy_to_clipboard(row.size === undefined ? String(row.value) : JSON.stringify(row.nested ? JSON.parse(row.value) : row.value, null, 2));
		});
		$view.on("click", "[data-action=all]", () => frappe.utils.copy_to_clipboard(control.get_value() || control.value));
		$view.on("mouseenter", ".one-json-row", (event) => $view.find(".one-json-where").text(rows[at(event)].path));
		$view.on("mouseleave", ".one-json-rows", () => $view.find(".one-json-where").text(words()));
		$view.find(".one-json-find").on("input", frappe.utils.debounce(show, 150));
		if (editable) {
			$view.on("click", "[data-action=add]", (event) => {
				const row = $(event.currentTarget).closest(".one-json-row").length ? rows[at(event)] : null;
				add(row);
			});
			$view.on("click", "[data-action=remove]", (event) => remove(rows[at(event)]));
			$view.on("click", ".one-json-editable-part", (event) => {
				const part = $(event.currentTarget).hasClass("one-json-key") ? "key" : "value";
				edit(at(event), part);
			});
		}
		return $view;
	},

	// The heading's tools and a row's are icons, each named by its tooltip.
	icon(icon, title, action, css_class = "") {
		return frappe.ui.button.html({ icon, size: "sm", variant: "ghost", title, css_class, attrs: { "data-action": action, "aria-label": title } });
	},

	row(row, at, editable) {
		const esc = frappe.utils.escape_html;
		const changes = editable && !row.locked;
		const caret =
			row.size !== undefined
				? frappe.ui.button.html({ icon: "chevron-right", size: "xs", variant: "ghost", title: __("Fold or unfold"), css_class: "one-json-caret" })
				: `<span class="one-json-caret-space"></span>`;
		const named = changes && !row.in_array;
		const key = `<span class="${row.in_array ? "text-muted" : "one-json-key"}${named ? " one-json-editable-part" : ""}">${esc(String(row.key))}</span>`;
		let value;
		if (row.size !== undefined) {
			const size = row.kind === "array" ? `[${row.size}]` : `{${row.size}}`;
			value = `<span class="text-muted">${esc(size)}</span>${row.nested ? ` <span class="indicator-pill no-indicator-dot violet">${esc(__("JSON in text"))}</span>` : ""}`;
		} else {
			const text = row.kind === "string" ? row.value : String(row.value);
			const shown = text.length > this.LONG ? `${text.slice(0, this.LONG)}…` : text;
			const when = row.kind === "string" && /^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?$/.test(text);
			const link = !changes && row.kind === "string" && /^https?:\/\/\S+$/.test(text);
			value = row.kind === "string" ? `"${esc(shown)}"` : esc(shown);
			if (link) value = `<a href="${esc(text)}" target="_blank" rel="noopener noreferrer">${value}</a>`;
			value = `<span class="one-json-${row.kind}"${when ? ` title="${esc(frappe.datetime.prettyDate(text))}"` : ""}>${value}</span>`;
		}
		const editable_value = changes && row.size === undefined;
		const tools = [
			changes && row.size !== undefined && !row.nested ? this.icon("plus", __("Add"), "add", "one-json-tool") : "",
			frappe.ui.button.html({ icon: "copy", size: "xs", variant: "ghost", title: __("Copy"), css_class: "one-json-copy one-json-tool", attrs: { "data-action": "copy" } }),
			changes ? this.icon("trash-2", __("Remove"), "remove", "one-json-tool") : "",
		].join("");
		return $(`
			<div class="one-json-row" data-at="${at}" style="padding-inline-start: calc(var(--spacing) * ${2 + row.depth * 4})">
				${caret}${key}<span class="text-muted">:</span> <span class="one-json-value ellipsis${editable_value ? " one-json-editable-part" : ""}">${value}</span>
				${tools}
			</div>`);
	},
};

(() => {
	const Code = frappe.ui.form.ControlCode;
	if (!Code || Object.hasOwn(Code.prototype, "one_json")) return;
	Code.prototype.one_json = true;
	const refresh = Code.prototype.refresh;
	Code.prototype.refresh = function (...args) {
		const said = refresh.apply(this, args);
		onedesk.json_view.field(this);
		return said;
	};
	// A value set from outside (a script, a dialog's set_value) reaches the
	// input without a refresh; the tree follows it there too.
	const set_input = Code.prototype.set_formatted_input;
	Code.prototype.set_formatted_input = function (...args) {
		const said = set_input.apply(this, args);
		if (this.$wrapper) Promise.resolve(said).then(() => onedesk.json_view.field(this));
		return said;
	};
})();
