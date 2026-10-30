// Save to Library on a slide's menu (utils/slideMenu.js, a One: edit): the
// slide, as saved, kept on the company's shelf under the kind chosen
// (one_slide/library.py).
import { alert, call, prompt } from "../../kit/desk";
import { presentationDoc } from "../stores/presentation";
import { saveWithoutDelay } from "../stores/saving";
import { __ } from "./words.js";

export async function saveToLibrary(slide) {
	if (!slide) return;
	const said = await call("onedesk.one_slide.library.shelves");
	prompt(
		[{ fieldname: "kind", fieldtype: "Select", label: __("Kind"), reqd: 1, options: Object.entries(said.kinds).map(([value, label]) => ({ value, label })) }],
		async ({ kind }) => {
			await saveWithoutDelay();
			await call("onedesk.one_slide.library.keep", { name: presentationDoc.value.name, client_id: slide.clientId, kind });
			alert(__("The slide is in the library."));
		},
		__("Save to Library"),
		__("Save")
	);
}
