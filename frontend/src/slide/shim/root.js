// The editor draws inside the island's shadow root. Suite's code looks things up
// in the page and measures text in the page's body; here it does both inside the
// island, where the editor's own styles are (VENDORED.md, edits marked One:).
let root = null;
let shelf = null;

export const setSlideRoot = (node, measuring) => {
	root = node;
	shelf = measuring;
};

export const slideRoot = () => root || document;

export const slideBody = () => shelf || document.body;

// A listener on the window sees the island's host as the target of anything
// inside it; the element the event began at is the first in its path.
export const targetOf = (event) => event?.composedPath?.()[0] || event?.target;
