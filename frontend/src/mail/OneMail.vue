<template>
  <div ref="root" class="flex h-full min-h-0 flex-col text-ink-gray-8 outline-none" tabindex="-1" @keydown="key">
    <div class="flex min-h-0 flex-1 gap-2.5 px-2.5 pb-2.5" :class="{ 'pt-2.5': stacked && thread }">
    <div class="flex shrink-0 flex-col overflow-hidden rounded-6 border border-outline-gray-1 bg-surface-elevation-2" :class="stacked ? (thread ? 'hidden' : 'w-full') : 'w-96'" data-tour="onemail-list">
      <Loading v-if="loading && !items.length" />
      <ContextMenu v-else :options="menu" class="min-h-0 flex-1">
        <template #trigger>
          <MailList
            :items="items"
            :picked="picked"
            :open="thread"
            :more="more"
            :searching="!!search"
            :wide="stacked && !narrow"
            @open="open"
            @toggle="toggle"
            @all="(on) => (on ? items.forEach((one) => picked.add(one.thread)) : picked.clear())"
            @star="(item) => run(item.flagged ? 'unstar' : 'star', [item.thread])"
            @more="list({ more: true, keep: true })"
            @menu="menuFor"
          >
            <template #action>
              <template v-if="picked.size">
                <template v-for="one in commands" :key="one.act">
                  <Dropdown v-if="one.act === 'move'" :options="moveTo((target) => run(`move:${target}`, these))">
                    <template #trigger><Button size="sm" variant="ghost" :icon="one.icon" :aria-label="one.title" :title="one.title" :disabled="one.off" /></template>
                  </Dropdown>
                  <Button v-else size="sm" variant="ghost" :icon="one.icon" :aria-label="one.title" :title="one.title" :disabled="one.off" @click="command(one.act)" />
                </template>
              </template>
            </template>
          </MailList>
        </template>
      </ContextMenu>
    </div>
    <div class="min-w-0 flex-1" :class="{ hidden: stacked && !thread }" data-tour="onemail-reading">
      <div v-if="!boxes.length && !loading" class="flex h-full flex-col items-center justify-center gap-2 text-ink-gray-5">
        <span class="lucide-mail size-6" aria-hidden="true" />
        <span class="text-base">{{ __("No mailboxes") }}</span>
      </div>
      <MailConversation
        v-else
        ref="conversation"
        :messages="picked.size > 1 ? [] : messages"
        :box="box"
        :folder="folder"
        :selected="picked.size"
        :draft="draft"
        :thread="thread"
        :replying="replyingHere"
        :back="stacked"
        @back="close"
        @changed="refresh"
        @write="write"
        @draft="openDraft"
        @discard="discardDraft"
      >
        <template #commands>
          <template v-for="one in commands.filter((c) => !['link', 'clear'].includes(c.act))" :key="one.act">
            <Dropdown v-if="one.act === 'move'" :options="moveTo((target) => run(`move:${target}`, these))">
              <template #trigger><Button size="sm" variant="ghost" :icon="one.icon" :aria-label="one.title" :title="one.title" /></template>
            </Dropdown>
            <Button v-else size="sm" variant="ghost" :icon="one.icon" :aria-label="one.title" :title="one.title" @click="command(one.act)" />
          </template>
        </template>
      </MailConversation>
    </div>
    </div>
  </div>
</template>

<script setup>
// OneMail (one_mail/api.py): the reader's mailboxes and their folders in the
// window's nav pane, the conversations of the one chosen in the view, and the
// one open beside them. Its keys are its shortcuts (one_mail/shortcuts.py).
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Button, ContextMenu, Dropdown } from "frappe-ui";

import {
  Loading,
  __,
  alert,
  ask,
  call,
  compose,
  date,
  escape,
  goTo,
  goToUrl,
  listen,
  onedesk,
  prompt,
  setQuery,
  historyBack,
  pushedHere,
  shortcut,
  toast,
  userSettings,
  interfaceHandles,
  interfaceSearch,
  interfaceStatus,
  interfaceHeading,
  requires,
  interfaceModuleFoot,
  interfaceHeadAction,
  interfaceTree,
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
const draft = ref(null);
const team = ref(null);
const PANES = [
  { value: "list", icon: "lucide-rows-3", label: __("Hide Reading Pane") },
  { value: "pane", icon: "lucide-columns-2", label: __("Show Reading Pane") },
];
const TEAMS = [
  { label: __("Open"), value: "open" },
  { label: __("Mine"), value: "mine" },
  { label: __("Unassigned"), value: "unassigned" },
  { label: __("Done"), value: "done" },
];
watch(team, () => list());
const writers = ref({});
const replyingHere = computed(() => Object.values(writers.value[thread.value] || {}));
const more = ref(0);
const total = ref(0);
const search = ref("");
const picked = reactive(new Set());
const folds = ref({});
const loading = ref(true);
const root = ref(null);
const narrow = ref(false);
const sized = new ResizeObserver(([one]) => (narrow.value = one.contentRect.width < 900));
const pane = ref(false);
const stacked = computed(() => narrow.value || !pane.value);
function togglePane() {
  pane.value = !pane.value;
  userSettings.save("OneMail", "pane", pane.value);
}
watch(root, (now, was) => {
  if (was) sized.unobserve(was);
  if (now) sized.observe(now);
});
onBeforeUnmount(() => sized.disconnect());
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
  return folderLabel(folder.value);
});

// Each command an icon, the read and star ones saying what a click would do:
// beside New for the ticked conversations, as OneCloud's are, and at the
// row's other end for the one open when nothing is ticked.
const commands = computed(() => {
  const none = !these.value.length;
  const unread = theseItems.value.some((one) => one.unread);
  const starred = theseItems.value.length > 0 && theseItems.value.every((one) => one.flagged);
  const out = [
    { act: "archive", icon: "lucide-archive", title: __("Archive"), off: none },
    { act: "delete", icon: "lucide-trash-2", title: __("Delete"), off: none },
    unread
      ? { act: "read", icon: "lucide-mail-open", title: __("Mark as read"), off: none }
      : { act: "unread", icon: "lucide-mail", title: __("Mark as unread"), off: none },
    starred ? { act: "unstar", icon: "lucide-star-off", title: __("Unstar"), off: none } : { act: "star", icon: "lucide-star", title: __("Star"), off: none },
    { act: "move", icon: "lucide-folder-input", title: __("Move to"), off: none },
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

const searchBox = interfaceSearch(props.win, {
  placeholder: __("Search"),
  hint: __("Supports from:, to:, subject:, has:attachment, is:unread and is:starred"),
  onInput: (value) => {
    search.value = value;
    list();
  },
  onKey: (event) => event.key === "Escape" && root.value?.focus(),
});
interfaceHandles(props.win, { refresh: () => refresh() });
props.onTitle?.(__("OneMail"));

userSettings.get("OneMail").then((said) => {
  folds.value = (said && said.folds) || {};
  pane.value = !!(said && said.pane);
});

// The mailboxes the reader may read, each with its folders, folded as the
// reader left them: the window's tree (window/nav_tree.js) in the nav pane.
const BOX = "box:";
const FOLDER = "folder:";

function folded(one) {
  if (one.name in folds.value) return folds.value[one.name];
  return !(box.value && box.value.name === one.name);
}

// A person's own mailbox says when it is answering for them, one the
// reader covers for a colleague on leave says until when, and one a rule
// replies from says so.
function awayNote(one) {
  if (one.covering_until) return __("Covering until {0}", [date(one.covering_until)]);
  if (!one.away) return one.replies ? __("Auto Reply On") : "";
  if (one.away.leave) return __("On Leave until {0}", [date(one.away.until)]);
  return one.away.until ? __("Out of Office until {0}", [date(one.away.until)]) : __("Out of Office");
}

const treeRows = computed(() => {
  const out = [];
  for (const one of boxes.value) {
    const shut = folded(one);
    out.push({
      id: BOX + one.name,
      label: called(one),
      note: awayNote(one) || (called(one) !== one.email ? one.email : ""),
      title: one.email,
      icon: one.workspace ? "building-2" : one.shared ? "users" : "at-sign",
      depth: 0,
      open: !shut,
      warn: one.error || "",
      count: shut && one.unread ? one.unread : "",
      actions: true,
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
        actions: each.kind === "Other",
      });
    }
  }
  return out;
});

interfaceHeadAction(props.win, { icon: "plus", title: __("Connect Mailbox"), onClick: () => settings("connect") });

// OneMail's settings: frappe's settings dialog, public/js/one_mail/onemail_settings.js.
const SETTINGS = ["/assets/onedesk/js/one_mail/onemail_settings.js", "/assets/onedesk/css/one_mail/onemail_settings.css"];
async function settings(tab) {
  await requires(SETTINGS);
  onedesk().mail.settings(tab);
}
interfaceModuleFoot(props.win, { module: "OneMail", onSettings: () => settings() });

const tree = interfaceTree(props.win, {
  label: __("Mailboxes"),
  twist: (id) => fold(id.slice(BOX.length)),
  pick: (id) => {
    if (id.startsWith(BOX)) return fold(id.slice(BOX.length));
    choose(...JSON.parse(id.slice(FOLDER.length)));
  },
  menu: folderMenu,
});

// A mailbox's … in the nav pane makes a folder in it; a folder the user
// made can also hold one, be renamed or be deleted. Inbox, Sent and the
// other standard folders have none. The server does the same on the mail
// server (actions.py).
function folderMenu(id) {
  if (id.startsWith(BOX)) return boxMenu(boxes.value.find((one) => one.name === id.slice(BOX.length)));
  const [boxName, folderName] = JSON.parse(id.slice(FOLDER.length));
  const each = boxes.value.find((one) => one.name === boxName)?.folders.find((one) => one.name === folderName);
  if (!each) return [];
  const items = [{ label: __("New Folder"), icon: "folder-plus", onClick: () => newFolder(boxName, folderName) }];
  if (each.kind !== "Other") return items;
  return [
    ...items,
    { label: __("Rename"), icon: "pencil", onClick: () => renameFolder(each) },
    { label: __("Delete"), icon: "trash-2", theme: "red", onClick: () => deleteFolder(boxName, each) },
  ];
}

// A mailbox's own menu. Each part opens its view in OneMail's settings,
// for whoever's role or share lets them change it (holders.may). Out of
// Office shows on every mailbox of a person's own, where approved leave
// answers on its own; a shared one answers by a mail rule.
function boxMenu(one) {
  if (!one) return [];
  const at = (section) => () => settings(`mailbox:${one.name}${section ? ":" + section : ""}`);
  return [
    { label: __("New Folder"), icon: "folder-plus", onClick: () => newFolder(one.name) },
    one.may_sign ? { label: __("Signature"), icon: "signature", onClick: at("signature") } : null,
    !one.shared && !one.covering_until ? { label: __("Out of Office"), icon: "plane", onClick: at("away") } : null,
    one.may?.ai ? { label: __("OneAI"), icon: "oneai", onClick: at("oneai") } : null,
    { label: __("Automation"), icon: "workflow", onClick: at("rules") },
    { label: __("Attachments in OneCloud"), icon: "paperclip", onClick: () => goTo("onecloud", { node: `@mail/${one.name}` }) },
    { label: __("Mailbox Settings"), icon: "settings", onClick: at("") },
  ].filter(Boolean);
}

const askFolderName = (title, label, value, done) =>
  prompt([{ fieldname: "label", fieldtype: "Data", label: __("Folder Name"), reqd: 1, default: value }], ({ label: typed }) => done(typed.trim()), title, label);

function newFolder(account, parent = null) {
  askFolderName(__("New Folder"), __("Create"), "", async (label) => {
    await call(ACT + "create_folder", { account, label, parent });
    refresh();
  });
}

function renameFolder(each) {
  askFolderName(__("Rename Folder"), __("Rename"), folderLabel(each), async (label) => {
    await call(ACT + "rename_folder", { folder: each.name, label });
    refresh();
  });
}

async function deleteFolder(account, each) {
  if (!(await ask(__("Delete {0}? Its messages move to Trash.", [escape(folderLabel(each))])))) return;
  await call(ACT + "delete_folder", { folder: each.name });
  if (folder.value?.name === each.name) return choose(account, box.value.folders.find((one) => one.kind === "Inbox")?.name);
  refresh();
}
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
  team.value = box.value?.shared ? "open" : null;
  const folders = box.value?.folders || [];
  folder.value = folders.find((one) => one.name === want.folder) || folders.find((one) => one.kind === "Inbox") || folders[0] || null;
  loading.value = false;
  if (want.connect) settings("connect");
  if (want.settings) settings(want.settings);
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
let fetching = false;
async function list({ keep = false, more: further = false } = {}) {
  if (!box.value) return;
  if (further && (fetching || !more.value)) return;
  const mine = ++asked;
  fetching = further;
  let answer;
  try {
    answer = await call(API + "conversations", {
      account: box.value.name,
      folder: folder.value ? folder.value.name : null,
      search: search.value || null,
      team: box.value.shared && !search.value ? team.value : null,
      start: further ? items.value.filter((one) => !one.draft).length : 0,
    });
  } finally {
    if (further) fetching = false;
  }
  if (mine !== asked) return;
  items.value = further ? items.value.concat(answer.items) : answer.items;
  more.value = answer.more;
  if (answer.total != null) total.value = answer.total;
  interfaceStatus(props.win, __("{0} of {1}", [items.value.length, Math.max(total.value, items.value.length)]));
  if (!keep) picked.clear();
  const here = new Set(items.value.map((one) => one.thread));
  for (const one of [...picked]) if (!here.has(one)) picked.delete(one);
}

function close() {
  if (pushedHere()) return historyBack();
  thread.value = null;
  messages.value = [];
  draft.value = null;
  setQuery("thread", null);
}

async function open(name, { quiet = false, keep = false } = {}) {
  if (!box.value) return;
  const item = items.value.find((one) => one.thread === name);
  if (item?.draft) return openDraft(item.draft);
  if (!keep) picked.clear();
  const first = !thread.value && !quiet;
  thread.value = name;
  setQuery("thread", name, { push: first });
  const answer = await call(API + "conversation", { account: box.value.name, thread: name });
  if (thread.value !== name) return;
  if (!(answer.messages || []).length) return close();
  messages.value = answer.messages;
  draft.value = answer.draft || null;
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

async function openDraft(name) {
  const composer = await onedesk().mail.open_draft(name);
  composer.dialog.$wrapper.on("hidden.bs.modal", () => setTimeout(refresh, 1500));
}

async function discardDraft(name) {
  await call("onedesk.one_mail.drafts.discard", { name });
  draft.value = null;
  toast(__("Draft discarded."));
  refresh();
}

function write({ reply: answering = false, all = false, forward: passing = false } = {}) {
  if (!from.value) return noSender();
  const done = () => setTimeout(refresh, 1500);
  if (!answering && !passing) return compose({ sender: from.value, title: __("New Email") }, done);
  if (!messages.value.length) return;
  if (passing) return forward(messages.value, from.value, done);
  const here = { account: box.value.name, thread: thread.value };
  call("onedesk.one_mail.team.replying", { ...here, on: 1 });
  const composer = reply(boxes.value, messages.value, from.value, { all }, done);
  composer.dialog.$wrapper.on("hidden.bs.modal", () => call("onedesk.one_mail.team.replying", { ...here, on: 0 }));
}

// The mailbox's keys are OneMail's shortcuts (one_mail/shortcuts.py), as
// Gmail has them; the reader can move them in ShortcutCenter. Each does
// what it says while this screen is open. Escape clears the selection, as it
// does in any list.
function step(by) {
  const at = items.value.findIndex((one) => one.thread === thread.value);
  const next = items.value[Math.min(items.value.length - 1, Math.max(0, at + by))];
  if (next) open(next.thread);
}
const KEYS = {
  next: () => step(1),
  previous: () => step(-1),
  archive: () => run("archive", these.value),
  delete: () => run("delete", these.value),
  reply: () => thread.value && write({ reply: true }),
  reply_all: () => thread.value && write({ reply: true, all: true }),
  forward: () => thread.value && write({ forward: true }),
  star: () => thread.value && run(messages.value.some((one) => one.one_flagged) ? "unstar" : "star", [thread.value]),
  unread: () => thread.value && run("unread", [thread.value]),
  compose: () => write(),
  search: () => searchBox?.focus(),
  done: () => thread.value && conversation.value?.team()?.toggleDone(),
  snooze: () => thread.value && conversation.value?.team()?.snoozeNow(),
  assign: () => thread.value && conversation.value?.team()?.assignNow(),
};
const forget = Object.entries(KEYS).map(([key, fn]) => shortcut(`one_mail.${key}`, fn));
onBeforeUnmount(() => forget.forEach((one) => one()));

function key(event) {
  if (event.key === "Escape" && !event.target.closest?.("input, textarea, [contenteditable]")) picked.clear();
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
    team.value = found.shared ? "open" : null;
    folder.value = found.folders.find((one) => one.name === wantFolder) || found.folders.find((one) => one.kind === "Inbox") || found.folders[0];
    search.value = "";
    searchBox?.set("");
    picked.clear();
    close();
    list();
  }
);
watch(
  () => props.query,
  (query) => {
    const want = query.thread;
    if (want && want !== thread.value) open(want, { quiet: true });
    // Back in the browser to the list, as on a phone, closes it.
    if (!want && thread.value) {
      thread.value = null;
      messages.value = [];
    }
  }
);

watch(
  () => [stacked.value && thread.value, heading.value, folder.value, search.value, from.value, box.value, team.value, pane.value, narrow.value, boxes.value.length],
  () => {
    if (stacked.value && thread.value) return interfaceHeading(props.win, null);
    interfaceHeading(props.win, {
      title: heading.value,
      icon: folder.value && !search.value ? kindOf(folder.value)[0] : "lucide-search",
      quiet: boxes.value.length > 1 && box.value && !search.value ? called(box.value) : "",
      primary: from.value ? { label: __("New Email"), click: () => write() } : null,
      ways: narrow.value ? [] : PANES,
      ways_label: __("Reading Pane"),
      way: pane.value ? "pane" : "list",
      pick_way: (value) => (value === "pane") !== pane.value && togglePane(),
      states: box.value?.shared && !search.value && folder.value?.kind !== "Drafts" ? TEAMS : [],
      state: team.value,
      pick_state: (value) => (team.value = value),
    });
  },
  { flush: "post" }
);
onBeforeUnmount(() => interfaceHeading(props.win, null));

load();
const stop = listen("onemail_change", (data) => {
  if (!data || !boxes.value.some((one) => one.name === data.account)) return;
  clearTimeout(soon);
  soon = setTimeout(refresh, 800);
});
let soon = null;
onBeforeUnmount(stop);
const stopWriters = listen("onemail_replying", (data) => {
  if (!data || !boxes.value.some((one) => one.name === data.account)) return;
  const now = { ...(writers.value[data.thread] || {}) };
  if (data.on) now[data.user] = data.name;
  else delete now[data.user];
  writers.value = { ...writers.value, [data.thread]: now };
});
onBeforeUnmount(stopWriters);
</script>
