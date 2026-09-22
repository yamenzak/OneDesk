<!-- The panel: a list of conversations, and one conversation.

     Two views rather than a channel rail, because a list of threads is the
     shape OneMessaging will want too — its threads join this list rather than
     needing a second panel drawn beside this one. -->
<template>
	<div class="one-ai-panel" :class="`one-ai-panel--${size}`">
		<div class="one-ai-head">
			<button
				v-if="view === 'chat'"
				class="one-ai-icon"
				:title="__('All conversations')"
				@click="toThreads"
			>
				<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.6">
					<path d="M10 3 5 8l5 5" stroke-linecap="round" stroke-linejoin="round" />
				</svg>
			</button>
			<img v-else class="one-ai-head__mark" :src="mark" alt="" />

			<div class="one-ai-head__title">
				{{ view === "chat" ? chat.title || __("New conversation") : ONEAI }}
				<span class="one-ai-head__sub">{{ subtitle }}</span>
			</div>

			<button class="one-ai-icon" :title="__('New conversation')" @click="fresh">
				<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.6">
					<path d="M8 3.5v9M3.5 8h9" stroke-linecap="round" />
				</svg>
			</button>
			<button class="one-ai-icon" :title="bigger" @click="grow">
				<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.6">
					<path v-if="size === 'full'" d="M6.5 3v3.5H3M9.5 13V9.5H13" stroke-linecap="round" stroke-linejoin="round" />
					<path v-else d="M6 3H3v3M10 13h3v-3" stroke-linecap="round" stroke-linejoin="round" />
				</svg>
			</button>
			<button class="one-ai-icon" :title="__('Close')" @click="$emit('closed')">
				<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.6">
					<path d="M4 4l8 8M12 4l-8 8" stroke-linecap="round" />
				</svg>
			</button>
		</div>

		<div ref="body" class="one-ai-body">
			<template v-if="view === 'threads'">
				<button v-for="one in threads" :key="one.name" class="one-ai-thread" @click="openChat(one.name)">
					<span class="one-ai-thread__title">{{ one.title || __("Untitled") }}</span>
					<span class="one-ai-thread__when">{{ when(one.last_said_on) }}</span>
				</button>
				<div v-if="!threads.length" class="one-ai-empty">
					{{ __("Nothing asked yet. Ask something about what is on screen, or anything else.") }}
				</div>
			</template>

			<template v-else>
				<div v-if="!chat.said.length" class="one-ai-empty">
					{{ __("Ask about this page, look something up, or have a change suggested.") }}
				</div>

				<div
					v-for="(said, at) in chat.said"
					:key="at"
					class="one-ai-said"
					:class="`one-ai-said--${said.role}`"
				>
					<div v-if="said.files && said.files.length" class="one-ai-files">
						<a
							v-for="file in said.files"
							:key="file.url"
							class="one-ai-file"
							:href="file.url"
							target="_blank"
							rel="noopener"
						>
							<svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.5">
								<path d="M9 2H4.5A1.5 1.5 0 0 0 3 3.5v9A1.5 1.5 0 0 0 4.5 14h7a1.5 1.5 0 0 0 1.5-1.5V6z" stroke-linejoin="round" />
								<path d="M9 2v4h4" stroke-linejoin="round" />
							</svg>
							<span>{{ file.name }}</span>
						</a>
					</div>

					<div v-if="said.text" class="one-ai-said__text" :class="{ 'one-ai-prose': said.role === 'model' }">
						<span class="one-ai-said__who">{{ said.role === "you" ? __("You") : ONEAI }}</span>
						<span v-if="said.role === 'you'">{{ said.text }}</span>
						<span v-else v-html="prose(said.text)"></span>
					</div>

					<template v-for="(look, i) in said.looked" :key="i">
						<div v-if="look.error || (!look.records.length && !look.card)" class="one-ai-looked"
							:class="{ 'one-ai-looked--refused': look.error }">
							<span class="one-ai-looked__dot"></span>
							<span>{{ look.error || told(look) }}</span>
						</div>

						<Record v-for="rec in look.records" :key="rec.name" :record="rec" />
						<div v-if="look.more" class="one-ai-looked">
							<span class="one-ai-looked__dot"></span>
							<span>{{ __("and {0} more", [look.more]) }}</span>
						</div>
					</template>

					<Record
						v-for="name in said.cards"
						:key="name"
						:record="(cards[name] && cards[name].shown) || { doctype: '', name: '', title: '', fields: [] }"
						:suggested="cards[name] || { name, kind: 'Create', state: 'Proposed' }"
						@answered="answered"
					/>
				</div>

				<div v-if="busy" class="one-ai-thinking">
					<span class="one-ai-thinking__bloom"></span>
					<span>{{ doing }}</span>
				</div>

				<div v-if="broke" class="one-ai-broke">
					<div class="one-ai-broke__said">{{ broke }}</div>
					<button class="btn btn-default btn-xs" @click="send(lastAsked)">{{ __("Try again") }}</button>
				</div>
			</template>
		</div>

		<div v-if="view === 'chat'" class="one-ai-foot">
			<div v-if="here" class="one-ai-here">
				<span>{{ __("Knows about") }}</span>
				<button
					class="one-ai-here__chip"
					:aria-pressed="String(useHere)"
					:title="useHere ? __('Stop sending this') : __('Send this again')"
					@click="useHere = !useHere"
				>
					{{ here.label }}
				</button>
			</div>

			<div class="one-ai-ask" :class="{ 'one-ai-ask--busy': busy }" @click="box && box.focus()">
				<div v-if="waiting.length" class="one-ai-waiting">
					<span v-for="(file, at) in waiting" :key="file.url" class="one-ai-waiting__one">
						{{ file.name }}
						<button class="one-ai-waiting__off" :title="__('Remove')" @click.stop="waiting.splice(at, 1)">×</button>
					</span>
				</div>

				<textarea
					ref="box"
					v-model="text"
					rows="1"
					:placeholder="__('Ask {0}', [ONEAI])"
					@keydown.enter.exact.prevent="send()"
					@input="fit"
				></textarea>

				<div class="one-ai-ask__row" @click.stop>
					<button class="one-ai-round" :title="__('Attach a file')" :disabled="busy" @click="attach">
						<svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6">
							<path d="M8 3v10M3 8h10" stroke-linecap="round" />
						</svg>
					</button>
					<button
						v-if="chat.model_at"
						class="one-ai-model"
						:title="__('Change the model')"
						@click="toModel"
					>
						{{ chat.model || __("Default model") }}
					</button>
					<span v-else class="one-ai-model">{{ chat.model || __("Default model") }}</span>

					<button
						v-if="Hearing"
						class="one-ai-round one-ai-mic"
						:class="{ 'one-ai-mic--on': listening }"
						:title="listening ? __('Stop listening') : __('Speak')"
						:disabled="busy"
						@click="listen"
					>
						<svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5">
							<rect x="5.75" y="1.75" width="4.5" height="8" rx="2.25" />
							<path d="M3.25 7.5a4.75 4.75 0 0 0 9.5 0M8 12.25v2" stroke-linecap="round" />
						</svg>
					</button>
					<button
						class="one-ai-send"
						:class="{ 'one-ai-send--alone': !Hearing }"
						:disabled="busy || (!text.trim() && !waiting.length)"
						:title="__('Send')"
						@click="send()"
					>
						<svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8">
							<path d="M8 13V3.5M3.75 7.5 8 3.25l4.25 4.25" stroke-linecap="round" stroke-linejoin="round" />
						</svg>
					</button>
				</div>
			</div>

			<div v-if="chat.spent" class="one-ai-spent">
				{{ __("{0} credits in this conversation", [format(chat.spent)]) }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, ref } from "vue";

import Record from "./Record.vue";

const __ = window.__;
const mark = "/assets/onedesk/images/oneai.svg";

// A product name is a name. It is the same in every language, so it is written
// here once and never passed through `__()`.
const ONEAI = "OneAI";

const props = defineProps({ here: { type: Object, default: null } });
const emit = defineEmits(["closed", "counted"]);

const view = ref("threads");
const size = ref("snug");
const busy = ref(false);
const text = ref("");
const broke = ref("");
const lastAsked = ref("");
const waiting = ref([]);
const doing = ref("");
const threads = ref([]);
const cards = ref({});
const chat = ref({ name: null, title: null, said: [], spent: 0 });
const useHere = ref(true);
const body = ref(null);
const box = ref(null);
const listening = ref(false);

// The browser's own speech recognition, where there is one. Chrome and Safari
// have it and Firefox does not, so the button is simply absent there rather
// than present and broken. What it hears is typed into the box, not sent: a
// misheard word is fixed before the question goes, not after.
const Hearing = window.SpeechRecognition || window.webkitSpeechRecognition;
let ear = null;

//: Three sizes rather than two. Snug is the live-chat shape; roomy is for a
//: conversation with records in it; full is for reading a report next to the
//: page it is about. Remembered per browser, because it is a preference about
//: this screen rather than about this conversation.
const SIZES = ["snug", "roomy", "full"];

const bigger = computed(() =>
	size.value === "full" ? __("Make it smaller") : __("Make it bigger")
);

// Frappe loads a doctype's user settings on demand, so on a fresh page there
// are none in the browser yet — and `get_user_settings` answers a missing key
// with `{}` rather than undefined, which is how a size of "[object Object]"
// gets onto the panel. Fetched once, when the panel first mounts.
frappe.model.user_settings.get("AI Chat").then((kept) => {
	frappe.model.user_settings["AI Chat"] = kept || {};
	if (SIZES.includes((kept || {}).panel_size)) size.value = kept.panel_size;
});

function grow() {
	const at = SIZES.indexOf(size.value);
	size.value = SIZES[(at + 1) % SIZES.length];
	// Frappe's own per-user settings rather than this browser's storage, so the
	// size somebody chose is theirs on whatever machine they next sign in from.
	frappe.model.user_settings.save("AI Chat", "panel_size", size.value);
}

// Frappe's own markdown, which is showdown with tables on and a whitelist
// sanitiser after it — so a model that answers with a script tag gets its
// script tag removed by the framework rather than by something we wrote.
function prose(text) {
	return frappe.markdown(text || "");
}

const subtitle = computed(() => {
	if (view.value === "threads") return __("Your conversations");
	return chat.value.name ? __("Kept") : __("Answers from your own records");
});

defineExpose({
	// The launcher may say where to land: a conversation, or straight into a
	// fresh one from a record's own AI control.
	async opened(opening) {
		if (opening && opening.chat) return openChat(opening.chat);
		if (opening && opening.fresh) return fresh();
		// Into the conversation, not into a list of them: opening a panel and
		// being given an index is a second click before anybody has asked
		// anything. The list is one press back, for the times it is wanted.
		await list();
		threads.value.length ? openChat(threads.value[0].name) : fresh();
	},
});

async function list() {
	view.value = "threads";
	threads.value = await frappe.xcall("onedesk.one_ai.chat.chats");
}

async function openChat(name) {
	chat.value = await frappe.xcall("onedesk.one_ai.chat.opened", { chat: name });
	view.value = "chat";
	await load();
	toBottom();
}

function fresh() {
	chat.value = { name: null, title: null, said: [], spent: 0 };
	cards.value = {};
	view.value = "chat";
	nextTick(() => box.value && box.value.focus());
	// Asked for after the box is up, so a new conversation opens at once and
	// the pill fills in a moment later with whatever model would answer it.
	frappe.xcall("onedesk.one_ai.chat.opened").then((empty) => {
		if (!chat.value.name) chat.value = { ...chat.value, ...empty, said: chat.value.said };
	});
}

function toThreads() {
	list();
}

// Frappe's own uploader, attaching to the conversation — so the file is a File
// row with an owner and a permission, in the workspace, rather than something
// living inside a transcript nobody can find again. The chat has to exist first,
// which is why an empty one is saved before the dialog opens.
async function attach() {
	if (!chat.value.name) {
		chat.value = await frappe.xcall("onedesk.one_ai.chat.start");
	}
	new frappe.ui.FileUploader({
		doctype: "AI Chat",
		docname: chat.value.name,
		frm: null,
		on_success: (file) => waiting.value.push({ name: file.file_name, url: file.file_url }),
	});
}

// The model is the workspace's choice for the chat action, so changing it is
// that setting and not a picker here — one person switching it would switch it
// for everybody.
function toModel() {
	frappe.set_route("Form", "AI Action Setting", chat.value.model_at);
}

function listen() {
	if (ear) return ear.stop();
	ear = new Hearing();
	ear.lang = frappe.boot.lang || navigator.language;
	ear.interimResults = true;
	ear.continuous = true;
	const before = text.value.trim() ? `${text.value.trim()} ` : "";
	ear.onresult = (heard) => {
		text.value = before + Array.from(heard.results, (one) => one[0].transcript).join("");
		nextTick(fit);
	};
	ear.onend = ear.onerror = () => {
		listening.value = false;
		ear = null;
	};
	ear.start();
	listening.value = true;
}

async function send(again) {
	if (ear) ear.stop();
	const asked = (again || text.value).trim();
	if ((!asked && !waiting.value.length) || busy.value) return;
	if (!again) text.value = "";
	lastAsked.value = asked;
	broke.value = "";
	fit();
	busy.value = true;
	doing.value = __("Thinking…");

	// Shown before it is sent, so the question is on screen while the model is
	// still thinking about it rather than appearing with the answer.
	const sending = waiting.value.splice(0);
	if (!again) {
		chat.value.said.push({ role: "you", text: asked, looked: [], cards: [], files: sending });
	}
	toBottom();

	// The rounds take seconds each and a spinner that says nothing for twenty
	// of them reads as a hang. This is what it is doing, not how far along it
	// is — there is no progress to report until AI 9 streams one.
	const saying = setTimeout(() => (doing.value = __("Looking things up…")), 3000);

	try {
		chat.value = await frappe.xcall("onedesk.one_ai.chat.say", {
			text: asked,
			chat: chat.value.name,
			page: useHere.value && props.here ? props.here : null,
			files: sending.map((one) => one.url),
		});
		await load();
		emit("counted");
	} catch (raised) {
		// The question stays on screen with the reason under it and a button,
		// because a failed run that clears the box is a question retyped.
		broke.value = _why(raised);
		frappe.hide_msgprint && frappe.hide_msgprint();
	} finally {
		clearTimeout(saying);
		busy.value = false;
		toBottom();
	}
}

// Why it did not go through, in words somebody can act on.
//
// `frappe.xcall` rejects with the response's `message`, which for an exception
// is empty — the reason is in `frappe.last_response`, where frappe leaves the
// last reply so its own error dialog can read it. Read from there, stripped of
// markup, and frappe's dialog is dismissed because the panel is already saying
// it in the place somebody is looking.
function _why(raised) {
	const last = frappe.last_response || {};
	let said = "";
	try {
		said = JSON.parse(last._server_messages || "[]")[0] || "";
		said = JSON.parse(said).message || said;
	} catch (e) {
		// Not a server message. The next two lines still have somewhere to look.
	}
	said = said || last.exception || (typeof raised === "string" ? raised : "");
	said = $("<span>").html(String(said)).text().trim();
	return said || __("That did not go through.");
}

async function load() {
	const named = [];
	for (const said of chat.value.said) named.push(...(said.cards || []));
	if (!named.length) return;
	const found = await frappe.xcall("onedesk.one_ai.chat.cards", { names: named });
	cards.value = Object.fromEntries((found || []).map((one) => [one.name, one]));
}

async function answered() {
	await load();
	emit("counted");
}

// What it did, not which function it called. A write says it suggested rather
// than that it looked, because "looked at ToDo" above a card that would create
// one is the one sentence in the panel that could be read as "it did it".
function told(look) {
	const what = (look.args && (look.args.doctype || look.args.name)) || "";
	if (!look.ran) return what ? __("Suggested a change to {0}", [what]) : __("Suggested a change");
	return what ? __("Looked at {0}", [what]) : __("Looked something up");
}

// `comment_when` answers with a span carrying the exact time in a title, which
// is right where frappe puts it as HTML and wrong here, where it is text. The
// words are what is wanted; the markup is thrown away.
function when(said) {
	return said ? $("<span>").html(frappe.datetime.comment_when(said)).text() : "";
}

// Not `frappe.format`, which answers with markup for a Float and would print
// its own div into the sentence.
function format(credits) {
	return Number(credits || 0).toFixed(4);
}


function fit() {
	const el = box.value;
	if (!el) return;
	el.style.height = "auto";
	el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
}

function toBottom() {
	nextTick(() => {
		if (body.value) body.value.scrollTop = body.value.scrollHeight;
	});
}
</script>
