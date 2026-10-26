<template>
  <div class="flex min-h-full flex-col text-ink-gray-8 md:flex-row" data-tour="one-book">
    <section class="flex w-full shrink-0 flex-col border-outline-gray-1 md:w-96 md:border-e" :class="{ 'max-md:hidden': chosen }" data-tour="one-book-list">
      <div class="px-4 pt-4">
        <ViewTabs v-model="view" :views="views" />
        <TextInput v-model="search" class="mt-3 w-full" type="search" :placeholder="__('Search')" :aria-label="__('Search')">
          <template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
        </TextInput>
      </div>
      <Loading v-if="!said" />
      <p v-else-if="!said.rows.length" class="px-4 py-12 text-center text-base text-ink-gray-5">{{ search ? __("Nothing matches") : view === "contacts" ? __("No contacts yet.") : __("No addresses yet.") }}</p>
      <ul v-else class="px-2 py-2">
        <li v-for="one in said.rows" :key="one.name">
          <button type="button" class="flex w-full items-center gap-3 rounded-3 px-2 py-2 text-start hover:bg-surface-gray-2 focus-visible:ring-2 focus-visible:ring-outline-gray-3" :class="{ 'bg-surface-gray-3 hover:bg-surface-gray-3': chosen === one.name }" :aria-current="chosen === one.name ? 'true' : undefined" @click="choose(one.name)">
            <Avatar v-if="view === 'contacts'" :label="one.title" :image="one.image" size="lg" />
            <Avatar v-else shape="square" size="lg"><span class="lucide-map-pin size-4" /></Avatar>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-base text-ink-gray-8">{{ one.title }}</span>
              <span class="block truncate text-sm text-ink-gray-5">{{ [one.kind, one.sub, belongs(one)].filter(Boolean).join(" · ") }}</span>
            </span>
          </button>
        </li>
        <li v-if="said.more" class="flex justify-center py-2"><Button :label="__('Show More')" @click="more" /></li>
      </ul>
    </section>

    <section class="min-w-0 flex-1 px-6 py-6" :class="{ 'max-md:hidden': !chosen }" data-tour="one-book-chosen">
      <p v-if="!chosen" class="py-16 text-center text-base text-ink-gray-5">{{ view === "contacts" ? __("Choose a contact to see their details and their addresses.") : __("Choose an address to see it in full and who is there.") }}</p>
      <Loading v-else-if="!picked" />
      <template v-else>
        <Button class="mb-4 md:hidden" variant="ghost" icon-left="lucide-arrow-left" :label="__('Back')" @click="choose(null)" />
        <header class="flex flex-wrap items-start justify-between gap-3">
          <div class="flex min-w-0 items-center gap-4">
            <Avatar v-if="view === 'contacts'" :label="picked.title" :image="picked.image" size="3xl" />
            <div class="min-w-0">
              <h2 class="truncate text-2xl font-semibold text-ink-gray-9">{{ picked.title }}</h2>
              <p v-if="picked.role || picked.kind" class="mt-1 text-base text-ink-gray-5">{{ picked.role || picked.kind }}</p>
            </div>
          </div>
          <Button v-if="picked.writes" :label="__('Edit')" @click="go(record(kind, picked.name))" />
        </header>

        <Section v-if="view === 'contacts'" :title="__('Reach')">
          <dl class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div v-for="one in picked.emails" :key="one.email">
              <dt class="text-sm text-ink-gray-5">{{ one.primary ? __("Email") : __("Other Email") }}</dt>
              <dd><a class="text-base text-ink-gray-8 hover:underline" :href="`mailto:${one.email}`">{{ one.email }}</a></dd>
            </div>
            <div v-for="one in picked.phones" :key="one.phone">
              <dt class="text-sm text-ink-gray-5">{{ one.mobile ? __("Mobile") : __("Phone") }}</dt>
              <dd><a class="text-base tabular-nums text-ink-gray-8 hover:underline" :href="`tel:${one.phone}`">{{ one.phone }}</a></dd>
            </div>
          </dl>
          <p v-if="!picked.emails.length && !picked.phones.length" class="text-base text-ink-gray-5">{{ __("No email or phone yet.") }}</p>
        </Section>
        <Section v-else :title="__('Address')">
          <p class="text-base" v-html="picked.text" />
          <p v-if="picked.email || picked.phone" class="mt-2 text-base text-ink-gray-7">{{ [picked.email, picked.phone].filter(Boolean).join(" · ") }}</p>
        </Section>

        <Section :title="__('Belongs To')" :aside="picked.links.length || null">
          <Rows :rows="picked.links.map((one) => ({ key: `${one.doctype}-${one.name}`, label: one.title, sub: __(one.doctype), icon: 'lucide-link', route: record(one.doctype, one.name) }))" :empty="__('Nobody yet. Add who it belongs to in Edit.')" />
        </Section>

        <Section v-if="view === 'contacts'" :title="__('Their Addresses')" :aside="picked.places.length || null">
          <p v-if="!picked.places.length" class="text-base text-ink-gray-5">{{ __("None of the records they belong to has an address yet.") }}</p>
          <ul class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <li v-for="one in picked.places" :key="one.name">
              <button type="button" class="w-full rounded-4 border border-outline-gray-1 px-4 py-3 text-start text-base hover:bg-surface-gray-2" @click="jump('addresses', one.name)"><span v-html="one.text" /></button>
            </li>
          </ul>
        </Section>
        <Section v-else :title="__('People There')" :aside="picked.people.length || null">
          <Rows :rows="picked.people.map((one) => ({ key: one.name, label: one.title, sub: one.sub, avatar: one.title, onClick: () => jump('contacts', one.name) }))" :empty="__('Nobody linked to it has a contact yet.')" />
        </Section>
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { Avatar, Button, TextInput } from "frappe-ui";

import { Loading, Rows, Section, ViewTabs, __, followList, get, go, newDoc, setQuery } from "../kit";

const props = defineProps({ query: { type: Object, default: () => ({}) }, onTitle: Function, onActions: Function });

const view = ref(props.query.view === "addresses" ? "addresses" : "contacts");
const chosen = ref(props.query.name || null);
const search = ref("");
const said = ref(null);
const picked = ref(null);

const kind = computed(() => (view.value === "contacts" ? "Contact" : "Address"));
const views = computed(() => [
  { key: "contacts", label: __("Contacts"), icon: "lucide-user" },
  { key: "addresses", label: __("Addresses"), icon: "lucide-map-pin" },
]);

async function load() {
  said.value = await get("onedesk.one.address_book.read", { view: view.value, search: search.value || null });
  report();
}

async function more() {
  const got = await get("onedesk.one.address_book.read", { view: view.value, search: search.value || null, start: said.value.rows.length });
  said.value = { ...got, rows: [...said.value.rows, ...got.rows] };
}

async function show() {
  picked.value = null;
  if (chosen.value) picked.value = await get("onedesk.one.address_book.one", { view: view.value, name: chosen.value });
}

function choose(name) {
  chosen.value = name;
  setQuery("name", name);
  show();
}

function jump(to, name) {
  jumping = true;
  view.value = to;
  choose(name);
  nextTick(() => (jumping = false));
}

let timer = null;
watch(search, () => {
  clearTimeout(timer);
  timer = setTimeout(load, 250);
});
let jumping = false;
watch(view, (now) => {
  setQuery("view", now === "contacts" ? null : now);
  if (!jumping) {
    chosen.value = null;
    picked.value = null;
    setQuery("name", null);
  }
  search.value = "";
  load();
});
load();
show();
// The rail's Contacts and Addresses are this page with another ?view=.
watch(
  () => props.query.view,
  (asked) => {
    const now = asked === "addresses" ? "addresses" : "contacts";
    if (now !== view.value) view.value = now;
  }
);
const unheard = ["Contact", "Address"].map((one) =>
  followList(one, () => {
    load();
    if (chosen.value) show();
  })
);
onBeforeUnmount(() => {
  unheard.forEach((one) => one());
  clearTimeout(timer);
});

const slug = (doctype) => doctype.toLowerCase().replace(/ /g, "-");
const record = (doctype, name) => `/desk/${slug(doctype)}/${encodeURIComponent(name)}`;
const belongs = (one) => one.links.map((link) => link.title).join(", ");

function report() {
  props.onTitle?.({ title: __("Address Book") });
  props.onActions?.(said.value?.makes ? [{ label: view.value === "contacts" ? __("New Contact") : __("New Address"), primary: true, onClick: () => newDoc(kind.value) }] : []);
}
</script>
