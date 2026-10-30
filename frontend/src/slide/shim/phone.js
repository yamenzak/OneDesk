// The presenter view's half of a phone remote (one_slide/remote.py; the
// phone's half is public/js/one_slide/remote.js). Pairing asks for a token and
// the QR code that carries it; then this tab and the phone meet in the
// token's socket room on the desk's own socket: the phone says go and point,
// this tab says which slide is showing and its notes. Unpairing kills the
// token, so a photographed QR code drives nothing afterwards.
import { ref } from "vue";

import { call, deskSession } from "../../kit/desk";

// the token, the address the phone opens and its QR code, once paired
export const paired = ref(null);
// a phone has said hello since pairing
export const connected = ref(false);

let socket = null;
let heard = () => {};

function join() {
	if (paired.value) socket?.emit("onedesk_remote_join", paired.value.token, paired.value.screen, () => {});
}

function received(message) {
	if (!message?.event) return;
	if (message.event === "hello") connected.value = true;
	heard(message.event, message.payload || {});
}

export async function pairPhone(name, onSaid) {
	heard = onSaid;
	if (!paired.value) paired.value = await call("onedesk.one_slide.remote.pair", { name });
	if (socket) return;
	socket = deskSession().socket;
	if (!socket) return;
	socket.on("onedesk_remote", received);
	// a socket that reconnects has left every room
	socket.on("connect", join);
	join();
}

export const tellPhone = (state) => socket?.emit("onedesk_remote_say", "state", state);

export function unpairPhone() {
	if (socket) {
		socket.off("onedesk_remote", received);
		socket.off("connect", join);
	}
	if (paired.value) call("onedesk.one_slide.remote.unpair", { token: paired.value.token, screen: paired.value.screen });
	socket = null;
	paired.value = null;
	connected.value = false;
}
