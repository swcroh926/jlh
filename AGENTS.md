# Project collaboration

- The user wants periodic, plain-Korean development summaries. At meaningful milestones (features, fixes, dataset changes, tests, deployment), update `docs/DEVELOPMENT_LOG.md` with the current state and evidence.
- Distinguish local development, GitHub commits, GitHub Pages frontend deployment, public backend deployment, mocked tests, and actual provider calls. Do not claim live AI readiness from mocked tests or key presence.
- Keep the shareable Markdown copy at `/workspace/deliverables/탐구의씨앗-개발과배포기록.md` in sync when that workspace directory is available. Mention the updated document in the final reply.
- Never record API key values, full environment dumps, or sensitive raw provider logs in the development log.

## Explain work for a beginner (user preference)

- Before each stage, explain the user-facing capability in plain Korean, why it is next, and what changes in the screen, Python server, AI model and storage.
- At meaningful milestones, explain what now works and what happens next. Connect file/command details to their role in the service.
- For errors, explain the cause, user impact and intended fix. Explain material departures from the agreed requirements before implementing them; do not stop for routine approval.
- At completion, provide a concrete before/after example, the screen/input/button sequence for user testing, and distinguish mocked responses, live AI calls, local execution and public deployment.
- Briefly update completed vs remaining specification stages. Continue authorized work without repeatedly seeking confirmation.
