import {
  getEventHash,
  getPublicKey,
  nip44,
  verifyEvent,
} from "nostr-tools";

const GIFT_WRAP_KIND = 1059;
const SEAL_KIND = 13;
const PRIVATE_MESSAGE_KIND = 14;
const MAX_ENCRYPTED_CONTENT_LENGTH = 1_000_000;
const HEX_32 = /^[0-9a-f]{64}$/;
const HEX_64 = /^[0-9a-f]{128}$/;

function canonicalEvent(event, { signed, label }) {
  if (!event || typeof event !== "object") {
    throw new Error(`${label} is not an event`);
  }
  if (!Number.isSafeInteger(event.kind) || !Number.isSafeInteger(event.created_at)) {
    throw new Error(`${label} has invalid numeric fields`);
  }
  if (
    !HEX_32.test(event.id || "") ||
    !HEX_32.test(event.pubkey || "") ||
    (signed && !HEX_64.test(event.sig || "")) ||
    typeof event.content !== "string" ||
    !Array.isArray(event.tags) ||
    !event.tags.every(
      (tag) => Array.isArray(tag) && tag.every((value) => typeof value === "string"),
    )
  ) {
    throw new Error(`${label} has invalid fields`);
  }
  if (event.content.length > MAX_ENCRYPTED_CONTENT_LENGTH) {
    throw new Error(`${label} content is too large`);
  }

  const canonical = {
    id: event.id,
    pubkey: event.pubkey,
    created_at: event.created_at,
    kind: event.kind,
    tags: event.tags.map((tag) => [...tag]),
    content: event.content,
  };
  if (signed) canonical.sig = event.sig;
  return canonical;
}

function verifySignedEvent(event, expectedKind, label) {
  const canonical = canonicalEvent(event, { signed: true, label });
  if (canonical.kind !== expectedKind) {
    throw new Error(`${label} has the wrong kind`);
  }
  if (getEventHash(canonical) !== canonical.id || !verifyEvent(canonical)) {
    throw new Error(`${label} signature is invalid`);
  }
  return canonical;
}

function decryptJson(event, recipientSecretKey, label) {
  const conversationKey = nip44.getConversationKey(recipientSecretKey, event.pubkey);
  const plaintext = nip44.decrypt(event.content, conversationKey);
  const parsed = JSON.parse(plaintext);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label} plaintext is not an event`);
  }
  return parsed;
}

function hasRecipient(event, recipientPublicKey) {
  return event.tags.some(
    (tag) => tag[0] === "p" && tag[1] === recipientPublicKey,
  );
}

export function unwrapAuthenticatedNip17(wrap, recipientSecretKey) {
  const recipientPublicKey = getPublicKey(recipientSecretKey);
  const authenticatedWrap = verifySignedEvent(wrap, GIFT_WRAP_KIND, "gift wrap");
  if (!hasRecipient(authenticatedWrap, recipientPublicKey)) {
    throw new Error("gift wrap is not addressed to this recipient");
  }

  const decryptedSeal = decryptJson(authenticatedWrap, recipientSecretKey, "seal");
  const authenticatedSeal = verifySignedEvent(decryptedSeal, SEAL_KIND, "seal");
  if (authenticatedSeal.tags.length !== 0) {
    throw new Error("seal must not expose tags");
  }

  const decryptedRumor = decryptJson(authenticatedSeal, recipientSecretKey, "rumor");
  const rumor = canonicalEvent(decryptedRumor, { signed: false, label: "rumor" });
  if (rumor.kind !== PRIVATE_MESSAGE_KIND) {
    throw new Error("rumor has the wrong kind");
  }
  if (getEventHash(rumor) !== rumor.id) {
    throw new Error("rumor id is invalid");
  }
  if (authenticatedSeal.pubkey !== rumor.pubkey) {
    throw new Error("seal signer does not match rumor author");
  }
  if (!hasRecipient(rumor, recipientPublicKey)) {
    throw new Error("rumor is not addressed to this recipient");
  }

  return rumor;
}
