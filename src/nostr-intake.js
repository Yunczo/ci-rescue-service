import {
  SimplePool,
  generateSecretKey,
  getPublicKey,
  nip17,
  nip19,
} from "nostr-tools";
import { bytesToHex, hexToBytes } from "nostr-tools/utils";
import { unwrapAuthenticatedNip17 } from "./nip17-auth.js";

const SERVICE_PUBLIC_KEY =
  "350390e2ddcb4d14a0802cff6c1ce47868871d6719cff65d4ecf9eca1bc276a3";
const RELAYS = [
  "wss://relay.damus.io",
  "wss://nos.lol",
  "wss://relay.primal.net",
  "wss://nostr.mom",
];
const STORAGE_KEY = "ci-rescue-anonymous-ticket-key-v1";
const SENT_AT_KEY = "ci-rescue-anonymous-ticket-sent-at-v1";

const form = document.querySelector("#anonymous-intake-form");
const status = document.querySelector("#anonymous-intake-status");
const ticket = document.querySelector("#anonymous-ticket-id");
const responseBox = document.querySelector("#anonymous-intake-response");
const refreshButton = document.querySelector("#anonymous-intake-refresh");

if (!form || !status || !ticket || !responseBox || !refreshButton) {
  throw new Error("Anonymous intake markup is incomplete");
}

function loadOrCreateTicketKey() {
  let stored = window.localStorage.getItem(STORAGE_KEY);
  if (!stored || !/^[0-9a-f]{64}$/.test(stored)) {
    stored = bytesToHex(generateSecretKey());
    window.localStorage.setItem(STORAGE_KEY, stored);
  }
  return hexToBytes(stored);
}

const ticketSecretKey = loadOrCreateTicketKey();
const ticketPublicKey = getPublicKey(ticketSecretKey);
const ticketNpub = nip19.npubEncode(ticketPublicKey);
ticket.textContent = ticketNpub;

function setStatus(message, state = "neutral") {
  status.textContent = message;
  status.dataset.state = state;
}

function acceptedRelayCount(results) {
  return results.filter(
    (result) =>
      result.status === "fulfilled" &&
      !/(failure|failed|error|reject|blocked|rate)/i.test(String(result.value)),
  ).length;
}

async function publishRequest(event) {
  const pool = new SimplePool({ enableReconnect: false });
  try {
    return await Promise.allSettled(pool.publish(RELAYS, event, { maxWait: 9_000 }));
  } finally {
    window.setTimeout(() => pool.destroy(), 250);
  }
}

async function loadReplies() {
  refreshButton.disabled = true;
  setStatus("Checking the encrypted reply inbox…");

  const pool = new SimplePool({ enableReconnect: false });
  try {
    const sentAt = Number(window.localStorage.getItem(SENT_AT_KEY) || 0);
    const filter = {
      kinds: [1059],
      "#p": [ticketPublicKey],
      limit: 50,
    };
    // NIP-59 gift wraps deliberately randomize their outer timestamp by up to
    // two days, so keep a three-day margin when polling the anonymous inbox.
    if (sentAt > 0) filter.since = Math.max(0, sentAt - 3 * 86_400);

    const wraps = await pool.querySync(RELAYS, filter, { maxWait: 8_000 });
    const replies = [];

    for (const wrap of wraps) {
      try {
        const rumor = unwrapAuthenticatedNip17(wrap, ticketSecretKey);
        if (rumor.pubkey !== SERVICE_PUBLIC_KEY) continue;
        replies.push({ createdAt: rumor.created_at, content: rumor.content });
      } catch {
        // Ignore unrelated or malformed encrypted events.
      }
    }

    replies.sort((a, b) => b.createdAt - a.createdAt);
    if (replies.length === 0) {
      responseBox.hidden = true;
      setStatus(
        sentAt > 0
          ? "No reply yet. Keep this browser storage and check again within 24 hours."
          : "No request has been sent from this browser yet.",
      );
      return;
    }

    let newest = replies[0].content;
    try {
      const parsed = JSON.parse(newest);
      newest = parsed.message || newest;
    } catch {
      // Plain text responses remain valid.
    }

    responseBox.textContent = newest;
    responseBox.hidden = false;
    setStatus("A signed reply from the CI Rescue service key was found.", "success");
  } catch {
    setStatus("The relay inbox could not be reached. Try refresh again shortly.", "error");
  } finally {
    pool.destroy();
    refreshButton.disabled = false;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = form.querySelector("button[type='submit']");
  const formData = new FormData(form);
  const payload = {
    version: 1,
    requestId: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    ticketPublicKey,
    summary: String(formData.get("summary") || "").trim(),
    publicUrl: String(formData.get("publicUrl") || "").trim(),
    details: String(formData.get("details") || "").trim(),
  };

  if (!payload.summary || !payload.details || !formData.get("sanitized")) {
    setStatus("Complete the required fields and confirm the evidence is sanitized.", "error");
    return;
  }

  submitButton.disabled = true;
  setStatus("Encrypting and publishing the request to independent relays…");

  try {
    const wrapped = nip17.wrapEvent(
      ticketSecretKey,
      { publicKey: SERVICE_PUBLIC_KEY, relayUrl: RELAYS[0] },
      JSON.stringify(payload),
      "CI Rescue request",
    );
    const results = await publishRequest(wrapped);
    const accepted = acceptedRelayCount(results);
    if (accepted < 1) throw new Error("No relay accepted the request");

    window.localStorage.setItem(SENT_AT_KEY, String(Math.floor(Date.now() / 1000)));
    form.reset();
    setStatus(
      `Encrypted request sent through ${accepted} relay${accepted === 1 ? "" : "s"}. Keep this browser storage and check for a reply within 24 hours.`,
      "success",
    );
  } catch {
    setStatus("The request was not accepted by a relay. Nothing was charged; try again later.", "error");
  } finally {
    submitButton.disabled = false;
  }
});

refreshButton.addEventListener("click", loadReplies);

if (window.localStorage.getItem(SENT_AT_KEY)) {
  loadReplies();
}
