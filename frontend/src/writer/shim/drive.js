// What the writer took from Suite's Drive, answered by OneCloud: renaming the
// document's File, who may be mentioned, and the clipboard.
import { reactive } from "vue";

import { call } from "../../kit/desk";

export const rename = reactive({
	params: {},
	loading: false,
	submit(params, { onSuccess } = {}) {
		rename.params = params;
		return call("onedesk.one_doc.api.rename_document", { name: params.entity_name, title: params.new_title }).then((said) => {
			rename.params = { ...params, new_title: said.title };
			onSuccess?.(said);
			return said;
		});
	},
});

export const allUsers = reactive({
	data: null,
	fetch() {
		return call("onedesk.one_doc.api.people").then((found) => {
			allUsers.data = (found || []).map((one) => ({ ...one, name: one.email, value: one.email, label: (one.full_name || "").trimEnd() }));
			return allUsers.data;
		});
	},
});
allUsers.fetch();

export const rootInfo = reactive({ data: null, fetch() {} });

export const prettyData = (entities) => entities;

export const copyToClipboard = (text) => navigator.clipboard.writeText(text);
