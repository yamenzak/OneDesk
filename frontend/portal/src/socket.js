import { io } from "socket.io-client";

import { boot } from "./words";

let socket = null;

export function realtime() {
  if (socket) return socket;
  const port = window.location.port ? `:${boot().socketio_port || 9000}` : "";
  const scheme = window.location.protocol === "https:" ? "https" : "http";
  socket = io(`${scheme}://${window.location.hostname}${port}/${boot().site_name}`, { withCredentials: true, reconnectionAttempts: 5 });
  return socket;
}
