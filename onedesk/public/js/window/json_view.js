// OneInterface's JSON viewer (docs/ONEINTERFACE.md): a field that holds JSON
// and can't be edited is shown as a tree that folds by level. Its frame is
// framed the way frappe frames a child table with its filter row: a
// bordered, rounded box, a gray heading strip with frappe's buttons, a white
// strip under it with frappe's own small input (find a key or a value, at any
// depth) and frappe's buttons. A field that can be edited keeps frappe's
// code editor.
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
	// index and, for an object or a list, what it holds.
	rows(json) {
		const rows = [];
		const walk = (value, key, path, depth, parent, in_array) => {
			const nested = this.kind(value) === "string" ? this.parse(value) : undefined;
			const inner = nested !== undefined ? nested : value;
			const kind = this.kind(inner);
			const row = { key, path, depth, parent, in_array, value, kind, nested: nested !== undefined };
			rows.push(row);
			if (kind === "object" || kind === "array") {
				const at = rows.length - 1;
				row.size = Object.keys(inner).length;
				for (const one of Object.keys(inner)) walk(inner[one], one, this.path(path, one, kind === "array"), depth + 1, at, kind === "array");
			}
		};
		for (const one of Object.keys(json)) walk(json[one], one, this.path("", one, Array.isArray(json)), 0, -1, Array.isArray(json));
		return rows;
	},

	// A field on a form: the tree instead of frappe's read-only text, while
	// the field is read-only and what it holds is JSON.
	field(control) {
		const value = control.value ?? (control.get_value && control.get_value());
		const json = control.get_status && control.get_status() === "Read" ? this.parse(value) : undefined;
		let $view = control.$wrapper.find(".one-json").first();
		if (json === undefined) {
			$view.remove();
			return;
		}
		if ($view.length && $view.data("source") === value) {
			this.raw($view, control, !!$view.data("raw"));
			return;
		}
		$view.remove();
		$view = this.draw(json, control).data("source", value);
		$(control.disp_area).before($view);
		this.raw($view, control, false);
	},

	// Tree or the stored text, laid out with two spaces a level. frappe's
	// own read-only display and its copy button stay hidden: Copy in the
	// heading copies what is stored.
	raw($view, control, raw) {
		$view.data("raw", raw);
		$view.find(".one-json-filter, .one-json-body, [data-action=open], [data-action=fold]").toggleClass("hide", raw);
		$view.find(".one-json-text").toggleClass("hide", !raw);
		$view.find("[data-action=raw] .es-button__label").text(raw ? __("Show Tree") : __("Show Raw"));
		$(control.disp_area).addClass("hide");
		control.copy_button && control.copy_button.addClass("hide");
	},

	draw(json, control) {
		const esc = frappe.utils.escape_html;
		const rows = this.rows(json);
		const open = rows.length <= this.SMALL ? Infinity : this.OPEN;
		const button = (label, action) => frappe.ui.button.html({ label, size: "sm", variant: "outline", attrs: { "data-action": action } });
		const count = rows.length === 1 ? __("1 key") : __("{0} keys", [rows.length]);
		const $view = $(`
			<div class="one-json">
				<div class="one-json-head">
					<div class="ellipsis one-json-where">${esc(count)}</div>
					${button(__("Expand All"), "open")}
					${button(__("Collapse All"), "fold")}
					${button(__("Show Raw"), "raw")}
					${button(__("Copy"), "all")}
				</div>
				<div class="one-json-filter">
					<input type="text" class="form-control input-xs one-json-find" placeholder="${esc(__("Find a key or a value"))}" aria-label="${esc(__("Find a key or a value"))}">
				</div>
				<div class="one-json-body">
					<div class="one-json-rows"></div>
					<div class="text-muted small one-json-none hide">${esc(__("Nothing matches"))}</div>
				</div>
				<pre class="one-json-text hide">${esc(JSON.stringify(json, null, 2))}</pre>
			</div>`);
		const $rows = $view.find(".one-json-rows");
		const $made = rows.map((row, at) => this.row(row, at).appendTo($rows));
		const opened = new Set(rows.map((row, at) => (row.size !== undefined && row.depth < open ? at : null)).filter((at) => at !== null));

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
				for (let up = row.parent; shown && up >= 0; up = rows[up].parent) shown = word ? kept.has(up) : opened.has(up);
				$made[at].toggleClass("hide", !shown).toggleClass("one-json-hit", hit[at]);
				$made[at].find(".one-json-caret").toggleClass("open", word ? true : opened.has(at));
			});
			$view.find(".one-json-none").toggleClass("hide", !word || kept.size > 0);
		};
		show();

		const at = (event) => Number($(event.currentTarget).closest(".one-json-row").attr("data-at"));
		$view.on("click", ".one-json-caret", (event) => {
			const one = at(event);
			opened.has(one) ? opened.delete(one) : opened.add(one);
			show();
		});
		$view.on("click", "[data-action=open]", () => {
			rows.forEach((row, one) => row.size !== undefined && opened.add(one));
			show();
		});
		$view.on("click", "[data-action=fold]", () => {
			opened.clear();
			show();
		});
		$view.on("click", "[data-action=raw]", () => this.raw($view, control, !$view.data("raw")));
		$view.on("click", "[data-action=copy]", (event) => {
			const row = rows[at(event)];
			frappe.utils.copy_to_clipboard(row.size === undefined ? String(row.value) : JSON.stringify(row.nested ? JSON.parse(row.value) : row.value, null, 2));
		});
		$view.on("mouseenter", ".one-json-row", (event) => $view.find(".one-json-where").text(rows[at(event)].path));
		$view.on("click", "[data-action=all]", () => frappe.utils.copy_to_clipboard(control.value));
		$view.on("mouseleave", ".one-json-rows", () => $view.find(".one-json-where").text(count));
		$view.find(".one-json-find").on("input", frappe.utils.debounce(show, 150));
		return $view;
	},

	row(row, at) {
		const esc = frappe.utils.escape_html;
		const caret =
			row.size !== undefined
				? frappe.ui.button.html({ icon: "chevron-right", size: "xs", variant: "ghost", title: __("Fold or unfold"), css_class: "one-json-caret" })
				: `<span class="one-json-caret-space"></span>`;
		const key = `<span class="${row.in_array ? "text-muted" : "one-json-key"}">${esc(String(row.key))}</span>`;
		let value;
		if (row.size !== undefined) {
			const size = row.kind === "array" ? `[${row.size}]` : `{${row.size}}`;
			value = `<span class="text-muted">${esc(size)}</span>${row.nested ? ` <span class="indicator-pill no-indicator-dot violet">${esc(__("JSON in text"))}</span>` : ""}`;
		} else {
			const text = row.kind === "string" ? row.value : String(row.value);
			const shown = text.length > this.LONG ? `${text.slice(0, this.LONG)}…` : text;
			const when = row.kind === "string" && /^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?$/.test(text);
			const link = row.kind === "string" && /^https?:\/\/\S+$/.test(text);
			value = row.kind === "string" ? `"${esc(shown)}"` : esc(shown);
			if (link) value = `<a href="${esc(text)}" target="_blank" rel="noopener noreferrer">${value}</a>`;
			value = `<span class="one-json-${row.kind}"${when ? ` title="${esc(frappe.datetime.prettyDate(text))}"` : ""}>${value}</span>`;
		}
		return $(`
			<div class="one-json-row" data-at="${at}" style="padding-inline-start: calc(var(--spacing) * ${2 + row.depth * 4})">
				${caret}${key}<span class="text-muted">:</span> <span class="one-json-value ellipsis">${value}</span>
				${frappe.ui.button.html({ icon: "copy", size: "xs", variant: "ghost", title: __("Copy"), css_class: "one-json-copy", attrs: { "data-action": "copy" } })}
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
})();
