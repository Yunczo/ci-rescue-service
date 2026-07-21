# CI Rescue service terms

## Scope confirmation

No payment is requested until the public intake issue contains enough sanitized evidence to confirm that the request fits the advertised one-workflow scope. An intake reply must state the accepted USD price, the exact BTC amount, the payment address, and the delivery window.

## Delivery

The US$49 Rescue package includes:

- one GitHub Actions workflow;
- one failing job path;
- one focused patch or unified diff;
- a short root-cause and verification report; and
- one revision addressing the originally accepted failure.

The default delivery window is two days from confirmed payment and receipt of the required sanitized inputs.

## Buyer safety

- GitHub issues in this repository are public.
- Do not post secrets, tokens, private repository URLs, personal data, production logs, or proprietary source.
- Replace sensitive values and provide the smallest reproducible excerpt.
- No production, cloud-account, or credential access is requested or accepted.

## Payment and refunds

Bitcoin is irreversible. The buyer must not pay until the intake issue explicitly confirms scope and the BTC amount. If the accepted work cannot be delivered for a reason attributable to the service provider, a refund can be sent to a buyer-provided Bitcoin address, less the network fee actually required for that refund transaction. Scope changes after payment require a new written agreement; they are not silently added.

## Boundaries

This is CI diagnostics and implementation work, not security review, legal advice, tax advice, accounting advice, or a guarantee of hosted-run success. A clean diagnostic report means only that the included checks found no matching condition.
