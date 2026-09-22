<!-- The panel: a list of conversations, and one conversation.

     Two views rather than a channel rail, because a list of threads is the
     shape OneMessaging will want too — its threads join this list rather than
     needing a second panel drawn beside this one. -->
<template>
	<div class="one-ai-panel" :class="{ 'one-ai-panel--wide': wide }">
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
			<button class="one-ai-icon" :title="wide ? __('Narrow') : __('Widen')" @click="wide = !wide">
				<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.6">
					<path d="M6 3H3v3M10 13h3v-3" stroke-linecap="round" stroke-linejoin="round" />
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
					<div v-if="opens(at)" class="one-ai-said__who">
						{{ said.role === "you" ? __("You") : ONEAI }}
					</div>
					<div v-if="said.text" class="one-ai-said__text">{{ said.text }}</div>

					<div
						v-for="(look, i) in said.looked"
						:key="i"
						class="one-ai-looked"
						:class="{ 'one-ai-looked--refused': look.error }"
					>
						<span class="one-ai-looked__dot"></span>
						<span>{{ look.error || told(look) }}</span>
					</div>

					<Card
						v-for="name in said.cards"
						:key="name"
						:card="cards[name] || { name, kind: __('Suggested'), state: 'Proposed' }"
						@answered="answered"
					/>
				</div>

				<div v-if="busy" class="one-ai-thinking">
					<span class="one-ai-thinking__bloom"></span>
					<span>{{ __("Looking…") }}</span>
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

			<div class="one-ai-ask">
				<textarea
					ref="box"
					v-model="text"
					rows="1"
					:placeholder="__('Ask {0}', [ONEAI])"
					@keydown.enter.exact.prevent="send"
					@input="grow"
				></textarea>
				<button class="one-ai-send" :disabled="busy || !text.trim()" :title="__('Send')" @click="send">
					<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.7">
						<path d="M3 8h9M8.5 4l4 4-4 4" stroke-linecap="round" stroke-linejoin="round" />
					</svg>
				</button>
			</div>

			<div v-if="chat.spent" class="one-ai-spent">
				{{ __("{0} credits in this conversation", [format(chat.spent)]) }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, ref } from "vue";

import Card from "./Card.vue";

const __ = window.__;
const mark = "/assets/onedesk/images/oneai.svg";

// A product name is a name. It is the same in every language, so it is written
// here once and never passed through `__()`.
const ONEAI = "OneAI";

const props = defineProps({ here: { type: Object, default: null } });
const emit = defineEmits(["closed", "counted"]);

const view = ref("threads");
const wide = ref(false);
const busy = ref(false);
const text = ref("");
const threads = ref([]);
const cards = ref({});
const chat = ref({ name: null, title: null, said: [], spent: 0 });
const useHere = ref(true);
const body = ref(null);
const box = ref(null);

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
}

function toThreads() {
	list();
}

async function send() {
	const asked = text.value.trim();
	if (!asked || busy.value) return;
	text.value = "";
	grow();
	busy.value = true;

	// Shown before it is sent, so the question is on screen while the model is
	// still thinking about it rather than appearing with the answer.
	chat.value.said.push({ role: "you", text: asked, looked: [], cards: [] });
	toBottom();

	try {
		chat.value = await frappe.xcall("onedesk.one_ai.chat.say", {
			text: asked,
			chat: chat.value.name,
			page: useHere.value && props.here ? props.here : null,
		});
		await load();
		emit("counted");
	} finally {
		busy.value = false;
		toBottom();
	}
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

// A run of turns from the same side is named once. The model looking something
// up and then answering is one thing it did, not two.
function opens(at) {
	const said = chat.value.said;
	return at === 0 || said[at - 1].role !== said[at].role;
}

function grow() {
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
