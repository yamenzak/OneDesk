// The document's page draws inside the island's shadow root, where
// document.querySelector finds nothing of it. The page says where it is.
let root = null;

export const setWriterRoot = (node) => (root = node);

export const writerRoot = () => root || document;
