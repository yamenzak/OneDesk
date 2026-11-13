const draw = () => {
	const $card = document.querySelector(".for-login:not(.one-your-data) .page-card-body");
	if (!$card) return;
	if (!(window.PublicKeyCredential && navigator.credentials && window.isSecureContext)) return;

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
		$button.className = "es-button w-full one-passkey-login";
		$button.dataset.variant = "solid";
		$button.textContent = __("Sign in with a Passkey");
		$button.addEventListener("click", () => signIn($button));
		const $or = document.createElement("div");
		$or.className = "one-login-or text-p-sm text-ink-gray-5";
		$or.textContent = __("or use your password");
		$card.insertAdjacentElement("beforebegin", $or);
		$or.insertAdjacentElement("beforebegin", $button);
		const $password = $card.parentElement.querySelector('.page-card-actions button[type="submit"]');
		if ($password) $password.dataset.variant = "subtle";
	});
};

const footnote = () => {
	const $card = document.querySelector(".for-login:not(.one-your-data) .login-content");
	if (!$card || document.querySelector(".one-login-footnote")) return;
	const $line = document.createElement("p");
	$line.className = "one-login-footnote text-center text-p-sm text-ink-gray-6 mt-4 mb-0";
	for (const [href, label] of [
		["/your-data", __("Your Data")],
		["/legal/privacy", __("Privacy Policy")],
	]) {
		if ($line.childNodes.length) $line.append(" · ");
		const $a = document.createElement("a");
		$a.href = href;
		$a.className = "text-ink-gray-6";
		$a.textContent = label;
		$line.append($a);
	}
	$card.appendChild($line);
};

const start = () =>
	Promise.resolve(window.frappe && frappe._translations_loaded)
		.catch(() => null)
		.then(() => {
			footnote();
			draw();
		});
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
else start();
