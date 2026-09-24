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
		if (said && said.verdict) $el.html(onedesk.intake.junk(said));
		return;
	}
	$el.html(onedesk.intake.html(said));
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
	return `<div class="oi-panel">
		<div class="oi-head"><img src="${onedesk.intake.MARK}" alt=""><span>${__("Read by OneAI")}</span>${chips}</div>
		${said.title ? `<div class="oi-name">${esc(said.title)}</div>` : ""}
		${said.summary ? `<div class="oi-summary">${esc(said.summary)}</div>` : ""}
		${facts ? `<dl>${facts}</dl>` : ""}
		${parties}${dates}${asks}${parts}${attached}${dropped}
	</div>`;
};
