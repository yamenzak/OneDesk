<template>
  <div class="mx-auto flex w-full max-w-4xl flex-col gap-5 px-5 py-6">
    <Loading v-if="!boards" />
    <p v-else-if="!boards.length" class="text-base text-ink-gray-5">{{ __("No boards") }}</p>
    <template v-else>
      <div class="flex flex-wrap items-center gap-2">
        <Select v-if="boards.length > 1 && !only" v-model="board" class="w-56" :options="boards.map((one) => one.board)" />
        <Button v-if="only" variant="ghost" icon-left="lucide-layout-grid" :label="__('Every Item')" @click="only = null" />
      </div>
      <Loading v-if="!state" />
      <div v-else-if="only && item" class="flex flex-col items-center gap-4 rounded-3 border border-outline-gray-2 p-6 text-center">
        <p class="text-lg font-medium text-ink-gray-8">{{ item.item }}</p>
        <p class="text-5xl font-bold text-ink-gray-9">{{ item.state || item.value || "—" }}</p>
        <p class="text-base text-ink-gray-5">{{ under(item) }}</p>
        <Controls :item="item" :state="state" :busy="busy" size="lg" @change="change" />
      </div>
      <div v-else class="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
        <div v-for="one in state.items" :key="one.item" role="button" tabindex="0" class="flex cursor-pointer flex-col items-start gap-1 rounded-3 border border-outline-gray-2 p-4 text-start hover:bg-surface-gray-1" :class="picked === one.item ? 'border-outline-gray-4 bg-surface-gray-1' : ''" @click="picked = picked === one.item ? null : one.item" @keydown.enter="picked = one.item">
          <span class="text-base font-medium text-ink-gray-8">{{ one.item }}</span>
          <span class="flex items-center gap-2 text-lg font-semibold text-ink-gray-9">
            <span v-if="one.colour" class="size-3 rounded-full" :style="{ background: one.colour }" />
            {{ one.state || one.value || "—" }}
          </span>
          <span class="text-sm" :class="one.over ? 'text-ink-red-4' : 'text-ink-gray-5'">{{ under(one) }}</span>
          <Controls v-if="picked === one.item" :item="one" :state="state" :busy="busy" class="mt-2" @change="change" @click.stop />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, onUnmounted, ref, watch } from "vue";
import { Button, Select, TextInput } from "frappe-ui";

import { Loading, __, call, getQuery, listen } from "../kit";

const API = "onedesk.one_display.boards.";
const EVERY = 15000;

const boards = ref(null);
const board = ref(getQuery("board"));
const only = ref(getQuery("item"));
const picked = ref(null);
const state = ref(null);
const busy = ref(false);
let timer = null;

const item = computed(() => state.value?.items.find((one) => one.item === only.value));

function minutes(one) {
  if (one.minutes == null) return "";
  const whole = Math.floor(one.minutes);
  return whole < 60 ? __("{0} min", [whole]) : __("{0} h {1}", [Math.floor(whole / 60), String(whole % 60).padStart(2, "0")]);
}

// what sits under a state: the value beside it, how long, and past its limit
const under = (one) => [one.state && one.value ? `${state.value?.value_label || __("Value")}: ${one.value}` : "", minutes(one), one.over ? __("Over time limit") : ""].filter(Boolean).join(" · ");

async function load() {
  clearTimeout(timer);
  if (!board.value) return;
  state.value = await call(API + "get", { board: board.value });
  timer = setTimeout(load, EVERY);
}

async function change(args) {
  busy.value = true;
  try {
    state.value = await call(API + "change", { board: board.value, ...args });
  } finally {
    busy.value = false;
  }
}

// an item's buttons: its states, and its value stepped or written
const Controls = defineComponent({
  props: { item: Object, state: Object, busy: Boolean, size: { type: String, default: "md" } },
  emits: ["change"],
  setup(props, { emit }) {
    const typed = ref("");
    return () => {
      const one = props.item;
      const states = props.state.states.map((row) =>
        h(Button, {
          key: row.state,
          size: props.size,
          variant: row.state === one.state ? "solid" : "subtle",
          label: row.state,
          disabled: props.busy,
          onClick: (event) => {
            event.stopPropagation();
            emit("change", { item: one.item, state: row.state });
          },
        }),
      );
      const value = props.state.value_label
        ? props.state.value_kind === "Number"
          ? [
              h(Button, { size: props.size, icon: "lucide-minus", "aria-label": __("Less"), onClick: (event) => (event.stopPropagation(), emit("change", { item: one.item, step: -1 })) }),
              h("span", { class: "min-w-12 text-center text-xl font-semibold tabular-nums text-ink-gray-9" }, one.value || "0"),
              h(Button, { size: props.size, icon: "lucide-plus", "aria-label": __("More"), onClick: (event) => (event.stopPropagation(), emit("change", { item: one.item, step: 1 })) }),
            ]
          : [
              h(TextInput, { modelValue: typed.value, placeholder: props.state.value_label, "onUpdate:modelValue": (v) => (typed.value = v), onClick: (event) => event.stopPropagation() }),
              h(Button, { size: props.size, label: __("Set"), onClick: (event) => (event.stopPropagation(), emit("change", { item: one.item, value: typed.value }), (typed.value = "")) }),
            ]
        : [];
      return h("div", { class: "flex flex-col items-center gap-3" }, [
        states.length ? h("div", { class: "flex flex-wrap justify-center gap-2" }, states) : null,
        value.length ? h("div", { class: "flex items-center justify-center gap-2" }, value) : null,
      ]);
    };
  },
});

watch(board, () => {
  state.value = null;
  picked.value = null;
  load();
});

// another phone's change reaches this one at once
const unheard = listen("onedesk_board", (said) => said?.board === board.value && load());

onMounted(async () => {
  boards.value = await call(API + "mine");
  if (!board.value || !boards.value.some((one) => one.board === board.value)) board.value = boards.value[0]?.board || null;
  else load();
});

onUnmounted(() => {
  clearTimeout(timer);
  unheard();
});
</script>
