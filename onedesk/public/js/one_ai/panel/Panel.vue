<!-- The panel: a list of conversations, and one conversation.

     Two views rather than a channel rail, because a list of threads is the
     shape OneMessaging will want too — its threads join this list rather than
     needing a second panel drawn beside this one. -->
<template>
	<div class="one-ai-panel one-float" :class="`one-ai-panel--${size}`" data-tour="oneai-panel">
		<div class="one-ai-head">
			<button
				v-if="view === 'chat'"
				class="one-ai-icon"
				:title="__('All conversations')"
				@click="toThreads"
			>
				<Icon name="chevron-left" />
			</button>
			<img v-else class="one-ai-head__mark" :src="mark" alt="" />

			<div class="one-ai-head__title">
				<button
					v-if="view === 'chat' && chat.name"
					class="one-ai-head__name"
					:title="__('Rename')"
					@click="rename"
				>
					{{ chat.title || __("New conversation") }}
				</button>
				<template v-else>{{ view === "chat" ? __("New conversation") : ONEAI }}</template>
				<span class="one-ai-head__sub">{{ subtitle }}</span>
			</div>

			<button class="one-ai-icon" :title="__('New conversation')" data-tour="oneai-new" @click="fresh">
				<Icon name="square-pen" />
			</button>
			<button class="one-ai-icon" :title="bigger" data-tour="oneai-grow" @click="grow">
				<Icon :name="size === 'full' ? 'minimize-2' : 'maximize-2'" />
			</button>
			<button class="one-ai-icon" :title="__('Close')" @click="$emit('closed')">
				<Icon name="x" />
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
				<button class="one-ai-remembers" @click="toMemory">
					<Icon name="brain" />
					<span>{{ __("What OneAI remembers") }}</span>
				</button>
			</template>

			<template v-else>
				<div v-if="!chat.said.length && target" class="one-ai-empty">
					{{ __("Say what to write in {0}, or pick one of these.", [target.label]) }}
					<div class="one-ai-quick">
						<button v-for="one in quick" :key="one.label" class="one-ai-quick__one" :disabled="busy" @click="take(one)">
							{{ one.label }}
						</button>
					</div>
				</div>
				<div v-else-if="!chat.said.length" class="one-ai-empty">
					<div class="one-ai-empty__ask">{{ __("What would you like to do?") }}</div>
					<div v-if="offered.length" class="one-ai-quick">
						<button v-for="one in offered" :key="one.label" class="one-ai-quick__one" :disabled="busy" @click="take(one)">
							{{ one.label }}
						</button>
					</div>
					<div v-else>{{ __("Ask about this page, look something up, or have a change suggested.") }}</div>
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
							<Icon name="file" size="xs" />
							<span>{{ file.name }}</span>
						</a>
					</div>

					<div v-if="said.text" class="one-ai-said__text" :class="{ 'one-ai-prose': said.role === 'model' }">
						<span class="one-ai-said__who">{{ said.role === "you" ? __("You") : ONEAI }}</span>
						<span v-if="said.role === 'you'">{{ said.text }}</span>
						<span v-else v-html="prose(said.text)"></span>
					</div>

					<template v-for="(look, i) in said.looked" :key="i">
						<div v-if="look.error || (!look.records.length && !look.card && !look.found && !drew(said))" class="one-ai-looked"
							:class="{ 'one-ai-looked--refused': look.error }">
							<span class="one-ai-looked__dot"></span>
							<span>{{ look.error || told(look) }}</span>
						</div>

						<Found v-if="look.found" :found="look.found" />
						<Record v-for="rec in look.records" :key="rec.name" :record="rec" />
						<div v-if="look.more" class="one-ai-looked">
							<span class="one-ai-looked__dot"></span>
							<span>{{ __("and {0} more", [look.more]) }}</span>
						</div>
					</template>

					<div v-for="kept in said.remembered || []" :key="kept.memory" class="one-ai-looked one-ai-kept">
						<span class="one-ai-looked__dot"></span>
						<span>{{ kept.undone ? __("Forgotten") : __("Remembered: {0}", [kept.fact]) }}</span>
						<button v-if="!kept.undone" class="one-ai-kept__undo" @click="unremember(kept)">{{ __("Undo") }}</button>
					</div>

					<Record
						v-for="name in said.cards"
						:key="name"
						:record="(cards[name] && cards[name].shown) || { doctype: '', name: '', title: '', fields: [] }"
						:suggested="cards[name] || { name, kind: 'Create', state: 'Proposed' }"
						@answered="answered"
						@failed="mend"
					/>
					<div v-if="waitingIn(said).length > 1" class="one-ai-all">
						<button class="one-ai-btn one-ai-btn--go" :disabled="busy || approving" @click="approveAll(said)">
							{{ __("Approve All ({0})", [waitingIn(said).length]) }}
						</button>
					</div>
				</div>

				<div v-if="busy" class="one-ai-thinking">
					<div v-for="(step, at) in steps" :key="at" class="one-ai-thinking__done">{{ step }}</div>
					<div class="one-ai-thinking__now">
						<span class="one-ai-thinking__bloom"></span>
						<span>{{ doing }}</span>
					</div>
				</div>

				<div v-if="broke" class="one-ai-broke">
					<div class="one-ai-broke__said">{{ broke }}</div>
					<button class="btn btn-default btn-xs" @click="send(lastAsked)">{{ __("Try again") }}</button>
				</div>
			</template>
		</div>

		<div v-if="view === 'chat'" class="one-ai-foot">
			<div v-if="target" class="one-ai-here">
				<span>{{ __("Writing") }}</span>
				<span class="one-ai-here__chip one-ai-here__chip--target">
					{{ target.label }}
					<button class="one-ai-waiting__off" :title="__('Stop writing this field')" @click="target = null">×</button>
				</span>
			</div>
			<div v-else-if="here" class="one-ai-here">
				<span>{{ __("Knows about") }}</span>
				<button
					class="one-ai-here__chip"
					:aria-pressed="String(useHere)"
					:title="useHere ? __('Stop sending this') : __('Send this again')"
					@click="useHere = !useHere"
				>
					{{ here.label }}
				</button>
				<span v-if="about && useHere" class="one-ai-here__chip one-ai-here__chip--target">
					{{ about.label }}
					<button class="one-ai-waiting__off" :title="__('Stop asking about this field')" @click="about = null">×</button>
				</span>
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
						<Icon name="plus" />
					</button>

					<button
						v-if="Hearing"
						class="one-ai-round one-ai-mic"
						:class="{ 'one-ai-mic--on': listening }"
						:title="listening ? __('Stop listening') : __('Speak')"
						:disabled="busy"
						@click="listen"
					>
						<Icon name="mic" />
					</button>
					<button
						class="one-ai-send"
						:class="{ 'one-ai-send--alone': !Hearing }"
						:disabled="busy || (!text.trim() && !waiting.length)"
						:title="__('Send')"
						@click="send()"
					>
						<Icon name="arrow-up" />
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
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

import Found from "./Found.vue";
import Record from "./Record.vue";
import Icon from "./Icon.vue";

const __ = window.__;
const mark = "/assets/onedesk/images/oneai.svg";

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

const target = ref(null);

// The field the reader was in when they opened the panel, when it is not one
// OneAI writes: what a question is about (oneai.js, justLeft).
const about = ref(null);

const steps = ref([]);

const offered = ref([]);
watch(
	() => props.here,
	() => !chat.value.said.length && offer(),
);
const POLL = 5000;
let watching = null;
frappe.realtime.on("one_ai_run", heard);
frappe.realtime.on("one_ai_title", titled);
onBeforeUnmount(() => {
	frappe.realtime.off("one_ai_run", heard);
	frappe.realtime.off("one_ai_title", titled);
	menu && menu.destroy();
	stop();
});

const said = (label) => ({ label, ask: label });
const quick = computed(() => {
	if (!target.value) return [];
	if (!words(current())) {
		return target.value.email && target.value.quoted
			? [said(__("Write a first draft")), { label: __("Reply saying…"), ask: __("Write a reply that says: "), fill: true }]
			: [said(__("Write a first draft"))];
	}
	if (!target.value.email) return [said(__("Improve it")), said(__("Make it shorter")), said(__("Fix spelling and grammar"))];
	return [
		said(__("Improve it")),
		said(__("Make it shorter")),
		said(__("Make it longer")),
		said(__("Make it more formal")),
		said(__("Make it friendlier")),
		said(__("Fix spelling and grammar")),
		{ label: __("Translate…"), ask: __("Translate it into "), fill: true },
	];
});

const words = (html) => $("<div>").html(String(html || "")).text().trim();

const Hearing = window.SpeechRecognition || window.webkitSpeechRecognition;
let ear = null;

const SIZES = ["snug", "roomy", "full"];

const bigger = computed(() =>
	size.value === "full" ? __("Make it smaller") : __("Make it bigger")
);

frappe.model.user_settings.get("AI Chat").then((kept) => {
	frappe.model.user_settings["AI Chat"] = kept || {};
	if (SIZES.includes((kept || {}).panel_size)) size.value = kept.panel_size;
});

function grow() {
	const at = SIZES.indexOf(size.value);
	size.value = SIZES[(at + 1) % SIZES.length];
	frappe.model.user_settings.save("AI Chat", "panel_size", size.value);
}

function prose(text) {
	return frappe.markdown(text || "");
}

const subtitle = computed(() => {
	if (view.value === "threads") return __("Your conversations");
	return chat.value.name ? __("Kept") : __("Answers from your own records");
});

defineExpose({
	async opened(opening) {
		if (opening && opening.chat) return openChat(opening.chat);
		if (opening && opening.fresh) return fresh();
		if (opening && opening.ask) {
			fresh();
			aimed.value = opening.about && props.here ? { ...props.here, field: opening.about } : null;
			await ask(opening.ask);
			aimed.value = null;
			return;
		}
		if (opening && opening.field) {
			fresh();
			target.value = opening.field;
			return;
		}
		if (opening && opening.about) {
			fresh();
			about.value = opening.about;
			return;
		}
		fresh();
	},
});

async function list() {
	view.value = "threads";
	threads.value = await frappe.xcall("onedesk.one_ai.chat.chats");
}

async function openChat(name) {
	stop();
	busy.value = false;
	chat.value = await frappe.xcall("onedesk.one_ai.chat.opened", { chat: name });
	if (!chat.value.said.length) offer();
	if (chat.value.running) {
		doing.value = __("Thinking…");
		follow(chat.value.running);
	}
	view.value = "chat";
	await load();
	toBottom();
}

function fresh() {
	stop();
	busy.value = false;
	target.value = null;
	about.value = null;
	chat.value = { name: null, title: null, said: [], spent: 0 };
	cards.value = {};
	view.value = "chat";
	nextTick(() => box.value && box.value.focus());
	offer();
	frappe.xcall("onedesk.one_ai.chat.opened").then((empty) => {
		if (!chat.value.name) chat.value = { ...chat.value, ...empty, said: chat.value.said };
	});
}

function toThreads() {
	list();
}

const SETTLE = 1200;

async function attach(then) {
	if (!chat.value.name) {
		chat.value = await frappe.xcall("onedesk.one_ai.chat.start");
	}
	let settle = null;
	new frappe.ui.FileUploader({
		doctype: "AI Chat",
		docname: chat.value.name,
		frm: null,
		on_success: (file) => {
			waiting.value.push({ name: file.file_name, url: file.file_url });
			if (!then) return;
			clearTimeout(settle);
			settle = setTimeout(() => nextTick(then), SETTLE);
		},
	});
}

async function offer() {
	offered.value = [];
	try {
		offered.value = await frappe.xcall("onedesk.one_ai.chat.suggestions", {
			page: (useHere.value && props.here) || onedesk.oneai.home(),
		});
	} catch (e) {
	}
}

function take(one) {
	if (one.run) return run(one);
	if (one.fill) {
		text.value = one.ask;
		nextTick(() => {
			if (!box.value) return;
			box.value.focus();
			box.value.setSelectionRange(text.value.length, text.value.length);
		});
		return;
	}
	if (one.file) return attach(() => ask(one.ask));
	ask(one.ask);
}

async function run(one) {
	const name = props.here && props.here.name;
	if (!name) return;
	chat.value.said.push({ role: "you", text: one.label, looked: [], cards: [], files: [] });
	busy.value = true;
	try {
		await frappe.xcall(one.run, { [one.arg]: name });
		chat.value.said.push({ role: "model", text: one.said, looked: [], cards: [], files: [] });
	} catch (e) {
	} finally {
		busy.value = false;
		toBottom();
	}
}

function ask(one) {
	text.value = one;
	return send();
}

function current() {
	const aim = target.value;
	if (!aim) return "";
	if (aim.email) {
		const writing = onedesk.oneai.writing;
		return writing && writing.composer.dialog.display ? onedesk.oneai.parts(writing).written : aim.value || "";
	}
	const frm = window.cur_frm;
	const same = frm && frm.doctype === aim.doctype && (aim.name ? frm.docname === aim.name : frm.is_new());
	return same ? frm.doc[aim.fieldname] || "" : aim.value || "";
}

function latest() {
	const writing = target.value && target.value.email && onedesk.oneai.writing;
	if (!writing || !writing.composer.dialog.display) return {};
	const dialog = writing.composer.dialog;
	return { subject: dialog.get_value("subject") || "", to: dialog.get_value("recipients") || "" };
}

function rename() {
	const named = chat.value.name;
	frappe.prompt(
		{ fieldname: "title", fieldtype: "Data", label: __("Name"), default: chat.value.title, reqd: 1 },
		async ({ title }) => {
			const now = await frappe.xcall("onedesk.one_ai.chat.rename", { chat: named, title });
			titled(now.name === named ? { chat: named, title: now.title } : {});
		},
		__("Rename Conversation"),
		__("Rename"),
	);
}

function titled(said) {
	if (!said || !said.chat) return;
	if (chat.value.name === said.chat) chat.value = { ...chat.value, title: said.title };
	threads.value = threads.value.map((one) => (one.name === said.chat ? { ...one, title: said.title } : one));
}

const aimed = ref(null);

// The page as it is when the question is sent: what is selected in a
// document or a workbook now, not when the page was opened (kit/desk.js, aiSees).
const seeing = (here) => {
	const seen = onedesk.oneai.seen;
	return { ...here, selection: seen && here.page && seen.page === here.page ? seen : null };
};

function toMemory() {
	onedesk.ai_center.open({ at: "yours" });
}

async function unremember(kept) {
	await frappe.xcall("onedesk.one_ai.yours.forget", { name: kept.memory });
	kept.undone = true;
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

	const sending = waiting.value.splice(0);
	if (!again) {
		chat.value.said.push({ role: "you", text: asked, looked: [], cards: [], files: sending });
	}
	toBottom();

	steps.value = [];

	try {
		const started = await frappe.xcall("onedesk.one_ai.chat.say", {
			text: asked,
			chat: chat.value.name,
			page: aimed.value || (useHere.value && props.here ? { ...seeing(props.here), ...(about.value ? { field: about.value.fieldname } : {}) } : null),
			files: sending.map((one) => one.url),
			field: target.value ? { ...target.value, value: current(), ...latest() } : null,
		});
		chat.value = started;
		follow(started.run);
	} catch (raised) {
		fail(_why(raised));
		frappe.hide_msgprint && frappe.hide_msgprint();
	}
	toBottom();
}

function follow(run) {
	stop();
	busy.value = true;
	watching = {
		run,
		poll: setInterval(
			() => frappe.xcall("onedesk.one_ai.chat.progress", { run }).then((state) => heard({ ...state, run })),
			POLL
		),
	};
}

function stop() {
	if (watching) clearInterval(watching.poll);
	watching = null;
}

function heard(step) {
	if (!watching || !step || step.run !== watching.run) return;
	if (step.steps) steps.value = step.steps.map(told);
	else if (step.tool) steps.value = [...steps.value, told(step)];
	if (step.thinking !== undefined) {
		doing.value = step.thinking ? __("Reading what it found…") : __("Thinking…");
	}
	if (step.done) return finish();
	if (step.failed) return fail(step.failed);
	toBottom();
}

async function finish() {
	stop();
	chat.value = await frappe.xcall("onedesk.one_ai.chat.opened", { chat: chat.value.name });
	await load();
	emit("counted");
	busy.value = false;
	steps.value = [];
	toBottom();
}

function fail(reason) {
	stop();
	broke.value = reason;
	busy.value = false;
	steps.value = [];
	toBottom();
}

function _why(raised) {
	const last = frappe.last_response || {};
	let said = "";
	try {
		said = JSON.parse(last._server_messages || "[]")[0] || "";
		said = JSON.parse(said).message || said;
	} catch (e) {
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

// The cards of one answer still waiting, which Approve All approves in the
// order they were suggested: a card pointing at another approves it first.
function waitingIn(said) {
	return (said.cards || []).filter((name) => cards.value[name] && cards.value[name].state === "Proposed");
}

const approving = ref(false);

async function approveAll(said) {
	const names = waitingIn(said);
	approving.value = true;
	try {
		await frappe.xcall("onedesk.one_ai.run.apply_all", { proposals: names });
		await answered();
	} catch (raised) {
		await answered();
		mend(names.find((name) => cards.value[name] && cards.value[name].state === "Proposed") || names[0], raised);
	} finally {
		approving.value = false;
	}
}

// A card that would not go through is handed back to OneAI with what went
// wrong, to be corrected and suggested again, rather than left as a red
// message the person has to turn into a question themselves.
function mend(name, raised) {
	const card = cards.value[name] || {};
	const reason = _why(raised);
	frappe.hide_msgprint && frappe.hide_msgprint();
	if (busy.value) return;
	text.value = __("Approving “{0}” did not go through: {1} Correct it and suggest it again.", [card.said || name, reason]);
	send();
}

function drew(said) {
	return (said.looked || []).some((look) => look.found || (look.records || []).length);
}

function told(look) {
	const what = (look.args && (look.args.doctype || look.args.name)) || "";
	if (!look.ran) return what ? __("Suggested a change to {0}", [what]) : __("Suggested a change");
	return what ? __("Looked at {0}", [what]) : __("Looked something up");
}

function when(said) {
	return said ? $("<span>").html(frappe.datetime.comment_when(said)).text() : "";
}

function format(credits) {
	return format_number(credits || 0, null, 4);
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
