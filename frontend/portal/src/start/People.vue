<template>
  <div class="flex flex-col gap-8">
    <div v-for="(one, at) in answers.people" :key="at" class="flex flex-col gap-3">
      <div class="flex items-center justify-between">
        <p class="text-base font-medium text-ink-gray-8">{{ one.first_name || one.email || __("Person {0}", [at + 1]) }}</p>
        <Button variant="ghost" icon="lucide-x" :aria-label="__('Remove')" @click="remove(at)" />
      </div>
      <FormControl v-model="one.email" type="email" size="lg" :label="__('Email')" autocomplete="off" required />
      <div class="grid grid-cols-2 gap-3">
        <FormControl v-model="one.first_name" size="lg" :label="__('First Name')" required />
        <FormControl v-model="one.last_name" size="lg" :label="__('Last Name')" />
      </div>
      <FormControl :model-value="ways[at]" type="select" size="lg" :label="__('Access')" :options="WAYS" @update:model-value="(way) => give(at, way)" />
      <div v-if="ways[at] === 'each'" class="flex flex-col gap-3">
        <FormControl
          v-for="app in apps"
          :key="app.id"
          :model-value="one.levels[app.id] || 'None'"
          type="select"
          :label="app.name"
          :options="LEVELS"
          @update:model-value="(level) => (one.levels = { ...one.levels, [app.id]: level })"
        />
      </div>
    </div>
    <div class="flex flex-col gap-2">
      <Button class="self-start" variant="subtle" icon-left="lucide-plus" :label="__('Add Person')" :disabled="full" @click="add" />
      <p v-if="held.seats" class="text-p-sm text-ink-gray-5">{{ __("The plan has room for {0} people, you among them.", [held.seats]) }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Button, FormControl } from "frappe-ui";

import { __ } from "../words";
import { answers, held, offer } from "./wizard";

const WAYS = [
  { label: __("User of Every App"), value: "user" },
  { label: __("Manager of Every App"), value: "manager" },
  { label: __("Administrator"), value: "admin" },
  { label: __("Chosen for Each App"), value: "each" },
];
const LEVELS = [
  { label: __("None"), value: "None" },
  { label: __("User"), value: "User" },
  { label: __("Manager"), value: "Manager" },
];

const apps = computed(() => offer.value.apps.filter((one) => !one.always && answers.apps[one.id]));
const full = computed(() => Boolean(held.seats) && answers.people.length >= held.seats - 1);

function way(one) {
  if (one.admin) return "admin";
  const given = new Set(Object.values(one.levels || {}));
  if (given.size === 1 && Object.keys(one.levels).length === apps.value.length) return given.has("Manager") ? "manager" : given.has("User") ? "user" : "each";
  return Object.keys(one.levels || {}).length ? "each" : "user";
}

const ways = ref(answers.people.map(way));

const every = (level) => Object.fromEntries(apps.value.map((one) => [one.id, level]));

function give(at, chosen) {
  ways.value[at] = chosen;
  const one = answers.people[at];
  one.admin = chosen === "admin";
  one.levels = chosen === "manager" ? every("Manager") : chosen === "admin" ? {} : every("User");
}

function add() {
  answers.people.push({ email: "", first_name: "", last_name: "", levels: every("User"), admin: false });
  ways.value.push("user");
}

function remove(at) {
  answers.people.splice(at, 1);
  ways.value.splice(at, 1);
}

const ready = computed(() => answers.people.every((one) => /^\S+@\S+\.\S+$/.test((one.email || "").trim()) && (one.first_name || "").trim()));

defineExpose({ ready, said: () => ({ answers: { people: answers.people } }) });
</script>
