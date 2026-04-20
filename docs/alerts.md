# Alert Rules and Runbooks

Owner: Member C - SLO and Alerts

This page is the runbook target for `config/alert_rules.yaml`. During demo, use the same investigation flow for every alert: start from metrics, open traces, then confirm the root cause in logs with the same `correlation_id`.

## SLO Summary

| SLI | Target | Window | Main dashboard panel |
|---|---:|---|---|
| Latency P95 | < 3000 ms | 28d | Latency P50/P95/P99 |
| Error Rate | < 2% | 28d | Error rate with breakdown |
| Daily Cost Budget | < $2.50/day | 1d | Cost over time |
| Average Quality Score | >= 0.75 | 28d | Quality proxy |

## 1. High latency P95

- Alert name: `high_latency_p95`
- Severity: P2
- Trigger: `latency_p95_ms > 5000 for 30m`
- Related SLO: Latency P95 < 3000 ms over 28d
- Likely lab incident: `rag_slow`
- Impact: users receive slow responses and tail latency breaches the SLO burn threshold.

First checks:

1. Open the latency dashboard panel and confirm P95 is above 5000 ms for the last 30 minutes.
2. Open the slowest traces from the last hour in Langfuse.
3. Compare RAG, LLM, and tool spans to locate the slow component.
4. Use the trace `correlation_id` to find matching JSON logs.
5. Check whether the incident toggle `rag_slow` is enabled.

Mitigation:

- Reduce prompt or context size for affected requests.
- Fallback to a faster retrieval source if the RAG span is slow.
- Temporarily lower concurrency or rate-limit expensive requests.
- After mitigation, rerun traffic and verify P95 returns below 3000 ms.

Evidence to capture:

- Screenshot of the latency panel with the threshold line.
- Trace waterfall showing the slow span.
- Log line with the same `correlation_id`.

## 2. High error rate

- Alert name: `high_error_rate`
- Severity: P1
- Trigger: `error_rate_pct > 5 for 5m`
- Related SLO: Error Rate < 2% over 28d
- Likely lab incident: `tool_fail`
- Impact: users receive failed responses and the service availability target is at risk.

First checks:

1. Open the error rate dashboard panel and confirm the error rate is above 5%.
2. Group recent JSON logs by `error_type`.
3. Use `correlation_id` to connect failed logs to failed traces.
4. Inspect whether the failure is from the LLM, RAG retrieval, tool call, or response schema.
5. Check recent changes or incident toggles before rolling back anything.

Mitigation:

- Disable or bypass the failing tool when possible.
- Retry with a fallback model or fallback retrieval path.
- Roll back the latest risky change if failures started after deployment.
- Verify the error rate drops below 2% after the fix.

Evidence to capture:

- Screenshot of the error rate panel.
- Example failed trace.
- JSON log line containing `error_type` and `correlation_id`.

## 3. Cost budget spike

- Alert name: `cost_budget_spike`
- Severity: P2
- Trigger: `hourly_cost_usd > 2x_baseline for 15m`
- Related SLO: Daily Cost Budget < $2.50/day
- Likely lab incident: `cost_spike`
- Impact: token usage or model routing burns budget faster than expected.

First checks:

1. Open the cost dashboard panel and confirm hourly cost is above 2x baseline.
2. Split recent traces by feature, model, and user/session if available.
3. Compare `tokens_in` and `tokens_out` for normal traffic versus spike traffic.
4. Use logs with the same `correlation_id` to confirm request shape and feature.
5. Check whether the incident toggle `cost_spike` is enabled.

Mitigation:

- Shorten prompts and reduce retrieved context size.
- Route simple requests to a cheaper model.
- Cap max output tokens for the affected endpoint.
- Enable or improve prompt caching if available.
- Verify projected daily cost returns below $2.50/day.

Evidence to capture:

- Screenshot of the cost panel.
- Trace showing abnormal token usage.
- Before/after cost value after mitigation.
