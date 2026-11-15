# Security

Agent ARB reads architecture documents, which are often sensitive. It is built to keep them on your machine:

- The CLI sends prompts only to the model endpoint you configure, which defaults to a local Ollama server.
- A prompt carries one decision's text plus the rules selected for it, never a whole document or pack.
- Seed documents are compiled locally and never sent anywhere.
- There is no telemetry.
- Every run writes a manifest listing exactly what each prompt contained.

## Reporting a vulnerability

Email the maintainer at the address on the GitHub profile with a description and, if possible, a reproduction. Please do not open a public issue for a vulnerability. You will get an acknowledgement within five working days.
