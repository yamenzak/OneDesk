<template>
  <WindowPart :win="win" part="commands" inline>
    <span class="inline-flex items-center gap-0.5">
      <Button variant="solid" icon-left="lucide-pencil" :label="__('New Email')" :disabled="!from" @click="write()" />
      <Dropdown v-if="box" :options="boxMenu">
        <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('This mailbox')" :title="__('This mailbox')" /></template>
      </Dropdown>
      <template v-if="picked.size">
        <span class="mx-1 h-5 w-px bg-surface-gray-4" />
        <template v-for="one in commands" :key="one.act">
          <Dropdown v-if="one.act === 'move'" :options="moveTo((target) => run(`move:${target}`, these))">
            <template #trigger><Button variant="ghost" :icon="one.icon" :aria-label="one.title" :title="one.title" :disabled="one.off" /></template>
          </Dropdown>
          <Button v-else variant="ghost" :icon="one.icon" :aria-label="one.title" :title="one.title" :disabled="one.off" @click="command(one.act)" />
        </template>
      </template>
    </span>
  </WindowPart>
  <WindowPart :win="win" part="views" inline>
    <span v-if="!picked.size && thread" class="inline-flex items-center gap-0.5">
      <template v-for="one in commands" :key="one.act">
        <Dropdown v-if="one.act === 'move'" :options="moveTo((target) => run(`move:${target}`, these))">
          <template #trigger><Button variant="ghost" :icon="one.icon" :aria-label="one.title" :title="one.title" :disabled="one.off" /></template>
        </Dropdown>
        <Button v-else variant="ghost" :icon="one.icon" :aria-label="one.title" :title="one.title" :disabled="one.off" @click="command(one.act)" />
      </template>
    </span>
  </WindowPart>

  <div ref="root" class="flex h-full min-h-0 text-ink-gray-8 outline-none" tabindex="-1" @keydown="key">
    <div class="w-96 shrink-0 border-e border-outline-gray-1 max-md:w-full" :class="{ 'max-md:hidden': thread }">
      <Loading v-if="loading && !items.length" />
      <ContextMenu v-else :options="menu" class="h-full">
        <template #trigger>
          <MailList
            :title="heading"
            :items="items"
            :picked="picked"
            :open="thread"
            :more="more"
            :searching="!!search"
            @open="open"
            @toggle="toggle"
            @all="(on) => (on ? items.forEach((one) => picked.add(one.thread)) : picked.clear())"
            @star="(item) => run(item.flagged ? 'unstar' : 'star', [item.thread])"
            @more="list({ more: true, keep: true })"
            @menu="menuFor"
          />
        </template>
      </ContextMenu>
    </div>
    <div class="min-w-0 flex-1" :class="{ 'max-md:hidden': !thread }">
      <div v-if="!boxes.length && !loading" class="flex h-full flex-col items-center justify-center gap-2 text-ink-gray-5">
        <span class="lucide-mail size-6" aria-hidden="true" />
        <span class="text-base">{{ __("No mailboxes") }}</span>
      </div>
      <MailConversation v-else ref="conversation" :messages="picked.size > 1 ? [] : messages" :box="box" :folder="folder" :selected="picked.size" @write="write" />
    </div>
  </div>
</template>

<script setup>
// OneMail (one_mail/api.py): the reader's mailboxes and their folders in the
// window's nav pane, the conversations of the one chosen in the view, and the
// one open beside them. Keys as Gmail has them: j and k, e to archive, # to
// delete, r, a and f to answer, s to star, u for unread, c to write, / to
// search.
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Button, ContextMenu, Dropdown } from "frappe-ui";

import {
  Loading,
  WindowPart,
  __,
  alert,
  ask,
  call,
  compose,
  dialog,
  goTo,
  goToUrl,
  hasRole,
  listen,
  setQuery,
  toast,
  userSettings,
  windowHandles,
  windowSearch,
  windowHeadAction,
  windowTree,
} from "../kit";
import { ACT, API, called, depth, folderLabel, forward, kindOf, names, noSender, reply, sender } from "./mail";
import MailConversation from "./MailConversation.vue";
import MailList from "./MailList.vue";

const props = defineProps({
  route: { type: Array, default: () => [] },
  query: { type: Object, default: () => ({}) },
  win: { type: Object, default: null },
  onTitle: Function,
});

const boxes = ref([]);
const box = ref(null);
const folder = ref(null);
const thread = ref(null);
const items = ref([]);
const messages = ref([]);
const more = ref(0);
const search = ref("");
const picked = reactive(new Set());
const folds = ref({});
const loading = ref(true);
const root = ref(null);
let anchor = null;

const from = computed(() => sender(boxes.value, box.value));
const conversation = ref(null);
const menu = ref([]);

// What the command row acts on: the ticked conversations, or the open one.
const these = computed(() => (picked.size ? [...picked] : thread.value ? [thread.value] : []));
const theseItems = computed(() => items.value.filter((one) => these.value.includes(one.thread)));

const heading = computed(() => {
  if (search.value) return __("Results for {0}", [search.value]);
  if (!folder.value) return "";
  return boxes.value.length > 1 && box.value ? `${folderLabel(folder.value)} · ${called(box.value)}` : folderLabel(folder.value);
});

// Each command an icon, the read and star ones saying what a click would do:
// beside New for the ticked conversations, as OneCloud's are, and at the
// row's other end for the one open when nothing is ticked.
const commands = computed(() => {
  const none = !these.value.length;
  const unread = theseItems.value.some((one) => one.unread);
  const starred = theseItems.value.length > 0 && theseItems.value.every((one) => one.flagged);
  const out = [
    unread
      ? { act: "read", icon: "lucide-mail-open", title: __("Mark as read"), off: none }
      : { act: "unread", icon: "lucide-mail", title: __("Mark as unread"), off: none },
    starred ? { act: "unstar", icon: "lucide-star-off", title: __("Unstar"), off: none } : { act: "star", icon: "lucide-star", title: __("Star"), off: none },
    { act: "move", icon: "lucide-folder-input", title: __("Move to"), off: none },
    { act: "archive", icon: "lucide-archive", title: __("Archive"), off: none },
    { act: "delete", icon: "lucide-trash-2", title: __("Delete"), off: none },
    { act: "link", icon: "lucide-link", title: __("Link to Record"), off: !thread.value || picked.size > 1 },
  ];
  if (picked.size) out.push({ act: "clear", icon: "lucide-x", title: __("Clear selection"), off: false });
  return out;
});

function command(what) {
  if (what === "link") return conversation.value?.fileOn();
  if (what === "clear") return picked.clear();
  run(what, these.value);
}

// A right-click acts on the ticked conversations when it lands on one of
// them, and on the one under it otherwise.
function menuFor(name) {
  const targets = picked.has(name) ? [...picked] : [name];
  const rows = items.value.filter((one) => targets.includes(one.thread));
  const unread = rows.some((one) => one.unread);
  const starred = rows.length > 0 && rows.every((one) => one.flagged);
  const option = (label, icon, onClick, theme) => ({ label, icon, onClick, theme });
  menu.value = [
    targets.length === 1 ? { group: "", hideLabel: true, options: [option(__("Open"), "lucide-mail-open", () => open(name))] } : null,
    {
      group: "",
      hideLabel: true,
      options: [
        unread ? option(__("Mark as read"), "lucide-mail-open", () => run("read", targets)) : option(__("Mark as unread"), "lucide-mail", () => run("unread", targets)),
        starred ? option(__("Unstar"), "lucide-star-off", () => run("unstar", targets)) : option(__("Star"), "lucide-star", () => run("star", targets)),
        option(__("Archive"), "lucide-archive", () => run("archive", targets)),
      ],
    },
    { group: "", hideLabel: true, options: [option(__("Delete"), "lucide-trash-2", () => run("delete", targets), "red")] },
  ].filter(Boolean);
}

const searchBox = windowSearch(props.win, {
  placeholder: __("Search"),
  title: __("Supports from:, to:, subject:, has:attachment, is:unread and is:starred"),
  onInput: (value) => {
    search.value = value;
    list();
  },
  onKey: (event) => event.key === "Escape" && root.value?.focus(),
});
windowHandles(props.win, { refresh: () => refresh() });
props.onTitle?.(__("OneMail"));

userSettings.get("OneMail").then((said) => (folds.value = (said && said.folds) || {}));

// The mailboxes the reader may read, each with its folders, folded as the
// reader left them: the window's tree (window/nav_tree.js) in the nav pane.
const BOX = "box:";
const FOLDER = "folder:";

function folded(one) {
  if (one.name in folds.value) return folds.value[one.name];
  return !(box.value && box.value.name === one.name);
}

const treeRows = computed(() => {
  const out = [];
  for (const one of boxes.value) {
    const shut = folded(one);
    out.push({
      id: BOX + one.name,
      label: called(one),
      note: called(one) !== one.email ? one.email : "",
      title: one.email,
      icon: one.workspace ? "building-2" : one.shared ? "users" : "at-sign",
      depth: 0,
      open: !shut,
      warn: one.error || "",
      count: shut && one.unread ? one.unread : "",
    });
    if (shut) continue;
    for (const each of one.folders || []) {
      const here = !search.value && box.value?.name === one.name && folder.value?.name === each.name;
      out.push({
        id: FOLDER + JSON.stringify([one.name, each.name]),
        label: folderLabel(each),
        icon: kindOf(each)[0],
        depth: 1 + depth(each),
        active: here,
        strong: Boolean(each.unread),
        count: each.unread && each.kind !== "Sent" && each.kind !== "Trash" ? each.unread : "",
        href: `/desk/onemail?box=${encodeURIComponent(one.name)}&folder=${encodeURIComponent(each.name)}`,
      });
    }
  }
  return out;
});

windowHeadAction(props.win, { icon: "plus", title: __("Connect Mailbox"), onClick: () => connect() });

const tree = windowTree(props.win, {
  label: __("Mailboxes"),
  twist: (id) => fold(id.slice(BOX.length)),
  pick: (id) => {
    if (id.startsWith(BOX)) return fold(id.slice(BOX.length));
    choose(...JSON.parse(id.slice(FOLDER.length)));
  },
});
if (tree) watch(treeRows, (rows) => tree.set(rows), { immediate: true });

function fold(name) {
  const one = boxes.value.find((row) => row.name === name);
  if (!one) return;
  const now = name in folds.value ? folds.value[name] : !(box.value && box.value.name === name);
  folds.value = { ...folds.value, [name]: !now };
  userSettings.save("OneMail", "folds", { [name]: !now });
}

async function load() {
  loading.value = true;
  boxes.value = (await call(API + "mailboxes")) || [];
  const want = props.query;
  box.value = boxes.value.find((one) => one.name === want.box) || boxes.value[0] || null;
  const folders = box.value?.folders || [];
  folder.value = folders.find((one) => one.name === want.folder) || folders.find((one) => one.kind === "Inbox") || folders[0] || null;
  loading.value = false;
  if (want.connect) connect();
  if (!box.value) return;
  await list();
  if (want.thread) open(want.thread, { quiet: true });
  else close();
}

async function refresh() {
  const was = thread.value;
  boxes.value = (await call(API + "mailboxes")) || [];
  if (box.value) box.value = boxes.value.find((one) => one.name === box.value.name) || boxes.value[0] || null;
  if (box.value && folder.value) folder.value = box.value.folders.find((one) => one.name === folder.value.name) || box.value.folders[0] || null;
  if (!box.value) return;
  await list({ keep: true });
  if (was) open(was, { quiet: true, keep: true });
}

// A folder is a place in the address, so Back returns to the one before.
function choose(boxName, folderName) {
  goToUrl(`/desk/onemail?box=${encodeURIComponent(boxName)}&folder=${encodeURIComponent(folderName)}`);
}

let asked = 0;
async function list({ keep = false, more: further = false } = {}) {
  if (!box.value) return;
  const mine = ++asked;
  const answer = await call(API + "conversations", {
    account: box.value.name,
    folder: folder.value ? folder.value.name : null,
    search: search.value || null,
    start: further ? items.value.length : 0,
  });
  if (mine !== asked) return;
  items.value = further ? items.value.concat(answer.items) : answer.items;
  more.value = answer.more;
  if (!keep) picked.clear();
  const here = new Set(items.value.map((one) => one.thread));
  for (const one of [...picked]) if (!here.has(one)) picked.delete(one);
}

function close() {
  thread.value = null;
  messages.value = [];
  setQuery("thread", null);
}

async function open(name, { quiet = false, keep = false } = {}) {
  if (!box.value) return;
  if (!keep) picked.clear();
  thread.value = name;
  setQuery("thread", name);
  const answer = await call(API + "conversation", { account: box.value.name, thread: name });
  if (thread.value !== name) return;
  if (!(answer.messages || []).length) return close();
  messages.value = answer.messages;
  const unread = messages.value.filter((one) => !one.seen).map((one) => one.name);
  if (unread.length && !quiet) {
    await call(ACT + "mark", { names: unread, seen: 1 });
    messages.value.forEach((one) => (one.seen = 1));
    const item = items.value.find((one) => one.thread === name);
    if (item) item.unread = 0;
  }
}

function toggle(name, range) {
  if (range && anchor) {
    const at = items.value.findIndex((one) => one.thread === anchor);
    const to = items.value.findIndex((one) => one.thread === name);
    const [low, high] = at < to ? [at, to] : [to, at];
    items.value.slice(low, high + 1).forEach((one) => picked.add(one.thread));
  } else if (picked.has(name)) picked.delete(name);
  else picked.add(name);
  anchor = name;
}

const moveTo = (then) =>
  (box.value?.folders || []).filter((one) => !folder.value || one.name !== folder.value.name).map((one) => ({ label: folderLabel(one), onClick: () => then(one.name) }));

const boxMenu = computed(() =>
  [
    { label: __("Attachments in OneCloud"), onClick: () => goTo("onecloud", { node: `@mail/${box.value.name}` }) },
    { label: __("Rules"), onClick: () => goTo("List", "Mail Rule", { account: box.value.name }) },
    { label: __("Out of Office"), onClick: away },
    box.value?.may_sign ? { label: __("Signature"), onClick: signature } : null,
  ].filter(Boolean)
);

async function act(method, args, threads) {
  const found = await names(box.value.name, threads);
  if (found.length) await call(ACT + method, { names: found, ...args });
}

async function moveThreads(threads, target) {
  const found = await names(box.value.name, threads, !search.value && folder.value ? folder.value.name : null);
  if (!found.length) return null;
  return ((await call(ACT + "move", { names: found, folder: target })) || {}).was;
}

async function deleteThreads(threads) {
  const found = await names(box.value.name, threads, !search.value && folder.value ? folder.value.name : null);
  if (!found.length) return null;
  if (folder.value?.kind === "Trash" && !search.value) {
    const sure = await ask(__("Permanently delete these messages? This can't be undone."));
    if (!sure) return null;
  }
  return ((await call(ACT + "delete", { names: found })) || {}).was;
}

async function run(what, threads) {
  if (!threads.length || !box.value) return;
  let was = null;
  try {
    if (what === "read" || what === "unread") await act("mark", { seen: what === "read" ? 1 : 0 }, threads);
    else if (what === "star" || what === "unstar") await act("star", { flagged: what === "star" ? 1 : 0 }, threads);
    else if (what === "archive") {
      const archive = box.value.folders.find((one) => one.kind === "Archive");
      if (!archive) return alert(__("No Archive folder in this mailbox"), "yellow");
      was = await moveThreads(threads, archive.name);
    } else if (what === "delete") was = await deleteThreads(threads);
    else if (what.startsWith("move:")) was = await moveThreads(threads, what.slice(5));
  } finally {
    const gone = ["archive", "delete"].includes(what) || what.startsWith("move:");
    if ((gone || what === "unread") && threads.includes(thread.value)) close();
    if (gone) picked.clear();
    refresh();
    if (was && was.length) {
      const said = { archive: __("Archived"), delete: __("Moved to Trash") }[what] || __("Moved");
      toast(said, { label: __("Undo"), onClick: async () => (await call(ACT + "put_back", { was }), refresh()) });
    }
  }
}

function write({ reply: answering = false, all = false, forward: passing = false } = {}) {
  if (!from.value) return noSender();
  const done = () => setTimeout(refresh, 1500);
  if (!answering && !passing) return compose({ sender: from.value, title: __("New Email") }, done);
  if (!messages.value.length) return;
  if (passing) return forward(messages.value, from.value, done);
  reply(boxes.value, messages.value, from.value, { all }, done);
}

function connect() {
  const asking = dialog({
    title: __("Connect Mailbox"),
    fields: [
      { fieldname: "email", fieldtype: "Data", options: "Email", label: __("Email Address"), reqd: 1 },
      { fieldname: "password", fieldtype: "Password", label: __("Password"), reqd: 1, description: __("Gmail and Outlook need an app password.") },
      { fieldname: "sends", fieldtype: "Check", label: __("Enable Outgoing"), default: 1 },
      {
        fieldname: "shared",
        fieldtype: "Check",
        label: __("Shared Mailbox"),
        hidden: !hasRole("Workspace Administrator"),
        description: __("A workspace address such as sales@. You choose who has access."),
      },
      { fieldtype: "Section Break", label: __("Server"), collapsible: 1 },
      { fieldname: "login", fieldtype: "Data", label: __("Login ID"), description: __("If different from the email address") },
      { fieldname: "email_server", fieldtype: "Data", label: __("IMAP Server") },
      { fieldname: "incoming_port", fieldtype: "Int", label: __("IMAP Port") },
      { fieldname: "use_ssl", fieldtype: "Check", label: __("Use SSL"), default: 1 },
      { fieldtype: "Column Break" },
      { fieldname: "smtp_server", fieldtype: "Data", label: __("SMTP Server") },
      { fieldname: "smtp_port", fieldtype: "Int", label: __("SMTP Port") },
    ],
    primary_action_label: __("Connect"),
    primary_action: async (values) => {
      asking.get_primary_btn().prop("disabled", true);
      try {
        const account = await call("onedesk.one_mail.connect.connect", values);
        asking.hide();
        alert(__("Mailbox connected"));
        goToUrl(`/desk/onemail?box=${encodeURIComponent(account)}`);
      } finally {
        asking.get_primary_btn().prop("disabled", false);
      }
    },
  });
  asking.show();
}

async function away() {
  const now = (await call("onedesk.one_mail.rules.away_of", { account: box.value.name })) || {};
  const asking = dialog({
    title: __("Out of office for {0}", [box.value.email]),
    fields: [
      {
        fieldname: "away",
        fieldtype: "Check",
        label: __("Enable Auto Reply"),
        default: now.one_away,
        description: __("Each sender gets one reply every four days. Mailing lists get none."),
      },
      { fieldname: "until", fieldtype: "Date", label: __("Until"), default: now.one_away_until, depends_on: "away" },
      { fieldname: "message", fieldtype: "Small Text", label: __("Message"), default: now.one_away_message, depends_on: "away" },
    ],
    primary_action_label: __("Save"),
    primary_action: async (values) => {
      await call("onedesk.one_mail.rules.set_away", { account: box.value.name, ...values });
      asking.hide();
      alert(values.away ? __("Auto reply on") : __("Auto reply off"));
    },
  });
  asking.show();
}

async function signature() {
  const now = await call("onedesk.one_mail.holders.signature_of", { account: box.value.name });
  const asking = dialog({
    title: __("Signature for {0}", [box.value.email]),
    fields: [
      { fieldname: "signature", fieldtype: "Text Editor", label: __("Signature"), default: now || "", description: __("Added to every email sent from this address.") },
    ],
    primary_action_label: __("Save"),
    primary_action: async (values) => {
      await call("onedesk.one_mail.holders.set_signature", { account: box.value.name, signature: values.signature });
      asking.hide();
      alert(__("Signature saved"));
    },
  });
  asking.show();
}

function key(event) {
  if (event.target.closest?.("input, textarea, [contenteditable]") || event.metaKey || event.ctrlKey || event.altKey) return;
  const at = items.value.findIndex((one) => one.thread === thread.value);
  const step = (by) => {
    const next = items.value[Math.min(items.value.length - 1, Math.max(0, at + by))];
    if (next) open(next.thread);
  };
  const flagged = messages.value.some((one) => one.one_flagged);
  const keys = {
    j: () => step(1),
    k: () => step(-1),
    ArrowDown: () => step(1),
    ArrowUp: () => step(-1),
    e: () => run("archive", these.value),
    "#": () => run("delete", these.value),
    Delete: () => run("delete", these.value),
    r: () => thread.value && write({ reply: true }),
    a: () => thread.value && write({ reply: true, all: true }),
    f: () => thread.value && write({ forward: true }),
    s: () => thread.value && run(flagged ? "unstar" : "star", [thread.value]),
    u: () => thread.value && run("unread", [thread.value]),
    c: () => write(),
    "/": () => searchBox?.focus(),
    Escape: () => picked.clear(),
  };
  const fn = keys[event.key];
  if (!fn) return;
  event.preventDefault();
  fn();
}

// Chosen in the address: a folder from the nav pane, a conversation from a
// record's Mail, or Back.
watch(
  () => [props.query.box, props.query.folder],
  ([wantBox, wantFolder], [hadBox, hadFolder] = []) => {
    if (!boxes.value.length) return;
    if (wantBox === hadBox && wantFolder === hadFolder) return;
    const found = boxes.value.find((one) => one.name === wantBox);
    if (!found) return load();
    box.value = found;
    folder.value = found.folders.find((one) => one.name === wantFolder) || found.folders.find((one) => one.kind === "Inbox") || found.folders[0];
    search.value = "";
    searchBox?.set("");
    picked.clear();
    close();
    list();
  }
);
watch(
  () => props.query.thread,
  (want) => {
    if (want && want !== thread.value) open(want, { quiet: true });
  }
);

load();
const stop = listen("onemail_change", (data) => {
  if (!data || !boxes.value.some((one) => one.name === data.account)) return;
  clearTimeout(soon);
  soon = setTimeout(refresh, 800);
});
let soon = null;
onBeforeUnmount(stop);
</script>
