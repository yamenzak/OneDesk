import { reactive, watch } from "vue";

import { onedesk } from "../kit";

/** A view's place on the project page (one_studio/places.py): its
 * extensions are told what the view shows, `data()`, each time that changes,
 * and what they add is kept here for PlaceSpot to draw inside the page. */
export function usePlace(key, data) {
  const said = reactive({ notes: [], actions: [] });
  let drawn = null;
  watch(
    data,
    (now) => {
      const places = onedesk().places;
      if (!now || !places?.listening(key)) return;
      const json = JSON.stringify(now);
      if (json === drawn) return;
      drawn = json;
      said.notes = [];
      said.actions = [];
      places.emit(key, now, {
        note: (text, tone) => said.notes.push({ text: String(text || ""), tone }),
        action: (label, handler) => said.actions.push({ label: String(label || ""), handler }),
      });
    },
    { deep: true, immediate: true }
  );
  return said;
}
