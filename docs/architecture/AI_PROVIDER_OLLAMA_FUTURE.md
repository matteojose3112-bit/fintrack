# AI Provider Architecture — Future Ollama Integration

**Status:** Future architecture note; no AI runtime integration in Foundation 0.3.

Yes: Aurelius can use the locally installed Ollama as an AI inference provider later. The recommended approach is a provider adapter so the product is not coupled to Ollama, one model family, or one machine.

## Proposed architecture

```
Aurelius application
  -> AI orchestration / policy layer
      -> provider interface
          -> Ollama local adapter (first local provider)
          -> optional hosted provider adapter (future)
```

The adapter should isolate:
- Base URL and model name in configuration, never hard-coded.
- Chat / structured-output request and response normalization.
- Timeouts, cancellation, retry limits, and health checks.
- Model capability declarations (tool use, JSON mode, context window, vision).
- Prompt templates and versioning.
- Redaction and data-minimization rules before sending private financial data to a model.

Ollama's local API and its OpenAI-compatible interface make this feasible. The exact endpoint and supported capabilities should be verified against the installed Ollama version and chosen model when implementation begins; do not assume every model supports tool calls or constrained JSON equally well.

## Financial safety boundary

AI is an analysis and explanation layer, not the accounting authority:
- The deterministic domain and database validate every account, amount, journal, and permission.
- The model may summarize, categorize, explain, forecast, or propose a draft journal for user review.
- The model cannot directly write ledger rows, bypass idempotency, change balances, close accounts, or execute trades/transfers.
- Any proposed financial action must be converted into a typed command, validated by deterministic code, shown to the user, and explicitly approved before execution.
- Read-only access is the default. Sensitive data is minimized and logged prompts/responses are governed by retention and privacy policy.
- Local Ollama can reduce the need to send data to a hosted model, but local execution is not automatically secure: machine access, model files, logs, network binding, backups, and access control still matter.

## Suggested rollout

1. Add a provider interface and fake deterministic provider for tests.
2. Add Ollama adapter behind a feature flag and configurable local endpoint.
3. Test unavailable server, malformed output, timeouts, unsupported capabilities, and model switching.
4. Add read-only financial summarization against sanitized fixtures.
5. Add draft-only categorization / journal suggestions with explicit human confirmation.
6. Consider hosted fallback only with explicit privacy, cost, and consent controls.

This is a future integration note only. Foundation 0.3 does not install, configure, expose, or call Ollama.
