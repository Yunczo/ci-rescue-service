# CI Rescue service terms

## Scope confirmation

No payment is requested until either the no-account anonymous inbox or a public GitHub intake issue contains enough sanitized evidence to confirm that the request fits the advertised one-workflow scope. The workflow may have one failing job path or one defined proactive Node 24 migration goal. A scope response is normally posted within 24 hours. An acceptance reply must state the accepted USD price, the exact BTC amount, the payment address, the quote expiry, and the delivery window. The BTC quote expires after 24 hours unless the acceptance reply states otherwise.

## Delivery

The US$49 Rescue package includes:

- one GitHub Actions workflow;
- one failing job path or one defined Node 24 migration goal;
- one focused patch or unified diff;
- a short root-cause and verification report; and
- one revision addressing the originally accepted failure.

The default delivery window is 48 hours from confirmed payment and receipt of the required sanitized inputs.

The included revision must be requested within seven calendar days of delivery and must address the originally accepted failure. New workflows, failure paths, or requirements are a new scope.

## Buyer safety

- GitHub issues in this repository are public.
- The no-account route encrypts message content with NIP-17, but public relays can observe transport metadata and availability is not guaranteed.
- The anonymous ticket key exists only in the buyer's browser storage; clearing it loses access to replies.
- Do not post secrets, tokens, private repository URLs, personal data, production logs, or proprietary source.
- Replace sensitive values and provide the smallest reproducible excerpt.
- No production, cloud-account, or credential access is requested or accepted.

## Payment and refunds

Bitcoin is irreversible. The buyer must not pay until a signed anonymous-inbox reply or public GitHub reply explicitly confirms scope and the BTC amount. If the accepted work cannot be delivered for a reason attributable to the service provider, a refund can be sent to a buyer-provided Bitcoin address, less the network fee actually required for that refund transaction. Scope changes after payment require a new written agreement; they are not silently added.

## Boundaries

This is CI diagnostics and implementation work, not security review, legal advice, tax advice, accounting advice, or a guarantee of hosted-run success. A clean diagnostic report means only that the included checks found no matching condition.
