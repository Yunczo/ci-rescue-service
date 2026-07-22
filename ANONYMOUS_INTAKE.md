# Anonymous intake boundary

The landing page offers a no-account request channel for buyers who do not want to create a GitHub issue.

## Public service identity

- Nostr public key: `350390e2ddcb4d14a0802cff6c1ce47868871d6719cff65d4ecf9eca1bc276a3`
- Nostr npub: `npub1x5pepckaedx3fgyq9nlkc88y0p5gw8t8r88lvh2we70v5x7zw63sxrrtak`
- [Public profile and field-guide note](https://njump.me/nevent1qgsr2qusutwukng55zqzelmvrnj8s6y8r4n3nnlkt48vl8k2r0p8dgcpz3mhxue69uhhyetvv9ujuerpd46hxtnfduqs6amnwvaz7tmwdaejumr0dsq3vamnwvaz7tmjv4kxz7fwwpexjmtpdshxuet5qqsdgaupfaty0x4kwsec58fgp24e8twq65jwtztejgatgnqe3tuhllqmrux48)

## Transport

The page generates a random ticket key in browser storage, encrypts the request to the service public key using NIP-17 gift-wrapped direct messages, and publishes the same signed event to several independent public Nostr relays. Before a reply is attributed to the service key, the page verifies the gift-wrap and seal signatures, their event IDs and required kinds, the intended-recipient tags, the rumor ID, and that the seal signer is the rumor author. The authenticated author must then exactly match the service public key above.

This design removes login and email requirements. It does not make transport metadata private, guarantee relay availability, recover a cleared browser key, or make sensitive material appropriate to send. Buyers must not submit secrets, tokens, private URLs, personal data, proprietary source, production logs, or credentials.

The public GitHub issue template remains available as an alternative. No service payment is requested until one of the two intake channels contains a written scope acceptance with an exact BTC amount, address, quote expiry, and delivery window.
