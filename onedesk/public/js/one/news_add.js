// Add News Source (one/news/adding.py). The first screen asks where the
// news comes from, one row per way; each way is then a screen of its own
// with only what it needs, laid out on one column and one spacing scale
// (css/one/news_add.css). Every way of making a News Source opens this
// (onedesk.window.creators).
frappe.provide("onedesk.news");
frappe.provide("onedesk.window.creators");

onedesk.news.WAYS = [
	{ way: "site", kind: "Feed", icon: "globe", label: __("Website"), text: __("Paste a news site's address and see its latest headlines.") },
	{ way: "library", kind: "Feed", icon: "library", label: __("From the Library"), text: __("Pick news sites near you, several at once.") },
	{ way: "google", kind: "Google News", icon: "search", label: __("Google News"), text: __("Top stories on a topic, or headlines for a search. For preview only.") },
	{ way: "ai", kind: "OneAI", icon: "sparkles", label: __("OneAI"), text: __("OneAI searches the web for the news you describe. Each run uses credits.") },
	{ way: "written", kind: "Written", icon: "pen-line", label: __("Written by You"), text: __("News you write yourself, for example company updates.") },
];

onedesk.news.TOPICS = ["Top Stories", "World", "Business", "Technology", "Science", "Health", "Sports", "Entertainment"];

onedesk.news.add = ({ after_insert = null } = {}) =>
	new Promise((resolve) => {
		const esc = frappe.utils.escape_html;
		let context = { google: false, country: "", language: "en" };
		let made = null;
		let way = "";
		let controls = {};
		let found = null;
		const picked = new Set();

		const dialog = new frappe.ui.Dialog({
			title: __("Add News Source"),
			size: "large",
			fields: [{ fieldtype: "HTML", fieldname: "body" }],
			secondary_action_label: __("Back"),
			secondary_action: () => show(""),
		});
		dialog.$wrapper.addClass("one-news-add");
		const $body = dialog.get_field("body").$wrapper.addClass("one-news-body");

		const control = ($at, df) => {
			const one = frappe.ui.form.make_control({ df, parent: $at[0], render_input: true });
			one.refresh();
			controls[df.fieldname] = one;
			return one;
		};
		const value = (name) => (controls[name] ? controls[name].get_value() : "") || "";
		const cell = () => $(`<div class="one-news-cell"></div>`);
		const pair = ($at) => {
			const $a = cell();
			const $b = cell();
			$(`<div class="one-news-pair"></div>`).append($a, $b).appendTo($at);
			return [$a, $b];
		};
		const face = (one) =>
			one.logo ? `<img class="one-news-logo" src="${esc(one.logo)}" alt="">` : `<span class="one-news-logo">${frappe.get_avatar("avatar-small", one.name)}</span>`;
		const headlines = (list) =>
			`<ul class="one-news-headlines">${list
				.map((one) => `<li><span class="one-news-headline">${esc(one.title)}</span><span class="one-news-ago">${esc(one.ago)}</span></li>`)
				.join("")}</ul>`;

		// Name and Category, the same two fields last on every way that makes one source
		const naming = ($at, name = "") => {
			const [$a, $b] = pair($at);
			control($a, { fieldtype: "Data", fieldname: "name", label: __("Name") }).set_value(name);
			control($b, { fieldtype: "Link", fieldname: "category", label: __("Category"), options: "News Category", placeholder: __("Optional") });
		};

		const show = (next) => {
			way = next;
			controls = {};
			found = null;
			picked.clear();
			$body.empty();
			const chosen = onedesk.news.WAYS.find((one) => one.way === way);
			dialog.set_title(chosen ? chosen.label : __("Add News Source"));
			dialog.$wrapper.toggleClass("one-news-choosing", !way);
			({ "": ways, site, library, google, ai, written })[way]();
			refresh();
		};

		const refresh = () => {
			const count = {
				site: () => (found && !found.there ? 1 : 0),
				library: () => picked.size,
				google: () => (context.google ? 1 : 0),
				ai: () => (value("ai_brief").trim() ? 1 : 0),
				written: () => (value("name").trim() ? 1 : 0),
			}[way];
			if (!count) return;
			const n = count();
			dialog.set_primary_action(n > 1 ? __("Add {0} Sources", [n]) : __("Add Source"), () => add());
			dialog.get_primary_btn().prop("disabled", !n);
		};
		$body.on("input change", "input, textarea, select", () => requestAnimationFrame(refresh));

		// Where the news comes from
		const ways = () => {
			$body.append(
				`<div class="one-news-ways">${onedesk.news.WAYS.map(
					(one) => `<button type="button" class="one-news-way" data-way="${one.way}">
						<span class="one-news-way-icon">${frappe.utils.icon(one.icon, "md")}</span>
						<span class="one-news-way-text"><span class="one-news-way-label">${esc(one.label)}</span><span class="one-news-quiet">${esc(one.text)}</span></span>
						<span class="one-news-way-go">${frappe.utils.icon("chevron-right", "sm")}</span>
					</button>`
				).join("")}</div>`
			);
		};
		$body.on("click", ".one-news-way", (e) => show(e.currentTarget.dataset.way));

		// A website, from its address
		const site = () => {
			const address = control(cell().appendTo($body), {
				fieldtype: "Data",
				fieldname: "address",
				label: __("Website or Feed Address"),
				placeholder: "khaleejtimes.com",
			});
			const $result = $(`<div class="one-news-result-at"></div>`).appendTo($body);
			let asked = 0;
			const look = async () => {
				const typed = (address.get_value() || "").trim();
				found = null;
				$result.empty();
				refresh();
				if (!typed) return;
				const mine = ++asked;
				$result.html(`<p class="one-news-quiet">${esc(__("Looking for the site's feed…"))}</p>`);
				const said = await frappe.xcall("onedesk.one.news.adding.find", { url: typed });
				if (mine !== asked) return;
				if (said.error) return $result.html(`<p class="one-news-problem">${esc(said.error)}</p>`);
				found = said;
				const $card = $(`<div class="one-news-result">
					<div class="one-news-site">${face(said)}<span class="one-news-site-text"><span class="one-news-site-name">${esc(said.name)}</span><span class="one-news-quiet">${esc(said.site)}</span></span></div>
					${headlines(said.headlines)}
				</div>`);
				$result.empty().append($card);
				if (said.there) $card.append(`<p class="one-news-quiet">${esc(__("Already added as {0}.", [said.there]))}</p>`);
				else naming($card, said.name);
				refresh();
			};
			address.$input.on("input", frappe.utils.debounce(look, 700));
			setTimeout(() => address.$input.trigger("focus"), 200);
		};

		// The library
		const library = () => {
			$body.append(`<div class="one-news-filters">
				<input type="text" class="form-control one-news-search" placeholder="${esc(__("Search by name or address"))}">
				<select class="form-control one-news-category"><option value="">${esc(__("All Categories"))}</option></select>
				<select class="form-control one-news-country"><option value="">${esc(__("Near You"))}</option></select>
			</div>
			<div class="one-news-rows"></div>
			<p class="one-news-quiet">${esc(__("These feeds belong to their publishers. You need each publisher's permission to show their content."))}</p>`);
			let asked = 0;
			let filled = false;
			const search = async () => {
				const mine = ++asked;
				const said = await frappe.xcall("onedesk.one.news.library.search", {
					query: $body.find(".one-news-search").val() || "",
					category: $body.find(".one-news-category").val() || "",
					country: $body.find(".one-news-country").val() || "",
				});
				if (mine !== asked) return;
				if (!filled) {
					filled = true;
					$body.find(".one-news-category").append(said.categories.map((one) => `<option value="${esc(one)}">${esc(__(one))}</option>`));
					$body.find(".one-news-country").append(said.countries.map((one) => `<option value="${esc(one)}">${esc(one)}</option>`));
				}
				const $rows = $body.find(".one-news-rows").empty();
				if (!said.feeds.length) return $rows.html(`<p class="one-news-quiet one-news-none">${esc(__("No feeds found."))}</p>`);
				for (const one of said.feeds) {
					const $row = $(`<div class="one-news-row" data-url="${esc(one.url)}">
						<label class="one-news-row-main">
							<input type="checkbox" class="one-news-pick" ${one.added ? "checked disabled" : picked.has(one.url) ? "checked" : ""}>
							${face(one)}
							<span class="one-news-site-text"><span class="one-news-site-name">${esc(one.name)}</span>
							<span class="one-news-quiet">${esc(one.added ? __("Added") : [__(one.category), one.country, one.site].filter(Boolean).join(" · "))}</span></span>
						</label>
						<div class="one-news-row-more"></div>
					</div>`).appendTo($rows);
					$row.find(".one-news-row-main").after(frappe.ui.button({ label: __("Preview"), variant: "ghost", size: "sm" }).addClass("one-news-preview"));
				}
				if (said.more) $rows.append(`<p class="one-news-quiet one-news-none">${esc(__("{0} more feeds match. Refine your search to see them.", [said.more]))}</p>`);
			};
			const again = frappe.utils.debounce(search, 300);
			$body.on("input", ".one-news-search", again);
			$body.on("change", ".one-news-category, .one-news-country", again);
			search();
		};
		$body.on("change", ".one-news-pick", (e) => {
			const url = $(e.currentTarget).closest(".one-news-row").data("url");
			if (e.currentTarget.checked) picked.add(url);
			else picked.delete(url);
			refresh();
		});
		$body.on("click", ".one-news-preview", async (e) => {
			const $row = $(e.currentTarget).closest(".one-news-row");
			const $more = $row.find(".one-news-row-more");
			if ($more.children().length) return $more.empty();
			$more.html(`<p class="one-news-quiet">${esc(__("Loading…"))}</p>`);
			const said = await frappe.xcall("onedesk.one.news.adding.find", { url: $row.data("url") });
			$more.html(said.error ? `<p class="one-news-problem">${esc(said.error)}</p>` : headlines(said.headlines));
		});

		// Where a search looks, for the two kinds that search
		const where = () => {
			const [$a, $b] = pair($body);
			control($a, { fieldtype: "Link", fieldname: "country", label: __("Country"), options: "Country" }).set_value(context.country);
			control($b, { fieldtype: "Link", fieldname: "language", label: __("Language"), options: "Language" }).set_value(context.language);
		};

		const google = () => {
			$body.append(
				context.google
					? `<p class="one-news-quiet">${esc(__("For preview only. Showing these headlines publicly may require each publisher's permission."))}</p>`
					: `<p class="one-news-problem">${esc(__("Google News is turned off. Turn it on in TrustCenter."))}</p>`
			);
			const [$a, $b] = pair($body);
			control($a, { fieldtype: "Select", fieldname: "google_topic", label: __("Topic"), options: onedesk.news.TOPICS.map((one) => ({ value: one, label: __(one) })) }).set_value(
				"Top Stories"
			);
			control($b, { fieldtype: "Data", fieldname: "google_query", label: __("Search For"), placeholder: __("Optional. Used instead of the topic.") });
			where();
			naming($body);
		};

		const ai = () => {
			control(cell().appendTo($body), { fieldtype: "Small Text", fieldname: "ai_brief", label: __("Look For"), placeholder: __("Construction and building materials news") });
			const [$a] = pair($body);
			control($a, { fieldtype: "Data", fieldname: "fetch_at", label: __("Times"), placeholder: "07:00, 13:00" }).set_value("07:00");
			where();
			naming($body);
		};

		const written = () => naming($body);

		const add = async () => {
			const names = [];
			const kind = onedesk.news.WAYS.find((one) => one.way === way).kind;
			const base = { kind, name: value("name"), category: value("category") };
			const searching = { country: value("country"), language: value("language") };
			dialog.get_primary_btn().prop("disabled", true);
			try {
				if (way === "site") names.push(await frappe.xcall("onedesk.one.news.adding.add", { ...base, feed_url: found.url }));
				if (way === "library") names.push(...(await frappe.xcall("onedesk.one.news.adding.add_many", { urls: [...picked] })));
				if (way === "google") names.push(await frappe.xcall("onedesk.one.news.adding.add", { ...base, ...searching, google_topic: value("google_topic"), google_query: value("google_query") }));
				if (way === "ai") names.push(await frappe.xcall("onedesk.one.news.adding.add", { ...base, ...searching, ai_brief: value("ai_brief"), fetch_at: value("fetch_at") }));
				if (way === "written") names.push(await frappe.xcall("onedesk.one.news.adding.add", base));
			} catch (e) {
				return refresh();
			}
			made = names[0] || null;
			dialog.hide();
			if (after_insert && made) return frappe.model.with_doc("News Source", made).then(() => after_insert(frappe.get_doc("News Source", made)));
			if (names.length > 1) {
				frappe.show_alert({ message: __("{0} sources added. Their first headlines arrive within a few minutes.", [names.length]), indicator: "green" });
				if (window.cur_list && cur_list.doctype === "News Source") cur_list.refresh();
			} else if (made) frappe.set_route("Form", "News Source", made);
		};

		dialog.onhide = () => resolve(made ? { name: made } : null);
		dialog.show();
		show("");
		frappe.xcall("onedesk.one.news.adding.start").then((said) => (context = said));
	});

onedesk.window.creators["News Source"] = onedesk.news.add;
