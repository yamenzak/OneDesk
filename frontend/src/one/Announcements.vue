<template>
  <Page data-tour="one-news">
    <Loading v-if="!said" />
    <template v-else>
      <ViewTabs v-model="shown" :views="views" class="mt-4" data-tour="one-news-views" />
      <p v-if="!rows.length" class="py-16 text-center text-base text-ink-gray-5">{{ empty }}</p>
      <article v-for="one in rows" :key="one.name" class="border-b border-outline-gray-1 py-6 last:border-0" data-tour="one-news-card">
        <header class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0">
            <h2 class="text-xl font-semibold text-ink-gray-9"><Branded :text="one.title" /></h2>
            <p class="mt-1 text-sm text-ink-gray-5">{{ byline(one) }}</p>
          </div>
          <div v-if="said.posts" class="flex shrink-0 items-center gap-1">
            <Button variant="ghost" :label="__('Edit')" @click="go(`/desk/note/${encodeURIComponent(one.name)}`)" />
            <Button v-if="one.running" variant="ghost" :label="__('Stop Showing')" @click="stop(one)" />
          </div>
        </header>
        <div class="prose prose-sm mt-4 max-w-none text-ink-gray-8" v-html="one.html" />
        <div v-if="one.seen" class="mt-4 text-sm text-ink-gray-5">
          <button v-if="one.seen.length" type="button" class="hover:underline" :aria-expanded="opened === one.name" @click="opened = opened === one.name ? null : one.name">
            {{ __("Seen by {0} of {1}", [one.seen.length, said.people]) }}
          </button>
          <span v-else>{{ __("Nobody has seen it yet") }}</span>
          <p v-if="opened === one.name" class="mt-2 text-ink-gray-7">{{ andList(one.seen) }}</p>
        </div>
      </article>
    </template>
  </Page>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Button } from "frappe-ui";

import { Branded, Loading, Page, ViewTabs, __, ago, andList, ask, call, date, followList, get, go, listen, newDoc, setQuery } from "../kit";

const props = defineProps({ query: { type: Object, default: () => ({}) }, onTitle: Function, onActions: Function });

const said = ref(null);
const shown = ref(props.query.view === "earlier" ? "earlier" : "now");
const opened = ref(null);

async function load() {
  said.value = await get("onedesk.one.announcements.read");
  props.onTitle?.({ title: __("Announcements") });
  props.onActions?.(said.value.posts ? [{ label: __("New Announcement"), primary: true, onClick: () => newDoc("Note", { public: 1, notify_on_login: 1 }) }] : []);
}
load();
watch(shown, (now) => setQuery("view", now === "now" ? null : now));
const unheard = [followList("Note", load), followList("User", load), listen("one_announcements", load)];
onBeforeUnmount(() => unheard.forEach((one) => one()));

const now = computed(() => said.value.rows.filter((one) => one.running));
const earlier = computed(() => said.value.rows.filter((one) => !one.running));
const rows = computed(() => (shown.value === "now" ? now.value : earlier.value));
const views = computed(() => [
  { key: "now", label: __("Showing Now"), count: now.value.length || null },
  { key: "earlier", label: __("Earlier"), count: earlier.value.length || null },
]);
const empty = computed(() => (shown.value === "now" ? __("Nothing is being announced.") : __("Nothing was announced before.")));

function byline(one) {
  const posted = __("{0}, {1}", [one.by, ago(one.on)]);
  if (one.running && one.until) return `${posted} · ${__("Showing until {0}", [date(one.until)])}`;
  if (one.ended) return `${posted} · ${__("Stopped {0}", [date(one.until)])}`;
  return posted;
}

function stop(one) {
  ask(__("Stop showing {0}? It stays here under Earlier.", [one.title]), () => call("onedesk.one.announcements.stop", { name: one.name }).then(load));
}
</script>
