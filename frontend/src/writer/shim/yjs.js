// Derived from frappe/suite@df7f341 (frontend/src/apps/writer)/composables/useYjs.ts. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see ../VENDORED.md.
// The writer's Yjs, saved through one_doc/api.py and shared over One's relay
// (realtime/handlers.js, the room a document's) in place of Suite's: no
// signalling server of somebody else's, and no copy kept in the browser.
import * as Y from "yjs";
import { Awareness, removeAwarenessStates } from "y-protocols/awareness";
import { toUint8Array, fromUint8Array } from "js-base64";
import { debounce, toast } from "frappe-ui";
import { absolutePositionToRelativePosition, ySyncPluginKey } from "@tiptap/y-tiptap";
import { ref } from "vue";

import { __, call, deskSession, person } from "../../kit/desk";
import { rebuild } from "../extensions/comments";
import { useCollaborationUsers } from "../composables/useCollaborationUsers";

const REMOTE = "remote";
const SAVE_AFTER_MS = 2000;
const FLUSH_MS = 16;
const KEEPALIVE_MS = 8000;

// The room a document's, joined once; every message names the room it is for.
function relay(name) {
	const { socket } = deskSession();
	const listeners = new Map();
	const waiting = [];
	let room = null;
	let write = false;

	const heard = (said) => {
		if (!said || said.room !== room) return;
		for (const cb of listeners.get(said.event) || []) cb(said.payload || {});
	};
	const join = () =>
		socket.emit("onedesk_join", "document", name, (answer) => {
			if (!answer?.ok) return;
			room = answer.room;
			write = !!answer.write;
			while (waiting.length) socket.emit("onedesk_send", room, ...waiting.shift());
			for (const cb of listeners.get("@joined") || []) cb();
		});
	if (socket) {
		socket.on("onedesk_said", heard);
		join();
		socket.on("connect", join);
	}
	return {
		get write() {
			return write;
		},
		send(event, payload) {
			if (!socket) return;
			if (room) socket.emit("onedesk_send", room, event, payload);
			else waiting.push([event, payload]);
		},
		on(event, cb) {
			if (!listeners.has(event)) listeners.set(event, new Set());
			listeners.get(event).add(cb);
		},
		close() {
			if (!socket) return;
			socket.off("onedesk_said", heard);
			socket.off("connect", join);
			if (room) socket.emit("onedesk_leave", room);
			room = null;
		},
	};
}

// Others' cursors, from their JSON states, in a y-protocols Awareness the
// caret extension reads.
function shareAwareness(doc, link) {
	const awareness = new Awareness(doc);
	const me = doc.clientID;
	const publish = () => link.send("yjs_awareness", { from: me, state: awareness.getLocalState() });
	awareness.on("update", (_, origin) => origin === "local" && publish());
	link.on("yjs_awareness", ({ from, state }) => {
		if (typeof from !== "number" || from === me || !state) return;
		const user = state.user || {};
		state.user = { ...user, name: user.fullName || user.name };
		const known = awareness.states.has(from);
		awareness.states.set(from, state);
		awareness.meta.set(from, { clock: (awareness.meta.get(from)?.clock || 0) + 1, lastUpdated: Date.now() });
		const change = { added: known ? [] : [from], updated: known ? [from] : [], removed: [] };
		awareness.emit("change", [change, REMOTE]);
		awareness.emit("update", [change, REMOTE]);
	});
	link.on("yjs_awareness_bye", ({ from }) => typeof from === "number" && removeAwarenessStates(awareness, [from], REMOTE));
	link.on("@joined", publish);
	const keepalive = setInterval(publish, KEEPALIVE_MS);
	return {
		awareness,
		destroy() {
			clearInterval(keepalive);
			link.send("yjs_awareness_bye", { from: me });
			awareness.destroy();
		},
	};
}

export const useComments = (document, editor, link) => {
	const commentsDoc = new Y.Doc();
	if (document.doc.ycomments) Y.applyUpdate(commentsDoc, toUint8Array(document.doc.ycomments), "server");
	commentsDoc.on("update", (update, origin) => {
		if (origin !== REMOTE && origin !== "server") link.send("yjs_comments", { update: fromUint8Array(update) });
	});
	link.on("yjs_comments", ({ update }) => {
		if (update) Y.applyUpdate(commentsDoc, toUint8Array(update), REMOTE);
		rebuild(editor.value);
	});

	const comments = commentsDoc.getMap("comments");
	const newComment = (id, from, to, owner, anchorText) => {
		const ystate = ySyncPluginKey.getState(editor.value.view.state);
		comments.set(id, {
			id,
			new: true,
			creation: Date.now(),
			owner,
			replies: [],
			anchorText,
			anchor: {
				from: Y.encodeRelativePosition(absolutePositionToRelativePosition(from, ystate.type, ystate.binding.mapping)),
				to: Y.encodeRelativePosition(absolutePositionToRelativePosition(to, ystate.type, ystate.binding.mapping)),
			},
		});
		rebuild(editor.value);
	};
	const saveComments = () =>
		call("onedesk.one_doc.api.save_comments", { name: document.doc.name, data: fromUint8Array(Y.encodeStateAsUpdate(commentsDoc)) });
	return { saveComments, newComment, comments, commentsDoc };
};

export function useYjs(id, document, editor, edited) {
	const doc = new Y.Doc({ gc: true });
	if (document.doc.content) Y.applyUpdate(doc, toUint8Array(document.doc.content), "server");
	const loaded = ref(true);
	const link = relay(id);

	// Saving to server: the whole state, and what the editor shows as HTML.
	const save = async (manual = false, oldHtml) => {
		if (!manual && !edited.value) return;
		const html = editor.value ? editor.value.getHTML() : oldHtml || "";
		try {
			await document.saveDoc.submit({ data: fromUint8Array(Y.encodeStateAsUpdate(doc)), html });
		} catch (failed) {
			toast.error(failed?.message || __("Could not save the document."));
			throw failed;
		}
	};
	const autosave = debounce(save, SAVE_AFTER_MS);

	// Changes out, batched a frame; changes in, applied as remote.
	let pending = [];
	let timer = null;
	const flush = () => {
		timer = null;
		if (!pending.length) return;
		const merged = pending.length === 1 ? pending[0] : Y.mergeUpdates(pending);
		pending = [];
		link.send("yjs_update", { update: fromUint8Array(merged) });
	};
	doc.on("update", (update, origin) => {
		if (origin === "server") return;
		if (origin !== REMOTE) {
			autosave();
			pending.push(update);
			if (!timer) timer = setTimeout(flush, FLUSH_MS);
		}
	});
	link.on("yjs_update", ({ update }) => update && Y.applyUpdate(doc, toUint8Array(update), REMOTE));
	link.on("yjs_state", ({ update, comments }) => {
		if (update) Y.applyUpdate(doc, toUint8Array(update), REMOTE);
		if (comments) Y.applyUpdate(commentsData.commentsDoc, toUint8Array(comments), REMOTE);
	});
	link.on("yjs_state_request", () => {
		if (!link.write) return;
		flush();
		link.send("yjs_state", {
			update: fromUint8Array(Y.encodeStateAsUpdate(doc)),
			comments: fromUint8Array(Y.encodeStateAsUpdate(commentsData.commentsDoc)),
		});
	});
	link.on("@joined", () => link.send("yjs_state_request", {}));

	const shared = shareAwareness(doc, link);
	const provider = { awareness: shared.awareness };
	const { users, cleanup: cleanupUsers } = useCollaborationUsers(shared.awareness);
	const permanentUserData = new Y.PermanentUserData(doc);
	permanentUserData.setUserMapping(doc, doc.clientID, person().name || "Guest");

	const commentsData = useComments(document, editor, link);
	return {
		doc,
		cleanup: () => {
			flush();
			cleanupUsers();
			shared.destroy();
			link.close();
		},
		save,
		provider,
		users,
		permanentUserData,
		loaded,
		saveComments: commentsData.saveComments,
		newComment: commentsData.newComment,
		comments: commentsData.comments,
	};
}
