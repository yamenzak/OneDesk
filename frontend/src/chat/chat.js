// OneChat's calls and the small things its parts share (one_chat/api.py).
import { escape, markdown } from "../kit";

const API = "onedesk.one_chat.api";

export const method = (name) => `${API}.${name}`;

// An agent's face, drawn on the server from its id (one_chat/agents.py, face).
export const face = (agent) => (agent && agent.face ? `data:image/svg+xml;utf8,${encodeURIComponent(agent.face)}` : "");

// What a message says, as HTML: escaped first, so only Markdown's own marks
// become formatting and nothing a person typed runs.
export const said = (text) => markdown(escape(text || ""));

export const KINDS = { channel: "Channel", direct: "Direct", agent: "Agent" };

export const REACTIONS = ["👍", "✅", "👀", "🎉", "❤️", "😄"];
