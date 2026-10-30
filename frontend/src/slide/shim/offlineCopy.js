// Suite pins a presentation for offline use through its service worker, which
// the desk does not register. Nothing is pinned.
import { ref } from "vue";

export const offlineCopyProgress = ref({ running: false, done: 0, total: 0, failed: [] });
export const offlineCopyStatus = ref(null);
export const saveOfflineCopy = () => Promise.resolve(null);
export const pruneOfflineCopy = () => Promise.resolve();
export const cancelOfflineCopy = () => {};
export const removeOfflineCopy = () => Promise.resolve();
export const refreshOfflineStatus = () => {};
export const warmOfflineCopyAssets = () => {};
