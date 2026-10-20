// Suite's second co-editing path runs its own server; One co-edits over the
// desk's socket instead (useCollaboration.js), so this path is never taken.
export class HocuspocusProvider {
	constructor() {
		throw new Error("OneWorkbook co-edits over the desk's own socket.");
	}
}
