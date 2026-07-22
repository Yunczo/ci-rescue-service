export function updateIntakeStatus(
  ticketStatus,
  submissionStatus,
  message,
  state = "neutral",
  { useSubmission = false, focusSubmission = false } = {},
) {
  if (useSubmission) {
    submissionStatus.hidden = false;
    submissionStatus.textContent = message;
    submissionStatus.dataset.state = state;

    if (focusSubmission) {
      submissionStatus.focus({ preventScroll: true });
      submissionStatus.scrollIntoView({ block: "nearest" });
    }
    return;
  }

  ticketStatus.textContent = message;
  ticketStatus.dataset.state = state;
}
