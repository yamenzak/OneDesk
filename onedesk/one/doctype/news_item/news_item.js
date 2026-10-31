// A headline fetched from a source is read, not edited: its picture,
// publisher, title and summary, with Open Article and Hide Headline. A
// written one keeps its form. Hidden is read everywhere headlines are
// (news.items), so a hidden one leaves the bar and every screen.
const FETCHED_FIELDS = ["title", "source", "category", "published", "image", "link", "summary", "body", "publisher_section", "about_section", "hidden_item"];

frappe.ui.form.on("News Item", {
	refresh(frm) {
		const fetched = !frm.is_new() && !frm.doc.written;
		FETCHED_FIELDS.forEach((field) => frm.toggle_display(field, !fetched));
		frm.toggle_display("article", fetched);
		frm.toggle_display("item_section", !fetched);
		if (frm.is_new()) return;
		const hidden = !!frm.doc.hidden_item;
		frm.add_custom_button(hidden ? __("Show Headline") : __("Hide Headline"), () => {
			frm.set_value("hidden_item", hidden ? 0 : 1);
			frm.save();
		});
		if (!fetched) return;
		frm.disable_save();
		if (frm.doc.link) frm.add_custom_button(__("Open Article"), () => window.open(frm.doc.link, "_blank", "noopener"));
		article(frm);
	},
});

const article = (frm) => {
	const esc = frappe.utils.escape_html;
	const doc = frm.doc;
	const when = doc.published ? frappe.datetime.prettyDate(doc.published) : "";
	frm.fields_dict.article.$wrapper.html(`<div class="one-news-article${doc.image ? "" : " one-news-article-bare"}">
		<div class="one-news-article-text">
			<div class="one-news-quiet">${esc([doc.publisher || doc.source, when].filter(Boolean).join(" · "))}</div>
			<h2 class="one-news-article-title">${esc(doc.title)}</h2>
			${doc.summary && doc.summary !== doc.title ? `<p class="one-news-article-summary">${esc(doc.summary)}</p>` : ""}
		</div>
		${doc.image ? `<img class="one-news-article-image" src="${esc(doc.image)}" alt="" referrerpolicy="no-referrer">` : ""}
	</div>`);
};
