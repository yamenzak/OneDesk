frappe.provide("onedesk.clock");

// Clocking in, from the browser's side.
//
// The button never sends a direction. A tab left open since this morning would
// send whichever way it pointed when it loaded, so the server reads the
// direction from where the person already is and this only says "punch".
//
// What it does send is what only a browser can answer: the passkey assertion,
// the position, and what the browser says about itself. Each is collected only
// where the workspace asked for it — `ready()` says which — so nobody sees a
// location prompt they were never going to be judged on.

//: How long to wait for a position before giving up and saying so. A phone
//: indoors can take fifteen seconds to get a fix and a refusal is instant, so
//: the wait is for the honest case rather than the awkward one.
onedesk.clock.FIX_MS = 12000;

onedesk.clock.ready = () => frappe.xcall("onedesk.one_hr.clock.ready");

onedesk.clock.punch = async (ready, reason) => {
	const needs = ready?.needs || {};
	const seen = await onedesk.passkey.seen();

	let credential = null;
	if (needs.passkey) {
		if (!ready.registered) return { ok: false, told: [__("Register a passkey first.")], register: true };
		credential = await onedesk.passkey.sign();
	}

	const position = needs.place ? await onedesk.clock.where() : null;

	return frappe.xcall("onedesk.one_hr.clock.punch", {
		credential: credential ? JSON.stringify(credential) : null,
		position: position ? JSON.stringify(position) : null,
		seen: JSON.stringify(seen),
		reason: reason || null,
	});
};

// A refusal is a fact, not an error: somebody who said no to the prompt has
// answered the question, and the server decides what that costs.
onedesk.clock.where = () =>
	new Promise((resolve) => {
		if (!navigator.geolocation) return resolve({ refused: false });
		navigator.geolocation.getCurrentPosition(
			(at) =>
				resolve({
					latitude: at.coords.latitude,
					longitude: at.coords.longitude,
					accuracy: at.coords.accuracy,
				}),
			(error) => resolve({ refused: error.code === error.PERMISSION_DENIED }),
			{ enableHighAccuracy: true, timeout: onedesk.clock.FIX_MS, maximumAge: 0 }
		);
	});

// Asked on the way out and never on the way in, and only where the workspace
// wants it. Cancelling the dialog cancels the clock-out rather than filing one
// with no reason, because the prompt is the workspace's question and answering
// it is not optional once it has been asked.
onedesk.clock.why = (direction) =>
	new Promise((resolve) => {
		if (direction !== "OUT") return resolve(null);
		frappe.prompt(
			{
				fieldname: "reason",
				fieldtype: "Select",
				label: __("Why"),
				options: ["Break", "Lunch", "Errand", "Done for the day"],
				default: "Done for the day",
				reqd: 1,
			},
			({ reason }) => resolve(reason),
			__("Clocking out")
		);
	});

// `comment_when` answers in markup, and anywhere it is put into an attribute or
// escaped it would print the span rather than the words. The words are what we
// want, not the tooltip around them.
onedesk.clock.when = (stamp) =>
	stamp ? $("<div>").html(frappe.datetime.comment_when(stamp, true)).text() : "";
