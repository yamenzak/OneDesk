// The website's chat (one_chat/widget.py): a button at the foot of every
// page of the workspace's website, while a channel answers website chats.
// A visitor writes their name, address and question, which opens a room in
// OneChat; the key the server answers is kept in this browser, and the
// conversation is read with it every few seconds while the chat is open.
// A visitor has no user settings, so the key is kept in localStorage.
// Drawn with the DOM alone, since the website loads no desk or frappe-ui;
// every word is a text node, so nothing anybody wrote runs.
(() => {
	const M = "onedesk.one_chat.widget.";
	const KEY = "one_chat_key";
	const EVERY = 3000;
	const SKIPPED = ["/login", "/app", "/desk", "/update-password", "/portal"];

	if (window.one_chat_widget) return;
	window.one_chat_widget = true;
	if (frappe.get_cookie && frappe.get_cookie("system_user") === "yes") return;
	if (SKIPPED.some((path) => location.pathname === path || location.pathname.startsWith(`${path}/`))) return;

	const said = (body) => {
		try {
			const first = JSON.parse(JSON.parse(body._server_messages || "[]")[0] || "{}");
			return frappe.utils?.strip_html ? frappe.utils.strip_html(first.message || "") : first.message || "";
		} catch (e) {
			return "";
		}
	};

	const call = (method, args) =>
		new Promise((resolve, reject) => {
			frappe
				.call({ method: M + method, args: { ...(args || {}) }, statusCode: {} })
				.done((body) => resolve(body.message))
				.fail((xhr) => reject(Object.assign(new Error(said(xhr.responseJSON || {}) || __("Try again in a moment.")), { status: xhr.status })));
		});

	const make = (tag, attrs = {}, ...children) => {
		const el = document.createElement(tag);
		for (const [key, value] of Object.entries(attrs)) {
			if (key === "class") el.className = value;
			else if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
			else el.setAttribute(key, value);
		}
		for (const child of children) el.append(child);
		return el;
	};

	const icon = (path) => {
		const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
		svg.setAttribute("viewBox", "0 0 24 24");
		svg.setAttribute("aria-hidden", "true");
		svg.setAttribute("class", "one-chat-icon");
		svg.innerHTML = path;
		return svg;
	};
	const BUBBLE = '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>';
	const CROSS = '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>';
	const SEND = '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>';

	const draw = (offer) => {
		let token = localStorage.getItem(KEY);
		let last = null;
		let timer = null;
		const seen = new Set();

		const launch = make("button", { type: "button", class: "one-chat-launch", "aria-label": __("Chat"), "aria-expanded": "false" }, icon(BUBBLE));
		const panel = make("section", { class: "one-chat-panel", role: "dialog", "aria-label": offer.title || __("Chat"), hidden: "" });
		const close = make("button", { type: "button", class: "one-chat-close", "aria-label": __("Close"), onclick: () => toggle(false) }, icon(CROSS));
		const head = make("header", { class: "one-chat-head" }, make("div", { class: "one-chat-titles" }, make("h2", { dir: "auto" }, offer.title || __("Chat")), ...(offer.about ? [make("p", { dir: "auto" }, offer.about)] : [])), close);
		const body = make("div", { class: "one-chat-body" });
		const error = make("p", { class: "one-chat-error", role: "alert" });
		panel.append(head, body, error);
		document.body.append(launch, panel);

		const fail = (raised) => (error.textContent = raised.message || String(raised));

		const toggle = (open) => {
			panel.hidden = !open;
			launch.setAttribute("aria-expanded", String(open));
			clearInterval(timer);
			if (!open) return;
			if (token) {
				read();
				timer = setInterval(read, EVERY);
			}
		};
		launch.addEventListener("click", () => toggle(panel.hidden));

		const field = (label, input) => make("label", { class: "one-chat-field" }, make("span", {}, label), input);

		const start = () => {
			body.replaceChildren();
			const name = make("input", { type: "text", autocomplete: "name", required: "", maxlength: "80", dir: "auto" });
			const email = make("input", { type: "email", autocomplete: "email", required: "" });
			const text = make("textarea", { rows: "3", required: "", maxlength: "2000", dir: "auto" });
			const button = make("button", { type: "submit", class: "one-chat-solid" }, __("Start Chat"));
			const form = make(
				"form",
				{
					class: "one-chat-form",
					onsubmit: async (event) => {
						event.preventDefault();
						error.textContent = "";
						button.disabled = true;
						try {
							const got = await call("start", { name: name.value, email: email.value, text: text.value, page: location.pathname });
							token = got.token;
							localStorage.setItem(KEY, token);
							conversation();
							toggle(true);
						} catch (raised) {
							fail(raised);
						} finally {
							button.disabled = false;
						}
					},
				},
				field(__("Name"), name),
				field(__("Email"), email),
				field(__("Message"), text),
				make("p", { class: "one-chat-note", dir: "auto" }, __("{0} keeps this conversation to answer you.", [offer.title || __("This website")])),
				button
			);
			body.append(form);
		};

		const list = make("ol", { class: "one-chat-list", "aria-live": "polite" });
		const ended = make("div", { class: "one-chat-ended", hidden: "" }, make("p", {}, __("This chat has ended.")), make("button", { type: "button", class: "one-chat-subtle", onclick: () => again() }, __("Start a New Chat")));
		const box = make("textarea", { rows: "1", maxlength: "2000", dir: "auto", "aria-label": __("Message"), placeholder: __("Message") });
		const send = make("button", { type: "submit", class: "one-chat-solid one-chat-send", "aria-label": __("Send") }, icon(SEND));
		const composer = make(
			"form",
			{
				class: "one-chat-composer",
				onsubmit: async (event) => {
					event.preventDefault();
					if (!box.value.trim()) return;
					error.textContent = "";
					send.disabled = true;
					try {
						const got = await call("send", { token, text: box.value });
						box.value = "";
						add(got.message);
					} catch (raised) {
						fail(raised);
					} finally {
						send.disabled = false;
					}
				},
			},
			box,
			send
		);
		box.addEventListener("keydown", (event) => {
			if (event.key === "Enter" && !event.shiftKey) {
				event.preventDefault();
				composer.requestSubmit();
			}
		});

		const add = (one) => {
			if (seen.has(one.name)) return;
			seen.add(one.name);
			last = one.at;
			list.append(make("li", { class: one.mine ? "one-chat-mine" : "one-chat-theirs" }, make("span", { class: "one-chat-who", dir: "auto" }, one.who || ""), make("p", { dir: "auto" }, one.text)));
			list.scrollTop = list.scrollHeight;
		};

		const conversation = () => {
			body.replaceChildren(list, ended, composer);
			list.replaceChildren();
			seen.clear();
			last = null;
		};

		const read = async () => {
			try {
				const got = await call("said", { token, ...(last ? { after: last } : {}) });
				for (const one of got.messages) add(one);
				ended.hidden = !got.closed;
				composer.hidden = !!got.closed;
				if (got.closed) clearInterval(timer);
			} catch (raised) {
				if (raised.status === 404) again();
			}
		};

		const again = () => {
			token = null;
			localStorage.removeItem(KEY);
			clearInterval(timer);
			start();
		};

		if (token) conversation();
		else start();
	};

	const ready = async () => {
		try {
			const offer = await call("offered");
			if (offer && offer.on) draw(offer);
		} catch (e) {
			return;
		}
	};
	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready);
	else ready();
})();
