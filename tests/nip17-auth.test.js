import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  finalizeEvent,
  generateSecretKey,
  getEventHash,
  getPublicKey,
  nip17,
  nip44,
} from "nostr-tools";

import { unwrapAuthenticatedNip17 } from "../src/nip17-auth.js";

const now = () => Math.floor(Date.now() / 1000);

test("the live intake uses authenticated unwrapping", async () => {
  const source = await readFile(new URL("../src/nostr-intake.js", import.meta.url), "utf8");
  assert.match(source, /unwrapAuthenticatedNip17/);
  assert.doesNotMatch(source, /nip17\.unwrapEvent/);
});

function encryptedJson(value, senderSecretKey, recipientPublicKey) {
  const conversationKey = nip44.getConversationKey(senderSecretKey, recipientPublicKey);
  return nip44.encrypt(JSON.stringify(value), conversationKey);
}

function makeRumor(senderSecretKey, recipientPublicKey, overrides = {}) {
  const rumor = {
    pubkey: getPublicKey(senderSecretKey),
    created_at: now(),
    kind: 14,
    tags: [["p", recipientPublicKey]],
    content: "authenticated message",
    ...overrides,
  };
  rumor.id = getEventHash(rumor);
  return rumor;
}

function makeSeal(rumor, senderSecretKey, recipientPublicKey, overrides = {}) {
  return finalizeEvent(
    {
      kind: 13,
      created_at: now(),
      tags: [],
      content: encryptedJson(rumor, senderSecretKey, recipientPublicKey),
      ...overrides,
    },
    senderSecretKey,
  );
}

function makeWrap(seal, recipientPublicKey, overrides = {}) {
  const outerSecretKey = generateSecretKey();
  return finalizeEvent(
    {
      kind: 1059,
      created_at: now(),
      tags: [["p", recipientPublicKey]],
      content: encryptedJson(seal, outerSecretKey, recipientPublicKey),
      ...overrides,
    },
    outerSecretKey,
  );
}

test("accepts a fully authenticated NIP-17 direct message", () => {
  const senderSecretKey = generateSecretKey();
  const recipientSecretKey = generateSecretKey();
  const recipientPublicKey = getPublicKey(recipientSecretKey);
  const wrap = nip17.wrapEvent(
    senderSecretKey,
    { publicKey: recipientPublicKey },
    "valid reply",
  );

  const rumor = unwrapAuthenticatedNip17(wrap, recipientSecretKey);
  assert.equal(rumor.pubkey, getPublicKey(senderSecretKey));
  assert.equal(rumor.content, "valid reply");
});

test("rejects an attacker seal carrying a rumor that impersonates another key", () => {
  const attackerSecretKey = generateSecretKey();
  const claimedSecretKey = generateSecretKey();
  const recipientSecretKey = generateSecretKey();
  const recipientPublicKey = getPublicKey(recipientSecretKey);
  const claimedPublicKey = getPublicKey(claimedSecretKey);
  const forgedRumor = makeRumor(attackerSecretKey, recipientPublicKey, {
    pubkey: claimedPublicKey,
    content: "forged service reply",
  });
  const forgedWrap = makeWrap(
    makeSeal(forgedRumor, attackerSecretKey, recipientPublicKey),
    recipientPublicKey,
  );

  assert.equal(nip17.unwrapEvent(forgedWrap, recipientSecretKey).pubkey, claimedPublicKey);
  assert.throws(
    () => unwrapAuthenticatedNip17(forgedWrap, recipientSecretKey),
    /seal signer does not match rumor author/,
  );
});

test("rejects invalid outer and seal signatures", () => {
  const senderSecretKey = generateSecretKey();
  const recipientSecretKey = generateSecretKey();
  const recipientPublicKey = getPublicKey(recipientSecretKey);
  const validWrap = nip17.wrapEvent(
    senderSecretKey,
    { publicKey: recipientPublicKey },
    "valid reply",
  );
  const badOuter = { ...validWrap, sig: "0".repeat(128) };
  assert.throws(
    () => unwrapAuthenticatedNip17(badOuter, recipientSecretKey),
    /gift wrap signature is invalid/,
  );

  const rumor = makeRumor(senderSecretKey, recipientPublicKey);
  const seal = makeSeal(rumor, senderSecretKey, recipientPublicKey);
  const badSeal = { ...seal, sig: "0".repeat(128) };
  assert.throws(
    () => unwrapAuthenticatedNip17(makeWrap(badSeal, recipientPublicKey), recipientSecretKey),
    /seal signature is invalid/,
  );
});

test("rejects a changed rumor id, wrong kinds, and wrong recipient tags", () => {
  const senderSecretKey = generateSecretKey();
  const recipientSecretKey = generateSecretKey();
  const recipientPublicKey = getPublicKey(recipientSecretKey);
  const otherPublicKey = getPublicKey(generateSecretKey());

  const changedIdRumor = makeRumor(senderSecretKey, recipientPublicKey);
  changedIdRumor.id = "0".repeat(64);
  assert.throws(
    () =>
      unwrapAuthenticatedNip17(
        makeWrap(makeSeal(changedIdRumor, senderSecretKey, recipientPublicKey), recipientPublicKey),
        recipientSecretKey,
      ),
    /rumor id is invalid/,
  );

  const wrongRumorKind = makeRumor(senderSecretKey, recipientPublicKey, { kind: 1 });
  assert.throws(
    () =>
      unwrapAuthenticatedNip17(
        makeWrap(makeSeal(wrongRumorKind, senderSecretKey, recipientPublicKey), recipientPublicKey),
        recipientSecretKey,
      ),
    /rumor has the wrong kind/,
  );

  const rumor = makeRumor(senderSecretKey, recipientPublicKey);
  const wrongSealKind = makeSeal(rumor, senderSecretKey, recipientPublicKey, { kind: 12 });
  assert.throws(
    () => unwrapAuthenticatedNip17(makeWrap(wrongSealKind, recipientPublicKey), recipientSecretKey),
    /seal has the wrong kind/,
  );

  const seal = makeSeal(rumor, senderSecretKey, recipientPublicKey);
  assert.throws(
    () =>
      unwrapAuthenticatedNip17(
        makeWrap(seal, recipientPublicKey, { kind: 1 }),
        recipientSecretKey,
      ),
    /gift wrap has the wrong kind/,
  );
  assert.throws(
    () =>
      unwrapAuthenticatedNip17(
        makeWrap(seal, recipientPublicKey, { tags: [["p", otherPublicKey]] }),
        recipientSecretKey,
      ),
    /gift wrap is not addressed to this recipient/,
  );

  const wrongRecipientRumor = makeRumor(senderSecretKey, recipientPublicKey, {
    tags: [["p", otherPublicKey]],
  });
  assert.throws(
    () =>
      unwrapAuthenticatedNip17(
        makeWrap(
          makeSeal(wrongRecipientRumor, senderSecretKey, recipientPublicKey),
          recipientPublicKey,
        ),
        recipientSecretKey,
      ),
    /rumor is not addressed to this recipient/,
  );
});
