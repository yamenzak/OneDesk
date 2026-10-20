// The editor's realtime adapter, over One's relay (realtime/handlers.js) in
// place of Suite's, which published through publish_realtime to every
// signed-in user. Same { publish, on, off } as collab/realtime-adapter.js.
import { deskSession } from "../../kit/desk";

export function createRealtimeAdapter({ sheetId } = {}) {
	const { socket } = deskSession();
	const listeners = new Map();
	const waiting = [];
	let room = null;

	const heard = (said) => {
		if (!said || said.room !== room) return;
		for (const cb of listeners.get(said.event) || []) cb(said.payload);
	};

	const join = () =>
		socket.emit("onedesk_join", "workbook", sheetId, (answer) => {
			if (!answer?.ok) return;
			room = answer.room;
			while (waiting.length) socket.emit("onedesk_send", room, ...waiting.shift());
		});

	if (socket) {
		socket.on("onedesk_said", heard);
		join();
		socket.on("connect", join);
	}

	function publish(event, payload) {
		if (!socket) return;
		if (room) socket.emit("onedesk_send", room, event, payload ?? {});
		else waiting.push([event, payload ?? {}]);
	}

	function on(event, cb) {
		if (!listeners.has(event)) listeners.set(event, new Set());
		listeners.get(event).add(cb);
	}

	function off(event, cb) {
		listeners.get(event)?.delete(cb);
		if (socket && [...listeners.values()].every((one) => !one.size)) {
			socket.off("onedesk_said", heard);
			socket.off("connect", join);
			if (room) socket.emit("onedesk_leave", room);
			room = null;
		}
	}

	return { publish, on, off };
}
