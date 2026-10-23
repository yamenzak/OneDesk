
frappe.provide("onedesk.intake");

onedesk.intake.MARK = "/assets/onedesk/images/oneai.svg";

onedesk.intake.panel = async ($el, which) => {
	if (!onedesk.apps.intake()) return;
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

onedesk.intake.slim = (said) => {
	const esc = frappe.utils.escape_html;
	const date = (value) => (value ? frappe.datetime.str_to_user(value) : "");
	const acts = said.actions || [];
	const waits = acts.filter((one) => one.level === "Proposed" || (one.level === "Done" && one.audit === "Wrong")).length;
	const done = acts.filter((one) => one.level === "Done").length;
	const shown = (one) =>
		one.type === "currency" ? format_currency(one.value, one.currency) : one.type === "date" ? date(one.value) : esc(String(one.value));
	const quick = (said.quick || []).map((one) => `<dt>${esc(one.label)}</dt><dd>${shown(one)}</dd>`).join("");
	const box = waits ? "waiting" : "done";
	const status = acts.length
		? `<a class="oi-status" href="/app/intake?box=${box}&reading=${encodeURIComponent(said.name)}">${
				waits ? `${frappe.ui.badge.html({ label: __("{0} to decide", [waits]), theme: "orange", size: "sm" })} ` : ""
			}${esc(done === 1 ? __("OneAI did 1 thing with it") : __("OneAI did {0} things with it", [done]))} →</a>`
		: "";
	const chips = [
		said.kind ? `${frappe.ui.badge.html({ label: __(said.kind), theme: "blue", size: "sm" })}` : "",
		said.unsure ? `${frappe.ui.badge.html({ label: __("Unsure"), theme: "orange", size: "sm" })}` : "",
	].join("");
	const toggle = (key, label) => frappe.ui.button.html({ label, size: "xs", attrs: { "data-fold": key } });
	const pay = said.pay ? toggle("pay", said.pay.warn ? __("Do Not Pay Yet") : __("Pay")) : "";
	return `<div class="oi-panel oi-slim">
		<div class="oi-head"><img src="${onedesk.intake.MARK}" alt=""><span>${__("Read by OneAI")}</span>${chips}</div>
		${said.title ? `<div class="oi-name">${esc(said.title)}</div>` : ""}
		${said.summary ? `<div class="oi-summary">${esc(said.summary)}</div>` : ""}
		${quick ? `<dl class="oi-quick">${quick}</dl>` : ""}
		${status}
		<div class="oi-buttons oi-folds">${pay}
			${frappe.ui.button.html({ label: said.explained ? __("Explain Again") : __("Explain"), size: "xs", attrs: { "data-explain": "0", "data-again": said.explained ? "1" : "0" } })}
			${said.may_cancel ? frappe.ui.button.html({ label: __("Write Cancellation"), size: "xs", attrs: { "data-explain": "1" } }) : ""}
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
		${frappe.ui.badge.html({ label: __(said.verdict), theme: tone, size: "sm" })}</div>
	</div>`;
};

onedesk.intake.html = (said) => {
	const esc = frappe.utils.escape_html;
	const date = (value) => (value ? frappe.datetime.str_to_user(value) : "");
	const chips = [
		said.kind ? `${frappe.ui.badge.html({ label: __(said.kind), theme: "blue", size: "sm" })}` : "",
		said.unsure ? `${frappe.ui.badge.html({ label: __("Unsure"), theme: "orange", size: "sm" })}` : "",
		said.sensitivity && said.sensitivity !== "Ordinary" ? `${frappe.ui.badge.html({ label: __(said.sensitivity), theme: "violet", size: "sm" })}` : "",
	].join("");
	const value = (fact) => {
		if (fact.field === "gross") return format_currency(fact.value, fact.currency);
		if (["issued_on", "valid_until"].includes(fact.field)) return date(fact.value);
		if (fact.field === "iban") return String(fact.value).replace(/(.{4})/g, "$1 ").trim();
		return fact.value;
	};
	const facts = (said.facts || []).map((fact) => `<dt>${esc(fact.label)}</dt><dd>${esc(String(value(fact)))}</dd>`).join("");
	const party = (one) => {
		const link = one.record
			? `<a href="/desk/${frappe.router.slug(one.record[0])}/${encodeURIComponent(one.record[1])}">${esc(__(one.record[0]))} ${esc(one.record[1])}</a>`
			: one.ours
			? `<span class="one-shell-quiet">${one.ours === "Company" ? __("us") : __("a colleague")}</span>`
			: `<span class="one-shell-quiet">${__("not known yet")}</span>`;
		return `<li><span class="one-shell-quiet">${esc(one.role)}</span> ${esc(one.name || "")} · ${link}</li>`;
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
		__("Documents"),
		(said.parts || []).map((one) => `<li><span class="one-shell-quiet">${esc(one.part || "")}</span> ${esc(__(one.kind || ""))} · ${esc(one.title || "")}</li>`)
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

onedesk.intake.details = (said) => {
	onedesk.intake.details_only = true;
	try {
		return onedesk.intake.html(said);
	} finally {
		onedesk.intake.details_only = false;
	}
};

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

onedesk.intake.explained = (said) => {
	const buttons = `<span class="oi-buttons">
		${frappe.ui.button.html({ label: said.explained ? __("Explain Again") : __("Explain"), size: "xs", attrs: { "data-explain": "0", "data-again": said.explained ? "1" : "0" } })}
		${said.may_cancel ? frappe.ui.button.html({ label: __("Write Cancellation"), size: "xs", attrs: { "data-explain": "1" } }) : ""}</span>`;
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
		? `<div class="oi-title oi-did">${__("Letter")}${frappe.ui.button.html({ label: __("Copy"), size: "xs", attrs: { "data-copy": said.reply } })}</div><pre class="oi-letter">${esc(said.reply)}</pre>`
		: "";
	return `${paragraphs}${todo}${reply}`;
};

onedesk.intake.matter = (matter) => {
	if (!matter) return "";
	const esc = frappe.utils.escape_html;
	const doc = matter.document || {};
	const title = doc.route ? `<a href="${esc(doc.route)}">${esc(matter.title || "")}</a>` : esc(matter.title || "");
	const said = matter.copy ? __("A copy of {0}", [title]) : __("About {0}", [title]);
	const change = matter.change && !matter.copy ? ` ${frappe.ui.badge.html({ label: matter.change, theme: "gray", size: "sm" })}` : "";
	return `<div class="oi-matter">${said}${change}</div>`;
};

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
				? ` <span class="oi-buttons">${frappe.ui.button.html({ label: __("Apply"), size: "xs", variant: "solid", attrs: { "data-settle": one.name, "data-take": "1" } })}
				${frappe.ui.button.html({ label: __("Dismiss"), size: "xs", attrs: { "data-settle": one.name, "data-take": "0" } })}</span>`
				: "";
		const chip = waits
			? `${frappe.ui.badge.html({ label: __("Needs Review"), theme: "orange", size: "sm" })} `
			: one.level === "Refused"
			? `${frappe.ui.badge.html({ label: __("Not allowed"), theme: "gray", size: "sm" })} `
			: "";
		const why = waits || one.level === "Refused" ? (one.why ? `<div class="one-shell-quiet">${esc(one.why)}</div>` : "") : "";
		const change = (one.change || [])
			.map((it) => `<div class="oi-change">${esc(it.field)}: <s>${esc(String(it.from))}</s> → ${esc(String(it.to))}</div>`)
			.join("");
		return `<li>${chip}${esc(one.said)}${link(one)}${change}${buttons}${why}</li>`;
	};
	const done = rows.some((one) => one.level === "Done");
	const undo = done && said.may_decide ? frappe.ui.button.html({ label: __("Undo"), size: "xs", css_class: "oi-undo", attrs: { "data-undo": "1" } }) : "";
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
		$out.html(`<div class="one-shell-quiet">${cancel ? __("Writing…") : __("Explaining…")}</div>`);
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
		frappe.confirm(__("Undo everything OneAI did with this document?"), async () => {
			const said = await frappe.xcall("onedesk.one_intake.act.undo", { reading });
			onedesk.intake.undone(said);
			onedesk.intake.panel($el, which);
		});
	});
};

onedesk.intake.undone = (said) => {
	const esc = frappe.utils.escape_html;
	if (!(said.kept || []).length) {
		frappe.show_alert({ message: __("Undone"), indicator: "green" });
		return;
	}
	frappe.msgprint({
		title: __("Some Changes Kept"),
		message: `<ul>${said.kept.map((one) => `<li>${esc(one.target.join(" "))}: ${esc(one.why)}</li>`).join("")}</ul>`,
	});
};

$(document).on("form-refresh", (event, frm) => {
	const held = (frm.doc.__onload || {}).one_intake_mark;
	if (!held) return;
	const esc = frappe.utils.escape_html;
	const doc = held.document || {};
	const from = doc.route ? `<a href="${esc(doc.route)}">${esc(doc.label || "")}</a>` : esc(doc.label || "");
	frm.set_intro(
		`<div class="oi-banner"><img src="${onedesk.intake.MARK}" alt="">
		<span>${from ? __("Made by OneAI from {0}. Not checked yet.", [from]) : __("Made by OneAI. Not checked yet.")}</span>
		<span class="oi-buttons">${frappe.ui.button.html({ label: __("Mark as Checked"), size: "xs", attrs: { "data-looks-right": true } })}
		${held.action ? frappe.ui.button.html({ label: __("Undo"), size: "xs", attrs: { "data-undo-one": true } }) : ""}</span></div>`,
		"blue"
	);
	const $banner = frm.$intro_message || $();
	$banner.find("[data-looks-right]").on("click", async () => {
		await frappe.xcall("onedesk.one_intake.mark.looks_right", { doctype: frm.doctype, name: frm.docname });
		delete frm.doc.__onload.one_intake_mark;
		frm.set_intro();
		frappe.show_alert({ message: __("Marked as checked"), indicator: "green" });
	});
	$banner.find("[data-undo-one]").on("click", () => {
		frappe.confirm(__("Undo what OneAI did here?"), async () => {
			const said = await frappe.xcall("onedesk.one_intake.act.undo_one", { action: held.action });
			if (said.why) {
				frappe.msgprint(said.why);
				return;
			}
			frappe.show_alert({ message: __("Undone"), indicator: "green" });
			frappe.set_route("List", frm.doctype);
		});
	});
});
