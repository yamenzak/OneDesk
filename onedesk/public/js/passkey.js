frappe.provide("onedesk.passkey");

onedesk.passkey.supported = () =>
	Boolean(window.PublicKeyCredential && navigator.credentials && window.isSecureContext);

onedesk.passkey.register = async (seen) => {
	const options = await frappe.xcall("onedesk.one_hr.passkey.start_registration");
	const credential = await navigator.credentials.create({
		publicKey: onedesk.passkey.decode(options, ["challenge"], ["user", "id"]),
	});
	return frappe.xcall("onedesk.one_hr.passkey.finish_registration", {
		credential: JSON.stringify(onedesk.passkey.made(credential)),
		seen: JSON.stringify(seen || (await onedesk.passkey.seen())),
	});
};

onedesk.passkey.sign = async (employee) => {
	const options = await frappe.xcall("onedesk.one_hr.passkey.start_assertion", { employee });
	const credential = await navigator.credentials.get({
		publicKey: onedesk.passkey.decode(options, ["challenge"]),
	});
	return onedesk.passkey.signed(credential);
};

onedesk.passkey.decode = (options, ...paths) => {
	const out = JSON.parse(JSON.stringify(options));
	for (const path of paths) {
		let holder = out;
		for (const step of path.slice(0, -1)) holder = holder?.[step];
		const key = path[path.length - 1];
		if (holder && typeof holder[key] === "string") holder[key] = onedesk.passkey.bytes(holder[key]);
	}
	for (const list of ["allowCredentials", "excludeCredentials"]) {
		for (const one of out[list] || []) {
			if (typeof one.id === "string") one.id = onedesk.passkey.bytes(one.id);
		}
	}
	return out;
};

onedesk.passkey.made = (credential) => ({
	id: credential.id,
	rawId: onedesk.passkey.text(credential.rawId),
	type: credential.type,
	authenticatorAttachment: credential.authenticatorAttachment,
	response: {
		clientDataJSON: onedesk.passkey.text(credential.response.clientDataJSON),
		attestationObject: onedesk.passkey.text(credential.response.attestationObject),
	},
	clientExtensionResults: credential.getClientExtensionResults(),
});

onedesk.passkey.signed = (credential) => ({
	id: credential.id,
	rawId: onedesk.passkey.text(credential.rawId),
	type: credential.type,
	authenticatorAttachment: credential.authenticatorAttachment,
	response: {
		clientDataJSON: onedesk.passkey.text(credential.response.clientDataJSON),
		authenticatorData: onedesk.passkey.text(credential.response.authenticatorData),
		signature: onedesk.passkey.text(credential.response.signature),
		userHandle: credential.response.userHandle
			? onedesk.passkey.text(credential.response.userHandle)
			: null,
	},
	clientExtensionResults: credential.getClientExtensionResults(),
});

onedesk.passkey.bytes = (text) => {
	const padded = text.replace(/-/g, "+").replace(/_/g, "/");
	const raw = atob(padded + "=".repeat((4 - (padded.length % 4)) % 4));
	return Uint8Array.from(raw, (c) => c.charCodeAt(0)).buffer;
};

onedesk.passkey.text = (buffer) =>
	btoa(String.fromCharCode(...new Uint8Array(buffer)))
		.replace(/\+/g, "-")
		.replace(/\//g, "_")
		.replace(/=+$/, "");

onedesk.passkey.seen = async () => {
	if (onedesk.passkey._seen) return onedesk.passkey._seen;

	const seen = {
		user_agent: navigator.userAgent,
		platform: navigator.userAgentData?.platform || navigator.platform || "",
		model: "",
		screen: `${window.screen.width}x${window.screen.height}@${window.devicePixelRatio || 1}`,
		renderer: onedesk.passkey.renderer(),
		touch: navigator.maxTouchPoints || 0,
		mobile: navigator.userAgentData?.mobile ? 1 : 0,
	};
	try {
		const more = await navigator.userAgentData?.getHighEntropyValues(["model"]);
		seen.model = more?.model || "";
	} catch (e) {
	}
	onedesk.passkey._seen = seen;
	return seen;
};

onedesk.passkey.renderer = () => {
	try {
		const gl = document.createElement("canvas").getContext("webgl");
		const named = gl?.getExtension("WEBGL_debug_renderer_info");
		return named ? String(gl.getParameter(named.UNMASKED_RENDERER_WEBGL)).slice(0, 140) : "";
	} catch (e) {
		return "";
	}
};

$(document).on("app_ready", () => {
	if (!frappe.boot.one_passkey_ask || !onedesk.passkey.supported()) return;
	const offer = () => {
		if ($(".modal:visible").length) return setTimeout(offer, 4000);
		let chose = false;
		const declined = () => frappe.xcall("onedesk.one_hr.passkey.not_now");
		const dialog = new frappe.ui.Dialog({
			title: __("Sign In with a Passkey"),
			fields: [
				{
					fieldtype: "HTML",
					options: `<p class="text-ink-gray-7">${__(
						"Next time, sign in with your face, fingerprint or screen lock instead of typing your password. It takes a few seconds to set up."
					)}</p>`,
				},
			],
			primary_action_label: __("Create Passkey"),
			primary_action: async () => {
				chose = true;
				dialog.hide();
				try {
					await onedesk.passkey.register();
					frappe.boot.one_passkey_ask = false;
					frappe.show_alert({ message: __("Passkey created. Use it next time you sign in."), indicator: "green" });
				} catch (e) {
					declined();
				}
			},
			secondary_action_label: __("Not Now"),
			secondary_action: () => dialog.hide(),
		});
		dialog.onhide = () => chose || declined();
		dialog.show();
	};
	setTimeout(offer, 2500);
});
