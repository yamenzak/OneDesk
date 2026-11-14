<template>
  <template v-for="(part, i) in parts" :key="i">
    <span v-if="part.one" class="one-name one-solo inline-flex items-baseline gap-1 whitespace-nowrap"><svg v-if="mark" class="one-mark inline-block size-[1.05em] shrink-0 self-center" :viewBox="mark.viewBox" aria-hidden="true" v-html="mark.html" /><span class="font-light">{{ NAME }}</span></span>
    <span v-else-if="part.center" class="one-name one-solo inline-flex items-baseline gap-1 whitespace-nowrap"><svg v-if="part.mark" class="one-mark inline-block size-[1.05em] shrink-0 self-center" :viewBox="part.mark.viewBox" aria-hidden="true" v-html="part.mark.html" /><span><span class="font-light">{{ part.center }}</span>{{ CENTER }}</span></span>
    <span v-else-if="part.named" class="one-name inline-flex items-baseline gap-1 whitespace-nowrap"><svg v-if="part.mark" class="one-mark inline-block size-[1.05em] shrink-0 self-center" :viewBox="part.mark.viewBox" aria-hidden="true" v-html="part.mark.html" /><span><span class="font-light">{{ NAME }}</span>{{ part.named }}</span></span>
    <template v-else>{{ part }}</template>
  </template>
</template>

<script setup>
import { computed } from "vue";
import { name, onedesk, symbol } from "./desk";

// `marked` draws the mark on a name standing alone too, as a heading over
// what belongs to that app does.
const props = defineProps({ text: { type: [String, Number], default: "" }, marked: Boolean });
const NAME = name("one");
const CENTER = "Center";
const mark = symbol("one");
// The desk draws a product's name, "OneCloud", with One light and, in a
// sentence, its mark before it, and a lone "One" with One's mark
// (public/js/brand.js); an island, which the desk's observer leaves alone,
// draws both here the same way, and a centre's name, "HelpCenter", as the
// desk does (brand.CENTER).
const parts = computed(() => {
  const text = props.text === null || props.text === undefined ? "" : String(props.text);
  const brand = onedesk()?.brand;
  if (!brand?.parts) return [text];
  const out = [];
  let at = 0;
  const names = brand.CENTER ? `${brand.NAME.source}|${brand.CENTER.source}` : brand.NAME.source;
  for (const found of text.matchAll(new RegExp(names, "g"))) {
    if (found.index > at) out.push(...brand.parts(text.slice(at, found.index)));
    if (found[2]) out.push({ center: found[2], mark: symbol(brand.center_mark?.(found[2]) || "one") });
    else {
      const id = (props.marked || text.trim() !== found[0]) && brand.mark_of?.(found[1]);
      out.push({ named: found[1], mark: id ? symbol(id) : null });
    }
    at = found.index + found[0].length;
  }
  if (at < text.length) out.push(...brand.parts(text.slice(at)));
  return out;
});
</script>
