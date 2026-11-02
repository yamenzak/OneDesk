// A Select opens the menu a Link opens (onedesk/one_interface/AGENTS.md,
// Fields). frappe draws a Select as the browser's own <select>, whose list is
// the operating system's: another font, another highlight, and nothing like
// the list a Link field drops a step away on the same form. In Canvas the
// <select> stays frappe's and stays the value; only its list is ours, drawn
// with frappe's own awesomplete classes so it is the Link's list, and a pick
// is handed back to the <select> as a change, which frappe already listens to.
frappe.provide("onedesk.interface");

{
	const WANTED = ".frappe-control select:not([multiple]):not([size])";
	const canvas = () => document.documentElement.dataset.oneLook === "canvas";
	let open = null;

	const close = () => {
		if (!open) return;
		open.wrap.remove();
		open.select.removeAttribute("aria-expanded");
		open = null;
	};

	const mark = (index) => {
		if (!open) return;
		const items = open.items;
		if (!items.length) return;
		open.at = (index + items.length) % items.length;
		items.forEach((li, i) => li.setAttribute("aria-selected", i === open.at ? "true" : "false"));
		items[open.at].scrollIntoView({ block: "nearest" });
	};

	const pick = (index) => {
		if (!open) return;
		const { select, items } = open;
		const value = items[index] && items[index].dataset.value;
		close();
		if (value === undefined || value === select.value) return;
		select.value = value;
		select.dispatchEvent(new Event("input", { bubbles: true }));
		select.dispatchEvent(new Event("change", { bubbles: true }));
		$(select).trigger("select-change");
	};

	const show = (select) => {
		close();
		const wrap = document.createElement("div");
		wrap.className = "awesomplete one-select-menu";
		const list = document.createElement("ul");
		list.setAttribute("role", "listbox");
		const items = [];
		[...select.options].forEach((option) => {
			if (option.hidden || option.disabled) return;
			const li = document.createElement("li");
			li.setAttribute("role", "option");
			li.dataset.value = option.value;
			const text = option.textContent.trim();
			li.textContent = text || "—";
			if (!text) li.classList.add("one-select-none");
			li.addEventListener("mousedown", (event) => {
				event.preventDefault();
				pick(items.indexOf(li));
			});
			li.addEventListener("mousemove", () => open && open.at !== items.indexOf(li) && mark(items.indexOf(li)));
			items.push(li);
			list.append(li);
		});
		if (!items.length) return;
		wrap.append(list);
		place(select, wrap);
		document.body.append(wrap);
		select.setAttribute("aria-expanded", "true");
		open = { select, wrap, items, at: 0, typed: "", typed_at: 0 };
		const current = items.findIndex((li) => li.dataset.value === select.value);
		mark(current < 0 ? 0 : current);
	};

	// The list hangs in its own layer under (or, near the window's foot, over)
	// the box, so a scrolling strip, a table cell or a dialog cannot clip it.
	const place = (select, wrap) => {
		const box = select.getBoundingClientRect();
		const below = window.innerHeight - box.bottom;
		const up = below < 240 && box.top > below;
		wrap.classList.toggle("one-up", up);
		wrap.style.left = `${box.left}px`;
		wrap.style.width = `${box.width}px`;
		wrap.style.top = `${up ? box.top - 4 : box.bottom + 4}px`;
	};

	const usable = (select) => !!select && canvas() && !select.disabled && select.matches(WANTED);

	document.addEventListener(
		"mousedown",
		(event) => {
			const select = event.target.closest && event.target.closest("select");
			if (open && !open.wrap.contains(event.target) && select !== open.select) close();
			if (!usable(select) || event.button !== 0) return;
			event.preventDefault();
			select.focus();
		},
		true
	);

	// The list opens on the click, after frappe's own handlers for it have run:
	// a table's row takes the click to make itself editable and moves focus.
	document.addEventListener(
		"click",
		(event) => {
			const select = event.target.closest && event.target.closest("select");
			if (!usable(select) || event.button !== 0) return;
			setTimeout(() => {
				if (open && open.select === select) close();
				else if (select.isConnected) {
					select.focus();
					show(select);
				}
			});
		},
		true
	);

	document.addEventListener(
		"keydown",
		(event) => {
			const select = event.target;
			if (!(select instanceof HTMLSelectElement) || !usable(select)) return;
			const here = open && open.select === select;
			const key = event.key;
			if (!here) {
				if (key === "Enter" || key === " " || key === "F4" || (event.altKey && key === "ArrowDown")) {
					event.preventDefault();
					show(select);
				}
				return;
			}
			if (key === "ArrowDown" || key === "ArrowUp") mark(open.at + (key === "ArrowDown" ? 1 : -1));
			else if (key === "Home" || key === "End") mark(key === "Home" ? 0 : open.items.length - 1);
			else if (key === "Enter" || key === " ") pick(open.at);
			else if (key === "Escape") close();
			else if (key === "Tab") return close();
			else if (key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
				const now = Date.now();
				open.typed = (now - open.typed_at < 700 ? open.typed : "") + key.toLowerCase();
				open.typed_at = now;
				const found = open.items.findIndex((li) => li.textContent.toLowerCase().startsWith(open.typed));
				if (found >= 0) mark(found);
			} else return;
			event.preventDefault();
			event.stopPropagation();
		},
		true
	);

	document.addEventListener("focusout", (event) => open && event.target === open.select && setTimeout(() => open && document.activeElement !== open.select && close()));
	window.addEventListener("resize", close);
	document.addEventListener("scroll", (event) => open && !open.wrap.contains(event.target) && close(), true);
	$(document).on("page-change", close);

	onedesk.interface.select_menu = { close };
}
