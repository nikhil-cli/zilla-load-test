import fetch from "node-fetch";
import { fetchEventSource } from "@microsoft/fetch-event-source";

async function startClient(id) {
  const url = "https://api.com/events/key/ohlc_test/test_9";

  console.log(`Client ${id} connecting...`);

  await fetchEventSource(url, {
    method: "GET",
    fetch: fetch,
    headers: {
      Accept: "text/event-stream"
    },
    onmessage(msg) {
      console.log(`Client ${id} ->`, msg.data);
    },
    onclose() {
      console.log(`Client ${id} connection closed by server.`);
    },
    onerror(err) {
      console.log(`Client ${id} error:`, err);
    },
  });
}

// Run 1000 concurrent clients
const CLIENTS = 1000;

for (let i = 1; i <= CLIENTS; i++) {
  startClient(i);
}

// Keep node alive for 1 hour
setTimeout(() => {
  console.log("Done running 1-hour SSE test.");
  process.exit(0);
}, 3600_000);
