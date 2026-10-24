<template>
  <Loading v-if="!said || !read" />
  <div v-else class="flex min-h-full text-ink-gray-8">
    <nav class="w-64 shrink-0 border-e border-outline-gray-1 max-md:hidden" :aria-label="__('Documents')">
      <template v-for="group in groups" :key="group.label">
        <div class="px-4 pb-1.5 pt-4 text-xs font-medium text-ink-gray-5">{{ group.label }}</div>
        <a
          v-for="one in group.rows"
          :key="one.key"
          :href="`/desk/legal?document=${encodeURIComponent(one.key)}`"
          class="flex items-center gap-2 border-b border-outline-gray-1 px-4 py-2.5 text-base text-ink-gray-8 hover:bg-surface-gray-2"
          :class="{ 'bg-surface-gray-2 font-medium text-ink-gray-9': one.key === doc.key }"
          @click.prevent="open(one.key)"
        >
          <span class="min-w-0 flex-1 truncate">{{ one.title }}</span>
          <Badge v-if="state(one)" :label="state(one).label" :theme="state(one).theme" size="sm" />
        </a>
      </template>
    </nav>

    <section class="min-w-0 flex-1">
      <div class="flex items-center gap-2 border-b border-outline-gray-1 px-4 py-2.5">
        <span class="truncate font-semibold text-ink-gray-9">{{ read.title }}</span>
        <Badge v-if="read.historic" :label="__('As Agreed, {0}', [read.version])" theme="amber" size="sm" />
        <Badge v-else :label="__('Version {0}', [read.version])" theme="gray" size="sm" />
        <span class="flex-1" />
        <Button v-if="read.historic" variant="subtle" :label="__('Current Version')" @click="open(doc.key)" />
        <Button v-else-if="owed(doc)" variant="solid" :label="__('Agree')" @click="agree" />
      </div>
      <article ref="article" class="prose prose-sm prose-v3 max-w-3xl px-7 pb-12 pt-5 [&_.one-light]:font-light [&_.one-solo]:inline-flex [&_.one-solo]:items-baseline [&_.one-solo]:gap-[0.2em] [&_.one-solo]:whitespace-nowrap [&_.one-mark]:self-center [&_.one-mark]:shrink-0" v-html="text" />
    </section>

    <aside class="w-72 shrink-0 border-s border-outline-gray-1 p-4 text-sm max-lg:hidden">
      <div class="flex size-16 items-center justify-center rounded-4 bg-surface-gray-2 text-ink-gray-6">
        <span class="lucide-scale size-7" aria-hidden="true" />
      </div>
      <div class="mt-3 font-semibold text-ink-gray-9">{{ read.title }}</div>
      <div class="mt-4 space-y-3 border-t border-outline-gray-1 pt-4">
        <template v-if="doc.you || doc.organisation">
          <div v-for="side in sides" :key="side.label">
            <div class="mb-1 text-xs font-medium text-ink-gray-5">{{ side.label }}</div>
            <div>{{ side.said }}</div>
            <a v-if="side.earlier" class="block py-0.5 text-ink-gray-7" href="#" @click.prevent="open(doc.key, side.earlier)">
              {{ __("Read version {0}", [side.earlier]) }}
            </a>
          </div>
        </template>
        <div v-else class="text-ink-gray-5">{{ __("Nobody has to agree to this. It is here to read.") }}</div>
      </div>
      <div v-if="versions.length" class="mt-4 border-t border-outline-gray-1 pt-4">
        <div class="mb-1 text-xs font-medium text-ink-gray-5">{{ __("Earlier Versions") }}</div>
        <a
          v-for="one in versions"
          :key="one.version"
          class="block py-0.5 text-ink-gray-7"
          :class="{ 'font-medium text-ink-gray-9': one.version === version }"
          href="#"
          @click.prevent="open(doc.key, one.version)"
        >
          {{ __("Version {0}", [one.version]) }}
        </a>
      </div>
      <div class="mt-4 border-t border-outline-gray-1 pt-4">
        <div class="mb-1 text-xs font-medium text-ink-gray-5">{{ __("From") }}</div>
        <div>{{ said.party?.legal_name }}</div>
        <a :href="`mailto:${said.party?.email || ''}`">{{ said.party?.email }}</a>
      </div>
      <div v-if="said.admin" class="mt-4 border-t border-outline-gray-1 pt-4">
        <a class="text-ink-gray-7" href="/desk/legal-acceptance">{{ __("Everyone's Agreements") }}</a>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { Badge, Button } from "frappe-ui";

import { Loading, __, alert, call, followList, get, goTo, jq, onedesk, symbol } from "../kit";



const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  onTitle: Function,
});

const said = ref(null);
const read = ref(null);
const history = ref([]);
const doc = ref(null);
const version = ref("");

const owed = (one) => Boolean(one.you?.owed || (said.value.may_bind && one.organisation?.owed));

function state(one) {
  const sides = [one.you, said.value.may_bind || said.value.admin ? one.organisation : null].filter(Boolean);
  if (!sides.length) return null;
  if (sides.some((side) => side.owed && side.version)) return { label: __("Updated"), theme: "amber" };
  if (owed(one)) return { label: __("To Agree"), theme: "amber" };
  if (sides.some((side) => side.owed)) return { label: __("Waiting"), theme: "gray" };
  return { label: __("Agreed"), theme: "green" };
}

const groups = computed(() => {
  const docs = said.value.documents;
  return [
    { label: __("For You"), rows: docs.filter((one) => one.you) },
    { label: __("For Your Organisation"), rows: docs.filter((one) => !one.you && one.organisation) },
    { label: __("To Read"), rows: docs.filter((one) => !one.you && !one.organisation) },
  ].filter((group) => group.rows.length);
});

const text = computed(() => read.value.html.replace(/<h1[^>]*>[\s\S]*?<\/h1>/, ""));

const sides = computed(() =>
  [
    [doc.value.you, "you"],
    [doc.value.organisation, "organisation"],
  ]
    .filter(([side]) => side)
    .map(([side, whose]) => {
      let line;
      if (!side.version) line = side.owed && whose === "organisation" && !said.value.may_bind ? __("Waiting for an administrator") : __("Not agreed yet");
      else if (whose === "organisation") line = __("{0} agreed on {1}", [side.by, side.on]);
      else line = __("Agreed on {0}", [side.on]);
      return {
        label: whose === "organisation" ? __("Your Organisation") : __("You"),
        said: line,
        earlier: side.version && side.version !== side.current ? side.version : null,
      };
    })
);

const versions = computed(() => history.value.filter((one) => one.version !== doc.value.version));

let loads = 0;
async function load(fresh = false) {
  const mine = ++loads;
  if (!said.value || fresh) said.value = await get("onedesk.one_legal.reading.overview");
  const docs = said.value.documents;
  const chosen = docs.find((one) => one.key === props.query.document) || docs.find(owed) || docs[0];
  const asked = props.query.version || "";
  const [got, past] = await Promise.all([
    get("onedesk.one_legal.reading.document", { key: chosen.key, version: asked }),
    get("onedesk.one_legal.reading.history", { key: chosen.key }),
  ]);
  if (mine !== loads) return;
  doc.value = chosen;
  version.value = asked;
  read.value = got;
  history.value = past || [];
  props.onTitle?.(got.title);
  await nextTick();
  brand(article.value);
}

// The desk's observer draws product names with their marks (public/js/brand.js)
// but never reaches into an island, and a mark it draws points at the desk's
// sprite, which an island cannot see: so the names are drawn here, and each
// mark copied in.
const article = ref(null);
function brand(root) {
  const desk = onedesk().brand;
  if (!root || !desk) return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const found = [];
  while (walker.nextNode()) if (walker.currentNode.nodeValue.includes("One")) found.push(walker.currentNode);
  found.forEach((node) => desk.text(node, true));
  root.querySelectorAll("svg.one-mark").forEach((svg) => {
    const id = (svg.querySelector("use")?.getAttribute("href") || "").replace("#icon-", "");
    const mark = symbol(id);
    if (!mark) return svg.remove();
    svg.setAttribute("viewBox", mark.viewBox);
    svg.innerHTML = mark.html;
  });
}
load();
watch(() => [props.query.document, props.query.version], () => load());

const open = (key, asked) => goTo("legal", asked ? { document: key, version: asked } : { document: key });

async function agree() {
  const next = await call("onedesk.one_legal.gate.accept", { documents: [doc.value.key] });
  alert(__("Agreed to {0}", [__(doc.value.title)]));
  const legal = onedesk().legal;
  if (next.ok && legal.dialog) {
    legal.dialog.hide();
    legal.dialog = null;
  }
  jq(document).trigger("legal-agreed");
}

const agreed = () => load(true);
jq(document).on("legal-agreed", agreed);
const stop = ["Legal Acceptance", "Legal Document Version"].map((one) => followList(one, agreed));
onBeforeUnmount(() => {
  jq(document).off("legal-agreed", agreed);
  stop.forEach((one) => one());
});
</script>
