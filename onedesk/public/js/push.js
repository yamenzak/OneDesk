// Push in this browser: turning it on, off, and saying where it stands. The
// server side is one/push.py. The worker is served from a method with
// Service-Worker-Allowed: / so it is registered for the whole site; it handles
// push and clicks only, never a request the page makes.

frappe.provide("onedesk.push");

Object.assign(onedesk.push, {
	WORKER: "/api/method/onedesk.one.push.worker",

	supported() {
		return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
	},

	// Where this browser stands: not able to, blocked, on (with its address), or off.
	async state() {
		if (!this.supported()) return { state: "unsupported" };
		if (Notification.permission === "denied") return { state: "blocked" };
		const registration = await navigator.serviceWorker.getRegistration("/");
		const subscription = registration && (await registration.pushManager.getSubscription());
		return subscription ? { state: "on", endpoint: subscription.endpoint } : { state: "off" };
	},

	async on(key) {
		if ((await Notification.requestPermission()) !== "granted") return false;
		const registration = await navigator.serviceWorker.register(this.WORKER, { scope: "/" });
		await navigator.serviceWorker.ready;
		const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: this.bytes(key) });
		const said = subscription.toJSON();
		await frappe.xcall("onedesk.one.push.register", { endpoint: said.endpoint, p256dh: said.keys.p256dh, auth: said.keys.auth, label: this.label() });
		return true;
	},

	async off() {
		const registration = await navigator.serviceWorker.getRegistration("/");
		const subscription = registration && (await registration.pushManager.getSubscription());
		if (!subscription) return;
		await frappe.xcall("onedesk.one.push.forget", { endpoint: subscription.endpoint });
		await subscription.unsubscribe();
	},

	// The browser and the system, as a person would name the device.
	label() {
		const agent = navigator.userAgent;
		const browser = /Edg\//.test(agent) ? "Edge" : /Firefox\//.test(agent) ? "Firefox" : /Chrome\//.test(agent) ? "Chrome" : /Safari\//.test(agent) ? "Safari" : __("A browser");
		const system = /iPhone|iPad/.test(agent) ? "iOS" : /Android/.test(agent) ? "Android" : /Mac OS X/.test(agent) ? "macOS" : /Windows/.test(agent) ? "Windows" : /Linux/.test(agent) ? "Linux" : "";
		return system ? __("{0} on {1}", [browser, system]) : browser;
	},

	// The server's key as the browser wants it: base64url to bytes.
	bytes(key) {
		const padded = (key + "=".repeat((4 - (key.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/");
		return Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
	},
});
