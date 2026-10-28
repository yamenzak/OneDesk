// Stripe's own Checkout drawn inside our page (ui_mode "embedded"), for the
// signup, welcome and Plan and Credits pages alike. Stripe.js must come from
// js.stripe.com — Stripe allows no copy — so it is loaded the first time
// something is paid for and not before. Plain script: the desk and the
// guest pages both load it.
(function () {
	const SOURCE = "https://js.stripe.com/v3/";
	let loading = null;

	function load() {
		if (window.Stripe) return Promise.resolve(window.Stripe);
		if (!loading) {
			loading = new Promise((resolve, reject) => {
				const tag = document.createElement("script");
				tag.src = SOURCE;
				tag.onload = () => resolve(window.Stripe);
				tag.onerror = () => {
					loading = null;
					reject(new Error("Stripe.js did not load"));
				};
				document.head.appendChild(tag);
			});
		}
		return loading;
	}

	// `checkout` is what the account handed back (stripe.embedded): the
	// session's client secret and the publishable key. `done` is called when
	// a session that stays on the page is paid; one that returns to a page
	// takes the reader there itself.
	window.onePay = async function (into, checkout, { locale = "auto", done = null } = {}) {
		const Stripe = await load();
		const drawn = await Stripe(checkout.key, { locale }).initEmbeddedCheckout({
			fetchClientSecret: () => Promise.resolve(checkout.client_secret),
			...(done ? { onComplete: done } : {}),
		});
		drawn.mount(into);
		return drawn;
	};
})();
