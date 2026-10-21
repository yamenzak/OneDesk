// The writer's calls to Suite's server, made to One's (one_doc/).
import { reactive } from "vue";

import { call } from "../../kit/desk";

export const getTemplates = reactive({
	data: null,
	fetch() {
		return call("onedesk.one_doc.templates.listed", { html: 1 }).then((found) => (getTemplates.data = (found || []).map((one) => ({ ...one, content: one.html || "" }))));
	},
});

export const updateComments = {
	submit: ({ doc, data }) => call("onedesk.one_doc.api.save_comments", { name: doc, data }),
};

export const search = { submit: () => Promise.resolve([]), data: [] };
export const createDocument = { submit: () => Promise.resolve(null) };
export const getDocuments = { updateRow() {} };
export const apps = { data: [] };
