// A source's form is mostly a read view: what it is, when it was last
// fetched and its newest headlines. What the workspace controls stays
// editable (name, category, how often, how many to keep, OneAI's brief);
// what came from the source, or was chosen when it was added, does not.
frappe.ui.form.on("News Source", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.kind === "Written") {
			frm.add_custom_button(__("Write an Item"), () => frappe.new_doc("News Item", { source: frm.doc.name }));
		} else if (frm.perm[0]?.write) {
			frm.add_custom_button(__("Fetch Now"), () =>
				frappe.xcall("onedesk.one.news.fetching.fetch_now", { name: frm.doc.name }).then(() =>
					frappe.show_alert({ message: __("Fetching news. New items will appear shortly."), indicator: "blue" })
				)
			);
		}
		frm.add_custom_button(__("View Items"), () => frappe.set_route("List", "News Item", { source: frm.doc.name }));
		if (frm.doc.last_error) frm.dashboard.set_headline_alert(frappe.utils.escape_html(frm.doc.last_error), "orange");
		latest(frm);
	},
});

const latest = async (frm) => {
	const esc = frappe.utils.escape_html;
	const $at = frm.fields_dict.latest.$wrapper.addClass("one-news-body");
	const said = await frappe.xcall("onedesk.one.news.adding.latest", { name: frm.doc.name });
	// What the source is, on one line, in place of the fields it was made with
	const doc = frm.doc;
	const what = {
		Feed: [doc.website || doc.feed_url].map((one) => (one || "").replace(/^https?:\/\/(www\.)?/, "").replace(/\/.*$/, "")),
		"Google News": [doc.google_query ? `“${doc.google_query}”` : __(doc.google_topic || "Top Stories"), doc.country, doc.language],
		OneAI: [doc.country, doc.language, doc.fetch_at ? __("Runs at {0}", [doc.fetch_at]) : ""],
		Written: [],
	}[doc.kind].filter(Boolean);
	const when =
		doc.kind === "Written"
			? ""
			: said.fetched
			? __("Fetched {0}. Next fetch at {1}.", [said.fetched, said.next])
			: __("Not fetched yet. The first headlines arrive within a few minutes.");
	const line = [what.join(" · "), when].filter(Boolean).join(" · ");
	$at.html(`
		${line ? `<p class="one-news-quiet">${esc(line)}</p>` : ""}
		${
			said.items.length
				? `<ul class="one-news-headlines">${said.items
						.map(
							(one) => `<li><a class="one-news-headline" href="${esc(one.link || `/desk/news-item/${encodeURIComponent(one.name)}`)}" ${
								one.link ? 'target="_blank" rel="noopener"' : ""
							}>${esc(one.title)}</a><span class="one-news-ago">${esc(one.ago)}</span></li>`
						)
						.join("")}</ul>`
				: `<p class="one-news-quiet">${esc(__("No headlines yet."))}</p>`
		}`);
};
