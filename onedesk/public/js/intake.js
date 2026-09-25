// The Intake panel: what OneAI read in a file or a message, drawn beside it
// by OneCloud's preview and above a message by OneMail. The server says only
// what the reader may see (one_intake/panel.py); this draws it.

frappe.provide("onedesk.intake");

onedesk.intake.MARK = "/assets/onedesk/images/oneai.svg";

onedesk.intake.panel = async ($el, which) => {
	$el.empty();
	let said;
	try {
		said = which.file
			? await frappe.xcall("onedesk.one_intake.panel.for_file", { name: which.file })
			: await frappe.xcall("onedesk.one_intake.panel.for_message", { name: which.message });
	} catch (e) {
		return;
	}
	if (!said || !said.read_by_ai || ["Spam", "Advertising", "Newsletter", "Notification", "Phishing"].includes(said.verdict) && !said.kind) {
		if (said && said.verdict) {
			$el.html(onedesk.intake.junk(said));
			onedesk.intake.bind($el, which, said.name);
		}
		return;
	}
	$el.html(onedesk.intake.slim(said));
	onedesk.intake.bind($el, which, said.name);
};

// Beside a file or above a message the panel is short: what it is, one line
// about it, what OneAI did with it in a word that opens Intake, and Pay,
// Explain and the details behind a button each. Intake itself shows the rest.
onedesk.intake.slim = (said) => {
	const esc = frappe.utils.escape_html;
	const date = (value) => (value ? frappe.datetime.str_to_user(value) : "");
	const acts = said.actions || [];
	const waits = acts.filter((one) => one.level === "Proposed" || (one.level === "Done" && one.audit === "Wrong")).length;
	const done = acts.filter((one) => one.level === "Done").length;
	const due = (said.dates || []).find((one) => one.what === __("Due") || one.what === __("Deadline"));
	const gross = (said.facts || []).find((one) => one.field === "gross");
	const line = [gross ? format_currency(gross.value, gross.currency) : "", due ? `${esc(due.what)} ${date(due.date)}` : ""].filter(Boolean).join(" · ");
	const box = waits ? "waiting" : "done";
	const status = acts.length
		? `<a class="oi-status" href="/app/intake?box=${box}&reading=${encodeURIComponent(said.name)}">${
				waits ? `<span class="oi-chip" data-tone="orange">${esc(__("{0} to decide", [waits]))}</span> ` : ""
			}${esc(done === 1 ? __("OneAI did 1 thing with it") : __("OneAI did {0} things with it", [done]))} →</a>`
		: "";
	const chips = [
		said.kind ? `<span class="oi-chip">${esc(__(said.kind))}</span>` : "",
		said.unsure ? `<span class="oi-chip" data-tone="orange">${__("Unsure")}</span>` : "",
	].join("");
	const toggle = (key, label) => `<button class="btn btn-xs btn-default" data-fold="${key}">${label}</button>`;
	const pay = said.pay ? toggle("pay", said.pay.warn ? __("Do Not Pay Yet") : __("Pay")) : "";
	return `<div class="oi-panel oi-slim">
		<div class="oi-head"><img src="${onedesk.intake.MARK}" alt=""><span>${__("Read by OneAI")}</span>${chips}</div>
		${said.title ? `<div class="oi-name">${esc(said.title)}</div>` : ""}
		${said.summary ? `<div class="oi-summary">${esc(said.summary)}</div>` : ""}
		${line ? `<div class="oi-line">${line}</div>` : ""}
		${status}
		<div class="oi-buttons oi-folds">${pay}
			<button class="btn btn-xs btn-default" data-explain="0" data-again="${said.explained ? 1 : 0}">${said.explained ? __("Explain Again") : __("Explain")}</button>
			${said.may_cancel ? `<button class="btn btn-xs btn-default" data-explain="1">${__("Write the Cancellation")}</button>` : ""}
			${toggle("details", __("Details"))}
		</div>
		<div class="oi-fold hide" data-fold-body="pay">${onedesk.intake.pay(said.pay)}</div>
		<div class="oi-explained">${said.explained ? onedesk.intake.explanation(said.explained) : ""}</div>
		<div class="oi-fold hide" data-fold-body="details">${onedesk.intake.details(said)}</div>
	</div>`;
};

onedesk.intake.junk = (said) => {
	const esc = frappe.utils.escape_html;
	const tone = said.verdict === "Phishing" ? "red" : "gray";
	return `<div class="oi-panel">
		<div class="oi-head"><img src="${onedesk.intake.MARK}" alt=""><span>${__("Read by OneAI")}</span>
		<span class="oi-chip" data-tone="${tone}">${esc(__(said.verdict))}</span></div>
	</div>`;
};

onedesk.intake.html = (said) => {
	const esc = frappe.utils.escape_html;
	const date = (value) => (value ? frappe.datetime.str_to_user(value) : "");
	const chips = [
		said.kind ? `<span class="oi-chip">${esc(__(said.kind))}</span>` : "",
		said.unsure ? `<span class="oi-chip" data-tone="orange">${__("Unsure")}</span>` : "",
		said.sensitivity && said.sensitivity !== "Ordinary" ? `<span class="oi-chip" data-tone="purple">${esc(__(said.sensitivity))}</span>` : "",
	].join("");
	const value = (fact) => {
		if (fact.field === "gross") return format_currency(fact.value, fact.currency);
		if (["issued_on", "valid_until"].includes(fact.field)) return date(fact.value);
		// An IBAN in the groups of four banks print it in, which also lets it wrap.
		if (fact.field === "iban") return String(fact.value).replace(/(.{4})/g, "$1 ").trim();
		return fact.value;
	};
	const facts = (said.facts || []).map((fact) => `<dt>${esc(fact.label)}</dt><dd>${esc(String(value(fact)))}</dd>`).join("");
	const party = (one) => {
		const link = one.record
			? `<a href="/desk/${frappe.router.slug(one.record[0])}/${encodeURIComponent(one.record[1])}">${esc(__(one.record[0]))} ${esc(one.record[1])}</a>`
			: one.ours
			? `<span class="oi-quiet">${one.ours === "Company" ? __("us") : __("a colleague")}</span>`
			: `<span class="oi-quiet">${__("not known yet")}</span>`;
		return `<li><span class="oi-quiet">${esc(one.role)}</span> ${esc(one.name || "")} · ${link}</li>`;
	};
	const list = (title, rows) => (rows.length ? `<div class="oi-title">${title}</div><ul>${rows.join("")}</ul>` : "");
	const parties = list(__("Who"), (said.parties || []).map(party));
	const dates = list(
		__("When"),
		(said.dates || []).map((one) => `<li>${esc(one.what)} ${date(one.date)}${one.about ? ` · ${esc(one.about)}` : ""}</li>`)
	);
	const asks = list(
		__("Asks"),
		(said.asks || []).map((one) => `<li><b>${esc(one.what)}</b>${one.detail ? ` · ${esc(one.detail)}` : ""}${one.by ? ` · ${__("by {0}", [date(one.by)])}` : ""}</li>`)
	);
	const parts = list(
		__("Documents in it"),
		(said.parts || []).map((one) => `<li><span class="oi-quiet">${esc(one.part || "")}</span> ${esc(__(one.kind || ""))} · ${esc(one.title || "")}</li>`)
	);
	const attached = list(
		__("Attachments"),
		(said.attachments || []).map((one) => `<li>${esc(one.file)} · ${esc(__(one.kind || one.state || ""))}${one.title ? ` · ${esc(one.title)}` : ""}</li>`)
	);
	const dropped = (said.dropped || []).length
		? `<details class="oi-dropped"><summary>${__("Not in the document ({0})", [said.dropped.length])}</summary><ul>${said.dropped.map((line) => `<li>${esc(line)}</li>`).join("")}</ul></details>`
		: "";
	if (onedesk.intake.details_only) return `${facts ? `<dl>${facts}</dl>` : ""}${parties}${dates}${asks}${parts}${attached}${dropped}`;
	return `<div class="oi-panel">
		<div class="oi-head"><img src="${onedesk.intake.MARK}" alt=""><span>${__("Read by OneAI")}</span>${chips}</div>
		${said.title ? `<div class="oi-name">${esc(said.title)}</div>` : ""}
		${said.summary ? `<div class="oi-summary">${esc(said.summary)}</div>` : ""}
		${onedesk.intake.matter(said.matter)}
		${facts ? `<dl>${facts}</dl>` : ""}
		${parties}${dates}${asks}${parts}${attached}${dropped}${onedesk.intake.pay(said.pay)}${onedesk.intake.actions(said)}
		${onedesk.intake.explained(said)}
	</div>`;
};

// What was read, in full: the facts, who, when, what it asks.
onedesk.intake.details = (said) => {
	onedesk.intake.details_only = true;
	try {
		return onedesk.intake.html(said);
	} finally {
		onedesk.intake.details_only = false;
	}
};

// ------------------------------------------------------------------ paying it

// Whom to pay, each part ready to copy, and the GiroCode a banking app scans.
// A changed IBAN has no code, only why (one_intake/pay.py).
onedesk.intake.pay = (pay) => {
	if (!pay) return "";
	const esc = frappe.utils.escape_html;
	if (pay.warn) return `<div class="oi-title">${__("Payment")}</div><div class="oi-warn">${esc(pay.warn)}</div>`;
	const copy = (label, value, shown) =>
		value ? `<dt>${label}</dt><dd><button class="oi-copy" data-copy="${esc(String(value))}" title="${__("Copy")}">${esc(String(shown || value))}</button></dd>` : "";
	const iban = String(pay.iban || "").replace(/(.{4})/g, "$1 ").trim();
	const rows = [
		copy(__("To"), pay.name),
		copy(__("IBAN"), pay.iban, iban),
		copy(__("Amount"), pay.amount, pay.amount ? format_currency(pay.amount, pay.currency) : ""),
		copy(__("Reference"), pay.reference),
	].join("");
	const code = pay.code ? `<div class="oi-code" title="${__("Scan with your banking app")}">${pay.code}</div>` : "";
	return `<div class="oi-title">${__("Payment")}</div><div class="oi-pay"><dl>${rows}</dl>${code}</div>`;
};

// ------------------------------------------------------------------ explaining it

onedesk.intake.explained = (said) => {
	const buttons = `<span class="oi-buttons">
		<button class="btn btn-xs btn-default" data-explain="0" data-again="${said.explained ? 1 : 0}">${said.explained ? __("Explain Again") : __("Explain")}</button>
		${said.may_cancel ? `<button class="btn btn-xs btn-default" data-explain="1">${__("Write the Cancellation")}</button>` : ""}</span>`;
	return `<div class="oi-explain">${buttons}<div class="oi-explained">${said.explained ? onedesk.intake.explanation(said.explained) : ""}</div></div>`;
};

onedesk.intake.explanation = (said) => {
	const esc = frappe.utils.escape_html;
	const date = (value) => (value ? frappe.datetime.str_to_user(value) : "");
	const paragraphs = String(said.explanation || "")
		.split(/\n\s*\n/)
		.filter(Boolean)
		.map((one) => `<p>${esc(one)}</p>`)
		.join("");
	const todo = (said.todo || []).length
		? `<div class="oi-title">${__("What to do")}</div><ul>${said.todo
				.map((one) => `<li>${esc(one.what)}${one.by ? ` · ${__("by {0}", [date(one.by)])}` : ""}</li>`)
				.join("")}</ul>`
		: "";
	const reply = said.reply
		? `<div class="oi-title oi-did">${__("Letter")}<button class="btn btn-xs btn-default" data-copy="${esc(said.reply)}">${__("Copy")}</button></div><pre class="oi-letter">${esc(said.reply)}</pre>`
		: "";
	return `${paragraphs}${todo}${reply}`;
};

// ------------------------------------------------------------------ its matter

onedesk.intake.matter = (matter) => {
	if (!matter) return "";
	const esc = frappe.utils.escape_html;
	const doc = matter.document || {};
	const title = doc.route ? `<a href="${esc(doc.route)}">${esc(matter.title || "")}</a>` : esc(matter.title || "");
	const said = matter.copy ? __("A copy of {0}", [title]) : __("About {0}", [title]);
	const change = matter.change && !matter.copy ? ` <span class="oi-chip" data-tone="gray">${esc(matter.change)}</span>` : "";
	return `<div class="oi-matter">${said}${change}</div>`;
};

// ------------------------------------------------------------------ what OneAI did

onedesk.intake.actions = (said) => {
	const esc = frappe.utils.escape_html;
	const rows = said.actions || [];
	if (!rows.length) return "";
	const link = (one) =>
		one.record ? ` · <a href="/desk/${frappe.router.slug(one.record[0])}/${encodeURIComponent(one.record[1])}">${__("Open")}</a>` : "";
	const row = (one) => {
		const waits = one.level === "Proposed";
		const buttons =
			waits && said.may_decide
				? ` <span class="oi-buttons"><button class="btn btn-xs btn-primary" data-settle="${esc(one.name)}" data-take="1">${__("Apply")}</button>
				<button class="btn btn-xs btn-default" data-settle="${esc(one.name)}" data-take="0">${__("Dismiss")}</button></span>`
				: "";
		const chip = waits
			? `<span class="oi-chip" data-tone="orange">${__("Needs a look")}</span> `
			: one.level === "Refused"
			? `<span class="oi-chip" data-tone="gray">${__("Not allowed")}</span> `
			: "";
		const why = waits || one.level === "Refused" ? (one.why ? `<div class="oi-quiet">${esc(one.why)}</div>` : "") : "";
		const change = (one.change || [])
			.map((it) => `<div class="oi-change">${esc(it.field)}: <s>${esc(String(it.from))}</s> → ${esc(String(it.to))}</div>`)
			.join("");
		return `<li>${chip}${esc(one.said)}${link(one)}${change}${buttons}${why}</li>`;
	};
	const done = rows.some((one) => one.level === "Done");
	const undo = done && said.may_decide ? `<button class="btn btn-xs btn-default oi-undo" data-undo="1">${__("Undo")}</button>` : "";
	return `<div class="oi-title oi-did">${__("What OneAI did")}${undo}</div><ul>${rows.map(row).join("")}</ul>`;
};

onedesk.intake.bind = ($el, which, reading) => {
	$el.find("[data-fold]").on("click", (event) => {
		const key = $(event.currentTarget).attr("data-fold");
		$el.find(`[data-fold-body="${key}"]`).toggleClass("hide");
		$(event.currentTarget).toggleClass("active");
	});
	$el.find("[data-copy]").on("click", (event) => {
		frappe.utils.copy_to_clipboard($(event.currentTarget).attr("data-copy"));
	});
	$el.find("[data-explain]").on("click", async (event) => {
		const $button = $(event.currentTarget);
		const cancel = $button.attr("data-explain") === "1";
		$el.find("[data-explain]").prop("disabled", true);
		const $out = $el.find(".oi-explained");
		$out.html(`<div class="oi-quiet">${__("OneAI is reading it…")}</div>`);
		try {
			const said = await frappe.xcall("onedesk.one_intake.explain.explain", {
				reading,
				cancel: cancel ? 1 : 0,
				again: !cancel && $button.attr("data-again") === "1" ? 1 : 0,
			});
			$out.html(onedesk.intake.explanation(said));
			if (!cancel) $button.attr("data-again", "1").text(__("Explain Again"));
			$out.find("[data-copy]").on("click", (e) => frappe.utils.copy_to_clipboard($(e.currentTarget).attr("data-copy")));
		} catch (e) {
			$out.empty();
		}
		$el.find("[data-explain]").prop("disabled", false);
	});
	$el.find("[data-settle]").on("click", async (event) => {
		const $button = $(event.currentTarget);
		$button.prop("disabled", true);
		await frappe.xcall("onedesk.one_intake.act.settle", { action: $button.attr("data-settle"), take: $button.attr("data-take") });
		onedesk.intake.panel($el, which);
	});
	$el.find("[data-undo]").on("click", () => {
		frappe.confirm(__("Take back everything OneAI did with this document?"), async () => {
			const said = await frappe.xcall("onedesk.one_intake.act.undo", { reading });
			onedesk.intake.undone(said);
			onedesk.intake.panel($el, which);
		});
	});
};

onedesk.intake.undone = (said) => {
	const esc = frappe.utils.escape_html;
	if (!(said.kept || []).length) {
		frappe.show_alert({ message: __("Undone."), indicator: "green" });
		return;
	}
	frappe.msgprint({
		title: __("Some of it stays"),
		message: `<ul>${said.kept.map((one) => `<li>${esc(one.target.join(" "))}: ${esc(one.why)}</li>`).join("")}</ul>`,
	});
};

// ------------------------------------------------------------------ the mark in lists

// A record OneAI made and no person has checked carries the OneAI mark beside
// its title in every list (docs/INTAKE.md §4.2). The list asks once per
// render which of its rows are marked, and only for a doctype the boot says
// holds any; a row drawn later (the long list draws as it scrolls) reads the
// same answer when its title is made.
(() => {
	const List = frappe.views && frappe.views.ListView;
	if (!List || List.prototype.one_intake_marked) return;
	List.prototype.one_intake_marked = true;

	const mark = () => {
		const img = document.createElement("img");
		img.className = "one-intake-mark";
		img.src = onedesk.intake.MARK;
		img.alt = __("Made by OneAI");
		img.title = __("Made by OneAI. Nobody has checked it yet.");
		return img;
	};

	const subject = List.prototype.get_subject_element;
	List.prototype.get_subject_element = function (doc, title) {
		const div = subject.call(this, doc, title);
		const link = div.querySelector("a");
		if (link && this.one_unchecked && this.one_unchecked.has(doc.name)) link.before(mark());
		return div;
	};

	const render = List.prototype.render;
	List.prototype.render = function () {
		render.call(this);
		if (!(frappe.boot.one_intake_marked || []).includes(this.doctype)) return;
		frappe
			.xcall("onedesk.one_intake.mark.unchecked", { doctype: this.doctype, names: (this.data || []).map((doc) => doc.name) })
			.then((said) => {
				this.one_unchecked = new Set(said.names);
				for (const name of said.names) {
					const $box = this.$result.find(`.list-row-checkbox[data-name="${CSS.escape(name)}"]`);
					const $subject = $box.closest(".list-subject");
					if ($subject.length && !$subject.find(".one-intake-mark").length) $subject.find("a").first().before(mark());
				}
				onedesk.intake.unchecked_button(this, said);
			});
	};
})();

onedesk.intake.unchecked_button = (list, said) => {
	if (list.one_unchecked_label) list.page.remove_inner_button(list.one_unchecked_label);
	list.one_unchecked_label = null;
	if (!said.total) return;
	const label = said.total === 1 ? __("1 not checked by a person") : __("{0} not checked by a person", [said.total]);
	list.one_unchecked_label = label;
	list.page.add_inner_button(label, () => list.filter_area.add([[list.doctype, "name", "in", said.all]]));
};

// ------------------------------------------------------------------ the banner on a form

$(document).on("form-refresh", (event, frm) => {
	const held = (frm.doc.__onload || {}).one_intake_mark;
	if (!held) return;
	const esc = frappe.utils.escape_html;
	const doc = held.document || {};
	const from = doc.route ? `<a href="${esc(doc.route)}">${esc(doc.label || "")}</a>` : esc(doc.label || "");
	frm.set_intro(
		`<div class="oi-banner"><img src="${onedesk.intake.MARK}" alt="">
		<span>${from ? __("OneAI made this from {0}. Nobody has checked it yet.", [from]) : __("OneAI made this. Nobody has checked it yet.")}</span>
		<span class="oi-buttons"><button class="btn btn-xs btn-default" data-looks-right>${__("Looks right")}</button>
		${held.action ? `<button class="btn btn-xs btn-default" data-undo-one>${__("Undo")}</button>` : ""}</span></div>`,
		"blue"
	);
	const $banner = frm.$intro_message || $();
	$banner.find("[data-looks-right]").on("click", async () => {
		await frappe.xcall("onedesk.one_intake.mark.looks_right", { doctype: frm.doctype, name: frm.docname });
		delete frm.doc.__onload.one_intake_mark;
		frm.set_intro();
		frappe.show_alert({ message: __("Marked as checked."), indicator: "green" });
	});
	$banner.find("[data-undo-one]").on("click", () => {
		frappe.confirm(__("Take back what OneAI made here?"), async () => {
			const said = await frappe.xcall("onedesk.one_intake.act.undo_one", { action: held.action });
			if (said.why) {
				frappe.msgprint(said.why);
				return;
			}
			frappe.show_alert({ message: __("Undone."), indicator: "green" });
			frappe.set_route("List", frm.doctype);
		});
	});
});
