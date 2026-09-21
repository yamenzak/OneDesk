// The passkey button on the login page.
//
// `web_include_js` reaches here — `templates/base.html` renders those includes
// and `login.html` extends it — so the button is added to frappe's own card
// rather than by replacing their template. Nothing else on the page changes,
// and with the switch off nothing is added at all.
//
// No account is named before the signature is verified. Asking the server
// whether it holds a passkey for an address would turn the login page into a
// way of finding out who works here.
// Deferred to DOMContentLoaded: base.html renders the includes near the end of
// the body but the login card is drawn by a block above it, and reading for a
// card that is not there yet is how the button quietly never appears.
const draw = () => {
	const $card = document.querySelector(".page-card-body");
	if (!$card) return;
	if (!(window.PublicKeyCredential && navigator.credentials && window.isSecureContext)) return;

	// `frappe.call` is in frappe-web.bundle, which base.html loads before these
	// includes, so the login page has it and there is no reason to reach for
	// anything else.
	const call = (method, args) =>
		frappe.call({ method, args: args || {}, type: "POST" }).then((r) => r.message);

	const bytes = (text) => {
		const padded = text.replace(/-/g, "+").replace(/_/g, "/");
		const raw = atob(padded + "=".repeat((4 - (padded.length % 4)) % 4));
		return Uint8Array.from(raw, (c) => c.charCodeAt(0)).buffer;
	};
	const text = (buffer) =>
		btoa(String.fromCharCode(...new Uint8Array(buffer)))
			.replace(/\+/g, "-")
			.replace(/\//g, "_")
			.replace(/=+$/, "");

	const signIn = async ($button) => {
		$button.disabled = true;
		try {
			const options = await call("onedesk.one_hr.signin.begin");
			options.challenge = bytes(options.challenge);
			for (const one of options.allowCredentials || []) one.id = bytes(one.id);

			const got = await navigator.credentials.get({ publicKey: options });
			const done = await call("onedesk.one_hr.signin.finish", {
				credential: JSON.stringify({
					id: got.id,
					rawId: text(got.rawId),
					type: got.type,
					authenticatorAttachment: got.authenticatorAttachment,
					response: {
						clientDataJSON: text(got.response.clientDataJSON),
						authenticatorData: text(got.response.authenticatorData),
						signature: text(got.response.signature),
						userHandle: got.response.userHandle ? text(got.response.userHandle) : null,
					},
					clientExtensionResults: got.getClientExtensionResults(),
				}),
			});
			window.location.href = done?.home || "/desk";
		} catch (e) {
			$button.disabled = false;
		}
	};

	call("onedesk.one_hr.signin.offered").then((yes) => {
		if (!yes) return;
		const $button = document.createElement("button");
		$button.type = "button";
		$button.className = "es-button w-full btn-login-option one-passkey-login";
		$button.textContent = __ ? __("Sign in with a Passkey") : "Sign in with a Passkey";
		$button.addEventListener("click", () => signIn($button));
		// After frappe's own alternative sign-in, not between the password box and
		// the button that uses it.
		const $email = $card.querySelector(".btn-login-with-email-link");
		if ($email) $email.insertAdjacentElement("afterend", $button);
		else $card.appendChild($button);
	});
};

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", draw);
else draw();
