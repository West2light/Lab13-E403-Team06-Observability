# Member D Report — Load Test & Incident Injection

## 1. Member Metadata
- **Member**: Dương Quang Đông
- **Role**: Load Test & Incident Injection
- **Primary files**:
  - [scripts/load_test.py](scripts/load_test.py)
  - [scripts/inject_incident.py](scripts/inject_incident.py)
  - [app/incidents.py](app/incidents.py)
  - [data/incidents.json](data/incidents.json)
- **Supporting implementation context**:
  - Incident states are stored in [app/incidents.py:3-7](app/incidents.py#L3-L7).
  - Incident toggling is triggered by [scripts/inject_incident.py:10-18](scripts/inject_incident.py#L10-L18).
  - Client-side latency and response status are printed by [scripts/load_test.py:13-18](scripts/load_test.py#L13-L18).
  - The updated rule-based LLM behavior is implemented in [app/mock_llm.py:27-60](app/mock_llm.py#L27-L60), and `cost_spike` multiplies `output_tokens` by 4 at [app/mock_llm.py:31-32](app/mock_llm.py#L31-L32).

## 2. Role D Scope
The work for Member D focused on validating how the application behaves under normal traffic and under injected incidents. The responsibilities covered in this report are:

1. Execute baseline and concurrent load tests.
2. Inject each supported incident scenario and confirm the state change.
3. Collect terminal output and structured log evidence from [data/logs.jsonl](data/logs.jsonl).
4. Compare latency, error, token, and cost behavior across scenarios.
5. Provide evidence that can be reused in the group dashboard and incident response sections.

## 3. Test Setup
### 3.1 Commands used
```powershell
uvicorn app.main:app --reload
python scripts/load_test.py --concurrency 1
python scripts/load_test.py --concurrency 5
python scripts/inject_incident.py --scenario rag_slow
python scripts/inject_incident.py --scenario rag_slow --disable
python scripts/inject_incident.py --scenario tool_fail
python scripts/inject_incident.py --scenario tool_fail --disable
python scripts/inject_incident.py --scenario cost_spike
python scripts/inject_incident.py --scenario cost_spike --disable
python scripts/validate_logs.py
Get-Content .\data\logs.jsonl | Select-Object -Last 20
```

### 3.2 Scenario definitions
The three incident scenarios validated in this report match the descriptions in [data/incidents.json:2-4](data/incidents.json#L2-L4):
- `rag_slow`: retrieval latency spike
- `tool_fail`: vector store or tool error
- `cost_spike`: output token cost spike

## 4. Scenario Analysis

### 4.1 Baseline (no incident enabled)
#### Observed result
- All 10 requests returned HTTP `200`.
- Client-observed latency stayed in the **160.0ms–176.6ms** range.
- Log validation passed with **100/100**, no missing required fields, no missing context enrichment, and no detected PII leaks.
- Structured logs show stable `latency_ms=150` and moderate `cost_usd` values.

#### Evidence summary
Representative baseline log pair:
- `request_received` with correlation ID `req-71c2d057`
- `response_sent` with `latency_ms=150`, `tokens_in=37`, `tokens_out=137`, `cost_usd=0.002166`

#### Interpretation
This is the control sample for all later comparisons. The baseline confirms that the application is healthy, correlation IDs are present, logs are enriched, and PII is redacted before any incident is injected.

---

### 4.2 Incident: `rag_slow`
#### Incident status
The incident toggle returned:
```log
200 {'ok': True, 'incidents': {'rag_slow': True, 'tool_fail': False, 'cost_spike': False}}
```

#### Observed result
- All requests still returned HTTP `200`.
- With `--concurrency 5`, client-observed latency increased sharply to about **5.3s** for the first completions and **13.3s** for the remaining requests.
- Application logs show per-request `latency_ms` around **2650–2668ms**.

#### Evidence summary
Representative `rag_slow` log pair:
- `request_received` with correlation ID `req-7c5d1df5`
- `response_sent` with `latency_ms=2650`, `tokens_in=37`, `tokens_out=119`, `cost_usd=0.001896`

#### Interpretation
This scenario proves the latency degradation path expected from `rag_slow`. The gap between the server-side `latency_ms` (~2.65s) and the client-side completion time (5.3s–13.3s) under concurrency suggests additional waiting or queueing under load. This makes `rag_slow` a strong scenario for dashboard panels and for trace-based latency investigation.

---

### 4.3 Incident: `tool_fail`
#### Incident status
The incident toggle returned:
```log
200 {'ok': True, 'incidents': {'rag_slow': False, 'tool_fail': True, 'cost_spike': False}}
```

#### Observed result
- All requests returned HTTP `500`.
- Client-observed latency dropped to **8.9ms–30.7ms**, because requests failed fast.
- Structured logs changed from `response_sent` to `request_failed`.
- Each failure includes `error_type="RuntimeError"` and `detail="Vector store timeout"`.

#### Evidence summary
Representative `tool_fail` log pair:
- `request_received` with correlation ID `req-d7c992d0`
- `request_failed` with `error_type=RuntimeError` and payload detail `Vector store timeout`

#### Interpretation
This scenario proves the error path clearly. The terminal output shows `[500] None` because [scripts/load_test.py:18](scripts/load_test.py#L18) prints `r.json().get('correlation_id')`, while the 500 response body does not include that field. However, the application logs still preserve correlation IDs, so the incident remains traceable in structured logging.

---

### 4.4 Incident: `cost_spike`
#### Incident status
The incident toggle returned:
```log
200 {'ok': True, 'incidents': {'rag_slow': False, 'tool_fail': False, 'cost_spike': True}}
```

#### Observed result
- All 10 requests returned HTTP `200`.
- Client-observed latency stayed close to baseline at **160.5ms–171.6ms**.
- The main change appeared in `tokens_out` and `cost_usd`, not latency or status.
- Baseline `tokens_out` was roughly **82–179**, while `cost_spike` raised it to **364–716**.
- Baseline `cost_usd` was roughly **0.001344–0.002781**, while `cost_spike` raised it to **0.00555–0.010842**.

#### Evidence summary
Representative `cost_spike` log pair:
- `request_received` with correlation ID `req-1d035d2d`
- `response_sent` with `latency_ms=150`, `tokens_out=628`, `cost_usd=0.009531`

#### Interpretation
This scenario proves that an operational cost anomaly can occur even when request latency and success rate look healthy. It is therefore important for the group dashboard to include token/cost panels instead of relying only on error rate and latency.

## 5. Role D Findings Summary

| Scenario | HTTP status pattern | Client latency | Main log signal | Conclusion |
|---|---|---:|---|---|
| Baseline | All `200` | 160.0ms–176.6ms | `response_sent`, `latency_ms=150`, normal token/cost values | Healthy baseline |
| `rag_slow` | All `200` | 5.3s–13.35s | `response_sent`, `latency_ms≈2650ms` | Severe latency regression under concurrency |
| `tool_fail` | All `500` | 8.9ms–30.7ms | `request_failed`, `RuntimeError`, `Vector store timeout` | Fast-fail error scenario with clear root cause in logs |
| `cost_spike` | All `200` | 160.5ms–171.6ms | Normal latency, but much higher `tokens_out` and `cost_usd` | Cost anomaly without latency/error regression |

## 6. Role D Contribution Statement
This work is ready to be referenced in the Member D section of [docs/blueprint-template.md](docs/blueprint-template.md).

### Ready-to-paste content for `[MEMBER_D_NAME]`
- **[TASKS_COMPLETED]**: Executed baseline load testing and incident injection for `rag_slow`, `tool_fail`, and `cost_spike`; collected terminal output and structured log evidence; compared latency, error, token, and cost behavior across scenarios; prepared evidence for dashboard and incident response analysis.
- **[EVIDENCE_LINK]**: [docs/D_report.md](docs/D_report.md)

## 7. Conclusion
Member D successfully validated the system behavior in both normal and injected-failure conditions. The collected evidence shows three distinct observability patterns:
- `rag_slow` degrades latency under concurrency,
- `tool_fail` produces explicit 500 errors with clear root-cause logs,
- `cost_spike` increases usage cost without affecting latency.

These results are aligned with the intended responsibilities of the Load Test & Incident Injection role.

---

## Appendix A — Raw Command Evidence

### A.1 Start the app
```powershell
uvicorn app.main:app --reload
```

### A.2 Baseline: no incident enabled
```powershell
python scripts/load_test.py --concurrency 1
```
```log
[200] req-71c2d057 | qa | 176.6ms
[200] req-0e514814 | qa | 161.7ms
[200] req-8e9b1ed5 | summary | 161.2ms
[200] req-33f9a472 | qa | 168.1ms
[200] req-d10c91a5 | qa | 165.1ms
[200] req-36825447 | summary | 164.7ms
[200] req-5726d7cf | qa | 165.9ms
[200] req-4013382c | qa | 167.2ms
[200] req-3636cf32 | qa | 160.0ms
[200] req-0aac019f | qa | 170.2ms
```

```powershell
python scripts/validate_logs.py
```
```log
--- Lab Verification Results ---
Total log records analyzed: 21
Records with missing required fields: 0
Records with missing enrichment (context): 0
Unique correlation IDs found: 11
Potential PII leaks detected: 0

--- Grading Scorecard (Estimates) ---
+ [PASSED] Basic JSON schema
+ [PASSED] Correlation ID propagation
+ [PASSED] Log enrichment
+ [PASSED] PII scrubbing

Estimated Score: 100/100
```

```powershell
Get-Content .\data\logs.jsonl | Select-Object -Last 20
```
```log
{"service": "api", "payload": {"message_preview": "What is your refund policy? My email is [REDACTED_EMAIL]"}, "event": "request_received", "user_id_hash": "2055254ee30a", "env": "dev", "feature": "qa", "session_id": "s01", "model": "claude-sonnet-4-5", "correlation_id": "req-71c2d057", "level": "info", "ts": "2026-04-20T09:50:02.776954Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 37, "tokens_out": 137, "cost_usd": 0.002166, "payload": {"answer_preview": "Based on our documentation: Refunds are available within 7 days with proof of pu..."}, "event": "response_sent", "user_id_hash": "2055254ee30a", "env": "dev", "feature": "qa", "session_id": "s01", "model": "claude-sonnet-4-5", "correlation_id": "req-71c2d057", "level": "info", "ts": "2026-04-20T09:50:02.930843Z"}
{"service": "api", "payload": {"message_preview": "Explain why metrics traces and logs work together"}, "event": "request_received", "user_id_hash": "95b6504a8bd6", "env": "dev", "feature": "qa", "session_id": "s02", "model": "claude-sonnet-4-5", "correlation_id": "req-0e514814", "level": "info", "ts": "2026-04-20T09:50:02.938229Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 33, "tokens_out": 135, "cost_usd": 0.002124, "payload": {"answer_preview": "Do not expose PII, passwords, or sensitive data in logs. Use sanitized summaries..."}, "event": "response_sent", "user_id_hash": "95b6504a8bd6", "env": "dev", "feature": "qa", "session_id": "s02", "model": "claude-sonnet-4-5", "correlation_id": "req-0e514814", "level": "info", "ts": "2026-04-20T09:50:03.093092Z"}
{"service": "api", "payload": {"message_preview": "Summarize the monitoring policy for production logging"}, "event": "request_received", "user_id_hash": "97ce842ec69d", "env": "dev", "feature": "summary", "session_id": "s03", "model": "claude-sonnet-4-5", "correlation_id": "req-8e9b1ed5", "level": "info", "ts": "2026-04-20T09:50:03.099662Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 40, "tokens_out": 82, "cost_usd": 0.00135, "payload": {"answer_preview": "Based on our documentation: Metrics detect incidents, traces localize them, logs..."}, "event": "response_sent", "user_id_hash": "97ce842ec69d", "env": "dev", "feature": "summary", "session_id": "s03", "model": "claude-sonnet-4-5", "correlation_id": "req-8e9b1ed5", "level": "info", "ts": "2026-04-20T09:50:03.254632Z"}
{"service": "api", "payload": {"message_preview": "Can I get help with policy and monitoring?"}, "event": "request_received", "user_id_hash": "75af07890985", "env": "dev", "feature": "qa", "session_id": "s04", "model": "claude-sonnet-4-5", "correlation_id": "req-33f9a472", "level": "info", "ts": "2026-04-20T09:50:03.261921Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 36, "tokens_out": 105, "cost_usd": 0.001683, "payload": {"answer_preview": "Based on our documentation: Metrics detect incidents, traces localize them, logs..."}, "event": "response_sent", "user_id_hash": "75af07890985", "env": "dev", "feature": "qa", "session_id": "s04", "model": "claude-sonnet-4-5", "correlation_id": "req-33f9a472", "level": "info", "ts": "2026-04-20T09:50:03.420628Z"}
{"service": "api", "payload": {"message_preview": "Here is my phone [REDACTED_PHONE_VN], what should be logged?"}, "event": "request_received", "user_id_hash": "64f6ec689229", "env": "dev", "feature": "qa", "session_id": "s05", "model": "claude-sonnet-4-5", "correlation_id": "req-d10c91a5", "level": "info", "ts": "2026-04-20T09:50:03.432535Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 34, "tokens_out": 153, "cost_usd": 0.002397, "payload": {"answer_preview": "Do not expose PII, passwords, or sensitive data in logs. Use sanitized summaries..."}, "event": "response_sent", "user_id_hash": "64f6ec689229", "env": "dev", "feature": "qa", "session_id": "s05", "model": "claude-sonnet-4-5", "correlation_id": "req-d10c91a5", "level": "info", "ts": "2026-04-20T09:50:03.588268Z"}
{"service": "api", "payload": {"message_preview": "Give me a short summary of the observability workflow"}, "event": "request_received", "user_id_hash": "4c4f62330d76", "env": "dev", "feature": "summary", "session_id": "s06", "model": "claude-sonnet-4-5", "correlation_id": "req-36825447", "level": "info", "ts": "2026-04-20T09:50:03.594877Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 36, "tokens_out": 170, "cost_usd": 0.002658, "payload": {"answer_preview": "Metrics detect incidents, traces localize them, and logs explain the root cause...."}, "event": "response_sent", "user_id_hash": "4c4f62330d76", "env": "dev", "feature": "summary", "session_id": "s06", "model": "claude-sonnet-4-5", "correlation_id": "req-36825447", "level": "info", "ts": "2026-04-20T09:50:03.750939Z"}
{"service": "api", "payload": {"message_preview": "What should not appear in app logs?"}, "event": "request_received", "user_id_hash": "1632c29ecdec", "env": "dev", "feature": "qa", "session_id": "s07", "model": "claude-sonnet-4-5", "correlation_id": "req-5726d7cf", "level": "info", "ts": "2026-04-20T09:50:03.764716Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 30, "tokens_out": 179, "cost_usd": 0.002775, "payload": {"answer_preview": "Do not expose PII, passwords, or sensitive data in logs. Use sanitized summaries..."}, "event": "response_sent", "user_id_hash": "1632c29ecdec", "env": "dev", "feature": "qa", "session_id": "s07", "model": "claude-sonnet-4-5", "correlation_id": "req-5726d7cf", "level": "info", "ts": "2026-04-20T09:50:03.919998Z"}
{"service": "api", "payload": {"message_preview": "How do I debug tail latency?"}, "event": "request_received", "user_id_hash": "2f015d970c0b", "env": "dev", "feature": "qa", "session_id": "s08", "model": "claude-sonnet-4-5", "correlation_id": "req-4013382c", "level": "info", "ts": "2026-04-20T09:50:03.926075Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 28, "tokens_out": 84, "cost_usd": 0.001344, "payload": {"answer_preview": "To debug tail latency, compare P50/P95/P99 in metrics, find the slow span in tra..."}, "event": "response_sent", "user_id_hash": "2f015d970c0b", "env": "dev", "feature": "qa", "session_id": "s08", "model": "claude-sonnet-4-5", "correlation_id": "req-4013382c", "level": "info", "ts": "2026-04-20T09:50:04.082605Z"}
{"service": "api", "payload": {"message_preview": "What is the policy for PII and credit card [REDACTED_CREDIT_CARD]?"}, "event": "request_received", "user_id_hash": "4d14d5d4f719", "env": "dev", "feature": "qa", "session_id": "s09", "model": "claude-sonnet-4-5", "correlation_id": "req-3636cf32", "level": "info", "ts": "2026-04-20T09:50:04.094364Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 37, "tokens_out": 178, "cost_usd": 0.002781, "payload": {"answer_preview": "Based on our documentation: Do not expose PII in logs. Use sanitized summaries o..."}, "event": "response_sent", "user_id_hash": "4d14d5d4f719", "env": "dev", "feature": "qa", "session_id": "s09", "model": "claude-sonnet-4-5", "correlation_id": "req-3636cf32", "level": "info", "ts": "2026-04-20T09:50:04.247986Z"}
{"service": "api", "payload": {"message_preview": "How should alerts be designed?"}, "event": "request_received", "user_id_hash": "105a9cef3903", "env": "dev", "feature": "qa", "session_id": "s10", "model": "claude-sonnet-4-5", "correlation_id": "req-0aac019f", "level": "info", "ts": "2026-04-20T09:50:04.254075Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 29, "tokens_out": 137, "cost_usd": 0.002142, "payload": {"answer_preview": "Alerts should be symptom-based with clear thresholds, severity levels, runbook l..."}, "event": "response_sent", "user_id_hash": "105a9cef3903", "env": "dev", "feature": "qa", "session_id": "s10", "model": "claude-sonnet-4-5", "correlation_id": "req-0aac019f", "level": "info", "ts": "2026-04-20T09:50:04.413799Z"}
```

### A.3 Test `rag_slow`
```powershell
python scripts/inject_incident.py --scenario rag_slow
```
```log
200 {'ok': True, 'incidents': {'rag_slow': True, 'tool_fail': False, 'cost_spike': False}}
```

```powershell
python scripts/load_test.py --concurrency 5
```
```log
[200] req-7c5d1df5 | qa | 5334.2ms
[200] req-0baafca5 | qa | 5329.4ms
[200] req-257faf8e | qa | 13326.3ms
[200] req-c797a64f | summary | 13336.8ms
[200] req-632385b4 | qa | 13328.3ms
[200] req-7ca849c0 | summary | 13350.8ms
[200] req-c4327f7f | qa | 13350.2ms
[200] req-5974e738 | qa | 13320.8ms
[200] req-a88524d8 | qa | 13328.9ms
[200] req-02b6d855 | qa | 13332.9ms
```

```powershell
Get-Content .\data\logs.jsonl | Select-Object -Last 20
```
```log
{"service": "api", "payload": {"message_preview": "What is your refund policy? My email is [REDACTED_EMAIL]"}, "event": "request_received", "user_id_hash": "2055254ee30a", "env": "dev", "feature": "qa", "session_id": "s01", "model": "claude-sonnet-4-5", "correlation_id": "req-7c5d1df5", "level": "info", "ts": "2026-04-20T09:53:11.867425Z"}
{"service": "api", "latency_ms": 2650, "tokens_in": 37, "tokens_out": 119, "cost_usd": 0.001896, "payload": {"answer_preview": "Based on our documentation: Refunds are available within 7 days with proof of pu..."}, "event": "response_sent", "user_id_hash": "2055254ee30a", "env": "dev", "feature": "qa", "session_id": "s01", "model": "claude-sonnet-4-5", "correlation_id": "req-7c5d1df5", "level": "info", "ts": "2026-04-20T09:53:14.524470Z"}
{"service": "api", "payload": {"message_preview": "Explain why metrics traces and logs work together"}, "event": "request_received", "user_id_hash": "95b6504a8bd6", "env": "dev", "feature": "qa", "session_id": "s02", "model": "claude-sonnet-4-5", "correlation_id": "req-0baafca5", "level": "info", "ts": "2026-04-20T09:53:14.527514Z"}
{"service": "api", "latency_ms": 2650, "tokens_in": 33, "tokens_out": 130, "cost_usd": 0.002049, "payload": {"answer_preview": "Do not expose PII, passwords, or sensitive data in logs. Use sanitized summaries..."}, "event": "response_sent", "user_id_hash": "95b6504a8bd6", "env": "dev", "feature": "qa", "session_id": "s02", "model": "claude-sonnet-4-5", "correlation_id": "req-0baafca5", "level": "info", "ts": "2026-04-20T09:53:17.182577Z"}
{"service": "api", "payload": {"message_preview": "Can I get help with policy and monitoring?"}, "event": "request_received", "user_id_hash": "75af07890985", "env": "dev", "feature": "qa", "session_id": "s04", "model": "claude-sonnet-4-5", "correlation_id": "req-257faf8e", "level": "info", "ts": "2026-04-20T09:53:17.193132Z"}
{"service": "api", "latency_ms": 2650, "tokens_in": 36, "tokens_out": 86, "cost_usd": 0.001398, "payload": {"answer_preview": "Based on our documentation: Metrics detect incidents, traces localize them, logs..."}, "event": "response_sent", "user_id_hash": "75af07890985", "env": "dev", "feature": "qa", "session_id": "s04", "model": "claude-sonnet-4-5", "correlation_id": "req-257faf8e", "level": "info", "ts": "2026-04-20T09:53:19.847207Z"}
{"service": "api", "payload": {"message_preview": "Summarize the monitoring policy for production logging"}, "event": "request_received", "user_id_hash": "97ce842ec69d", "env": "dev", "feature": "summary", "session_id": "s03", "model": "claude-sonnet-4-5", "correlation_id": "req-c797a64f", "level": "info", "ts": "2026-04-20T09:53:19.854880Z"}
{"service": "api", "latency_ms": 2668, "tokens_in": 40, "tokens_out": 171, "cost_usd": 0.002685, "payload": {"answer_preview": "Based on our documentation: Metrics detect incidents, traces localize them, logs..."}, "event": "response_sent", "user_id_hash": "97ce842ec69d", "env": "dev", "feature": "summary", "session_id": "s03", "model": "claude-sonnet-4-5", "correlation_id": "req-c797a64f", "level": "info", "ts": "2026-04-20T09:53:22.526964Z"}
{"service": "api", "payload": {"message_preview": "Here is my phone [REDACTED_PHONE_VN], what should be logged?"}, "event": "request_received", "user_id_hash": "64f6ec689229", "env": "dev", "feature": "qa", "session_id": "s05", "model": "claude-sonnet-4-5", "correlation_id": "req-632385b4", "level": "info", "ts": "2026-04-20T09:53:22.529538Z"}
{"service": "api", "latency_ms": 2651, "tokens_in": 34, "tokens_out": 126, "cost_usd": 0.001992, "payload": {"answer_preview": "Do not expose PII, passwords, or sensitive data in logs. Use sanitized summaries..."}, "event": "response_sent", "user_id_hash": "64f6ec689229", "env": "dev", "feature": "qa", "session_id": "s05", "model": "claude-sonnet-4-5", "correlation_id": "req-632385b4", "level": "info", "ts": "2026-04-20T09:53:25.186013Z"}
{"service": "api", "payload": {"message_preview": "Give me a short summary of the observability workflow"}, "event": "request_received", "user_id_hash": "4c4f62330d76", "env": "dev", "feature": "summary", "session_id": "s06", "model": "claude-sonnet-4-5", "correlation_id": "req-7ca849c0", "level": "info", "ts": "2026-04-20T09:53:25.200560Z"}
{"service": "api", "latency_ms": 2650, "tokens_in": 36, "tokens_out": 150, "cost_usd": 0.002358, "payload": {"answer_preview": "Metrics detect incidents, traces localize them, and logs explain the root cause...."}, "event": "response_sent", "user_id_hash": "4c4f62330d76", "env": "dev", "feature": "summary", "session_id": "s06", "model": "claude-sonnet-4-5", "correlation_id": "req-7ca849c0", "level": "info", "ts": "2026-04-20T09:53:27.872382Z"}
{"service": "api", "payload": {"message_preview": "What should not appear in app logs?"}, "event": "request_received", "user_id_hash": "1632c29ecdec", "env": "dev", "feature": "qa", "session_id": "s07", "model": "claude-sonnet-4-5", "correlation_id": "req-c4327f7f", "level": "info", "ts": "2026-04-20T09:53:27.876119Z"}
{"service": "api", "latency_ms": 2651, "tokens_in": 30, "tokens_out": 154, "cost_usd": 0.0024, "payload": {"answer_preview": "Do not expose PII, passwords, or sensitive data in logs. Use sanitized summaries..."}, "event": "response_sent", "user_id_hash": "1632c29ecdec", "env": "dev", "feature": "qa", "session_id": "s07", "model": "claude-sonnet-4-5", "correlation_id": "req-c4327f7f", "level": "info", "ts": "2026-04-20T09:53:30.530691Z"}
{"service": "api", "payload": {"message_preview": "What is the policy for PII and credit card [REDACTED_CREDIT_CARD]?"}, "event": "request_received", "user_id_hash": "4d14d5d4f719", "env": "dev", "feature": "qa", "session_id": "s09", "model": "claude-sonnet-4-5", "correlation_id": "req-a88524d8", "level": "info", "ts": "2026-04-20T09:53:30.544031Z"}
{"service": "api", "latency_ms": 2651, "tokens_in": 37, "tokens_out": 98, "cost_usd": 0.001581, "payload": {"answer_preview": "Based on our documentation: Do not expose PII in logs. Use sanitized summaries o..."}, "event": "response_sent", "user_id_hash": "4d14d5d4f719", "env": "dev", "feature": "qa", "session_id": "s09", "model": "claude-sonnet-4-5", "correlation_id": "req-a88524d8", "level": "info", "ts": "2026-04-20T09:53:33.199806Z"}
{"service": "api", "payload": {"message_preview": "How do I debug tail latency?"}, "event": "request_received", "user_id_hash": "2f015d970c0b", "env": "dev", "feature": "qa", "session_id": "s08", "model": "claude-sonnet-4-5", "correlation_id": "req-02b6d855", "level": "info", "ts": "2026-04-20T09:53:33.201644Z"}
{"service": "api", "latency_ms": 2652, "tokens_in": 28, "tokens_out": 89, "cost_usd": 0.001419, "payload": {"answer_preview": "To debug tail latency, compare P50/P95/P99 in metrics, find the slow span in tra..."}, "event": "response_sent", "user_id_hash": "2f015d970c0b", "env": "dev", "feature": "qa", "session_id": "s08", "model": "claude-sonnet-4-5", "correlation_id": "req-02b6d855", "level": "info", "ts": "2026-04-20T09:53:35.859219Z"}
{"service": "api", "payload": {"message_preview": "How should alerts be designed?"}, "event": "request_received", "user_id_hash": "105a9cef3903", "env": "dev", "feature": "qa", "session_id": "s10", "model": "claude-sonnet-4-5", "correlation_id": "req-5974e738", "level": "info", "ts": "2026-04-20T09:53:35.862580Z"}
{"service": "api", "latency_ms": 2651, "tokens_in": 29, "tokens_out": 124, "cost_usd": 0.001947, "payload": {"answer_preview": "Alerts should be symptom-based with clear thresholds, severity levels, runbook l..."}, "event": "response_sent", "user_id_hash": "105a9cef3903", "env": "dev", "feature": "qa", "session_id": "s10", "model": "claude-sonnet-4-5", "correlation_id": "req-5974e738", "level": "info", "ts": "2026-04-20T09:53:38.519351Z"}
```

```powershell
python scripts/inject_incident.py --scenario rag_slow --disable
```

### A.4 Test `tool_fail`
```powershell
python scripts/inject_incident.py --scenario tool_fail
```
```log
200 {'ok': True, 'incidents': {'rag_slow': False, 'tool_fail': True, 'cost_spike': False}}
```

```powershell
python scripts/load_test.py --concurrency 1
```
```log
[500] None | qa | 30.7ms
[500] None | qa | 15.4ms
[500] None | summary | 11.9ms
[500] None | qa | 11.7ms
[500] None | qa | 11.0ms
[500] None | summary | 12.8ms
[500] None | qa | 8.9ms
[500] None | qa | 15.1ms
[500] None | qa | 19.1ms
[500] None | qa | 11.5ms
```

```powershell
Get-Content .\data\logs.jsonl | Select-Object -Last 20
```
```log
{"service": "api", "payload": {"message_preview": "What is your refund policy? My email is [REDACTED_EMAIL]"}, "event": "request_received", "user_id_hash": "2055254ee30a", "env": "dev", "feature": "qa", "session_id": "s01", "model": "claude-sonnet-4-5", "correlation_id": "req-d7c992d0", "level": "info", "ts": "2026-04-20T09:55:23.571855Z"}
{"service": "api", "error_type": "RuntimeError", "payload": {"detail": "Vector store timeout", "message_preview": "What is your refund policy? My email is [REDACTED_EMAIL]"}, "event": "request_failed", "user_id_hash": "2055254ee30a", "env": "dev", "feature": "qa", "session_id": "s01", "model": "claude-sonnet-4-5", "correlation_id": "req-d7c992d0", "level": "error", "ts": "2026-04-20T09:55:23.576619Z"}
{"service": "api", "payload": {"message_preview": "Explain why metrics traces and logs work together"}, "event": "request_received", "user_id_hash": "95b6504a8bd6", "env": "dev", "feature": "qa", "session_id": "s02", "model": "claude-sonnet-4-5", "correlation_id": "req-f42684ed", "level": "info", "ts": "2026-04-20T09:55:23.587076Z"}
{"service": "api", "error_type": "RuntimeError", "payload": {"detail": "Vector store timeout", "message_preview": "Explain why metrics traces and logs work together"}, "event": "request_failed", "user_id_hash": "95b6504a8bd6", "env": "dev", "feature": "qa", "session_id": "s02", "model": "claude-sonnet-4-5", "correlation_id": "req-f42684ed", "level": "error", "ts": "2026-04-20T09:55:23.591544Z"}
{"service": "api", "payload": {"message_preview": "Summarize the monitoring policy for production logging"}, "event": "request_received", "user_id_hash": "97ce842ec69d", "env": "dev", "feature": "summary", "session_id": "s03", "model": "claude-sonnet-4-5", "correlation_id": "req-ebf7e445", "level": "info", "ts": "2026-04-20T09:55:23.602052Z"}
{"service": "api", "error_type": "RuntimeError", "payload": {"detail": "Vector store timeout", "message_preview": "Summarize the monitoring policy for production logging"}, "event": "request_failed", "user_id_hash": "97ce842ec69d", "env": "dev", "feature": "summary", "session_id": "s03", "model": "claude-sonnet-4-5", "correlation_id": "req-ebf7e445", "level": "error", "ts": "2026-04-20T09:55:23.605356Z"}
{"service": "api", "payload": {"message_preview": "Can I get help with policy and monitoring?"}, "event": "request_received", "user_id_hash": "75af07890985", "env": "dev", "feature": "qa", "session_id": "s04", "model": "claude-sonnet-4-5", "correlation_id": "req-c32a19a7", "level": "info", "ts": "2026-04-20T09:55:23.615222Z"}
{"service": "api", "error_type": "RuntimeError", "payload": {"detail": "Vector store timeout", "message_preview": "Can I get help with policy and monitoring?"}, "event": "request_failed", "user_id_hash": "75af07890985", "env": "dev", "feature": "qa", "session_id": "s04", "model": "claude-sonnet-4-5", "correlation_id": "req-c32a19a7", "level": "error", "ts": "2026-04-20T09:55:23.620329Z"}{"service": "api", "payload": {"message_preview": "Here is my phone [REDACTED_PHONE_VN], what should be logged?"}, "event": "request_received", "user_id_hash": "64f6ec689229", "env": "dev", "feature": "qa", "session_id": "s05", "model": "claude-sonnet-4-5", "correlation_id": "req-e2992af8", "level": "info", "ts": "2026-04-20T09:55:23.628479Z"}
{"service": "api", "error_type": "RuntimeError", "payload": {"detail": "Vector store timeout", "message_preview": "Here is my phone [REDACTED_PHONE_VN], what should be logged?"}, "event": "request_failed", "user_id_hash": "64f6ec689229", "env": "dev", "feature": "qa", "session_id": "s05", "model": "claude-sonnet-4-5", "correlation_id": "req-e2992af8", "level": "error", "ts": "2026-04-20T09:55:23.631759Z"}
{"service": "api", "payload": {"message_preview": "Give me a short summary of the observability workflow"}, "event": "request_received", "user_id_hash": "4c4f62330d76", "env": "dev", "feature": "summary", "session_id": "s06", "model": "claude-sonnet-4-5", "correlation_id": "req-7dec43da", "level": "info", "ts": "2026-04-20T09:55:23.639063Z"}
{"service": "api", "error_type": "RuntimeError", "payload": {"detail": "Vector store timeout", "message_preview": "Give me a short summary of the observability workflow"}, "event": "request_failed", "user_id_hash": "4c4f62330d76", "env": "dev", "feature": "summary", "session_id": "s06", "model": "claude-sonnet-4-5", "correlation_id": "req-7dec43da", "level": "error", "ts": "2026-04-20T09:55:23.642331Z"}
{"service": "api", "payload": {"message_preview": "What should not appear in app logs?"}, "event": "request_received", "user_id_hash": "1632c29ecdec", "env": "dev", "feature": "qa", "session_id": "s07", "model": "claude-sonnet-4-5", "correlation_id": "req-ca7134f5", "level": "info", "ts": "2026-04-20T09:55:23.651248Z"}
{"service": "api", "error_type": "RuntimeError", "payload": {"detail": "Vector store timeout", "message_preview": "What should not appear in app logs?"}, "event": "request_failed", "user_id_hash": "1632c29ecdec", "env": "dev", "feature": "qa", "session_id": "s07", "model": "claude-sonnet-4-5", "correlation_id": "req-ca7134f5", "level": "error", "ts": "2026-04-20T09:55:23.653626Z"}
{"service": "api", "payload": {"message_preview": "How do I debug tail latency?"}, "event": "request_received", "user_id_hash": "2f015d970c0b", "env": "dev", "feature": "qa", "session_id": "s08", "model": "claude-sonnet-4-5", "correlation_id": "req-f76e7651", "level": "info", "ts": "2026-04-20T09:55:23.662289Z"}
{"service": "api", "error_type": "RuntimeError", "payload": {"detail": "Vector store timeout", "message_preview": "How do I debug tail latency?"}, "event": "request_failed", "user_id_hash": "2f015d970c0b", "env": "dev", "feature": "qa", "session_id": "s08", "model": "claude-sonnet-4-5", "correlation_id": "req-f76e7651", "level": "error", "ts": "2026-04-20T09:55:23.668717Z"}
{"service": "api", "payload": {"message_preview": "What is the policy for PII and credit card [REDACTED_CREDIT_CARD]?"}, "event": "request_received", "user_id_hash": "4d14d5d4f719", "env": "dev", "feature": "qa", "session_id": "s09", "model": "claude-sonnet-4-5", "correlation_id": "req-8bb3b9d6", "level": "info", "ts": "2026-04-20T09:55:23.678733Z"}
{"service": "api", "error_type": "RuntimeError", "payload": {"detail": "Vector store timeout", "message_preview": "What is the policy for PII and credit card [REDACTED_CREDIT_CARD]?"}, "event": "request_failed", "user_id_hash": "4d14d5d4f719", "env": "dev", "feature": "qa", "session_id": "s09", "model": "claude-sonnet-4-5", "correlation_id": "req-8bb3b9d6", "level": "error", "ts": "2026-04-20T09:55:23.685656Z"}
{"service": "api", "payload": {"message_preview": "How should alerts be designed?"}, "event": "request_received", "user_id_hash": "105a9cef3903", "env": "dev", "feature": "qa", "session_id": "s10", "model": "claude-sonnet-4-5", "correlation_id": "req-90127f9d", "level": "info", "ts": "2026-04-20T09:55:23.696445Z"}
{"service": "api", "error_type": "RuntimeError", "payload": {"detail": "Vector store timeout", "message_preview": "How should alerts be designed?"}, "event": "request_failed", "user_id_hash": "105a9cef3903", "env": "dev", "feature": "qa", "session_id": "s10", "model": "claude-sonnet-4-5", "correlation_id": "req-90127f9d", "level": "error", "ts": "2026-04-20T09:55:23.701262Z"}
```

```powershell
python scripts/inject_incident.py --scenario tool_fail --disable
```

### A.5 Test `cost_spike`
```powershell
python scripts/inject_incident.py --scenario cost_spike
```
```log
200 {'ok': True, 'incidents': {'rag_slow': False, 'tool_fail': False, 'cost_spike': True}}
```

```powershell
python scripts/load_test.py --concurrency 1
```
```log
[200] req-1d035d2d | qa | 168.7ms
[200] req-368f1eb6 | qa | 161.9ms
[200] req-9f2d9cad | summary | 160.5ms
[200] req-0179e0ae | qa | 160.9ms
[200] req-91f5179a | qa | 171.6ms
[200] req-b9b02e12 | summary | 161.6ms
[200] req-d8ab764b | qa | 165.8ms
[200] req-d2446706 | qa | 168.3ms
[200] req-a1200b48 | qa | 169.5ms
[200] req-906f7bd9 | qa | 161.0ms
```

```powershell
Get-Content .\data\logs.jsonl | Select-Object -Last 20
```
```log
{"service": "api", "payload": {"message_preview": "What is your refund policy? My email is [REDACTED_EMAIL]"}, "event": "request_received", "user_id_hash": "2055254ee30a", "env": "dev", "feature": "qa", "session_id": "s01", "model": "claude-sonnet-4-5", "correlation_id": "req-1d035d2d", "level": "info", "ts": "2026-04-20T09:56:41.570723Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 37, "tokens_out": 628, "cost_usd": 0.009531, "payload": {"answer_preview": "Based on our documentation: Refunds are available within 7 days with proof of pu..."}, "event": "response_sent", "user_id_hash": "2055254ee30a", "env": "dev", "feature": "qa", "session_id": "s01", "model": "claude-sonnet-4-5", "correlation_id": "req-1d035d2d", "level": "info", "ts": "2026-04-20T09:56:41.724374Z"}
{"service": "api", "payload": {"message_preview": "Explain why metrics traces and logs work together"}, "event": "request_received", "user_id_hash": "95b6504a8bd6", "env": "dev", "feature": "qa", "session_id": "s02", "model": "claude-sonnet-4-5", "correlation_id": "req-368f1eb6", "level": "info", "ts": "2026-04-20T09:56:41.734782Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 33, "tokens_out": 516, "cost_usd": 0.007839, "payload": {"answer_preview": "Do not expose PII, passwords, or sensitive data in logs. Use sanitized summaries..."}, "event": "response_sent", "user_id_hash": "95b6504a8bd6", "env": "dev", "feature": "qa", "session_id": "s02", "model": "claude-sonnet-4-5", "correlation_id": "req-368f1eb6", "level": "info", "ts": "2026-04-20T09:56:41.889120Z"}
{"service": "api", "payload": {"message_preview": "Summarize the monitoring policy for production logging"}, "event": "request_received", "user_id_hash": "97ce842ec69d", "env": "dev", "feature": "summary", "session_id": "s03", "model": "claude-sonnet-4-5", "correlation_id": "req-9f2d9cad", "level": "info", "ts": "2026-04-20T09:56:41.896151Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 40, "tokens_out": 380, "cost_usd": 0.00582, "payload": {"answer_preview": "Based on our documentation: Metrics detect incidents, traces localize them, logs..."}, "event": "response_sent", "user_id_hash": "97ce842ec69d", "env": "dev", "feature": "summary", "session_id": "s03", "model": "claude-sonnet-4-5", "correlation_id": "req-9f2d9cad", "level": "info", "ts": "2026-04-20T09:56:42.049757Z"}
{"service": "api", "payload": {"message_preview": "Can I get help with policy and monitoring?"}, "event": "request_received", "user_id_hash": "75af07890985", "env": "dev", "feature": "qa", "session_id": "s04", "model": "claude-sonnet-4-5", "correlation_id": "req-0179e0ae", "level": "info", "ts": "2026-04-20T09:56:42.057263Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 36, "tokens_out": 532, "cost_usd": 0.008088, "payload": {"answer_preview": "Based on our documentation: Metrics detect incidents, traces localize them, logs..."}, "event": "response_sent", "user_id_hash": "75af07890985", "env": "dev", "feature": "qa", "session_id": "s04", "model": "claude-sonnet-4-5", "correlation_id": "req-0179e0ae", "level": "info", "ts": "2026-04-20T09:56:42.211463Z"}
{"service": "api", "payload": {"message_preview": "Here is my phone [REDACTED_PHONE_VN], what should be logged?"}, "event": "request_received", "user_id_hash": "64f6ec689229", "env": "dev", "feature": "qa", "session_id": "s05", "model": "claude-sonnet-4-5", "correlation_id": "req-91f5179a", "level": "info", "ts": "2026-04-20T09:56:42.219105Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 34, "tokens_out": 716, "cost_usd": 0.010842, "payload": {"answer_preview": "Do not expose PII, passwords, or sensitive data in logs. Use sanitized summaries..."}, "event": "response_sent", "user_id_hash": "64f6ec689229", "env": "dev", "feature": "qa", "session_id": "s05", "model": "claude-sonnet-4-5", "correlation_id": "req-91f5179a", "level": "info", "ts": "2026-04-20T09:56:42.373671Z"}
{"service": "api", "payload": {"message_preview": "Give me a short summary of the observability workflow"}, "event": "request_received", "user_id_hash": "4c4f62330d76", "env": "dev", "feature": "summary", "session_id": "s06", "model": "claude-sonnet-4-5", "correlation_id": "req-b9b02e12", "level": "info", "ts": "2026-04-20T09:56:42.392199Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 36, "tokens_out": 504, "cost_usd": 0.007668, "payload": {"answer_preview": "Metrics detect incidents, traces localize them, and logs explain the root cause...."}, "event": "response_sent", "user_id_hash": "4c4f62330d76", "env": "dev", "feature": "summary", "session_id": "s06", "model": "claude-sonnet-4-5", "correlation_id": "req-b9b02e12", "level": "info", "ts": "2026-04-20T09:56:42.546213Z"}
{"service": "api", "payload": {"message_preview": "What should not appear in app logs?"}, "event": "request_received", "user_id_hash": "1632c29ecdec", "env": "dev", "feature": "qa", "session_id": "s07", "model": "claude-sonnet-4-5", "correlation_id": "req-d8ab764b", "level": "info", "ts": "2026-04-20T09:56:42.554235Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 30, "tokens_out": 364, "cost_usd": 0.00555, "payload": {"answer_preview": "Do not expose PII, passwords, or sensitive data in logs. Use sanitized summaries..."}, "event": "response_sent", "user_id_hash": "1632c29ecdec", "env": "dev", "feature": "qa", "session_id": "s07", "model": "claude-sonnet-4-5", "correlation_id": "req-d8ab764b", "level": "info", "ts": "2026-04-20T09:56:42.710811Z"}
{"service": "api", "payload": {"message_preview": "How do I debug tail latency?"}, "event": "request_received", "user_id_hash": "2f015d970c0b", "env": "dev", "feature": "qa", "session_id": "s08", "model": "claude-sonnet-4-5", "correlation_id": "req-d2446706", "level": "info", "ts": "2026-04-20T09:56:42.718588Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 28, "tokens_out": 640, "cost_usd": 0.009684, "payload": {"answer_preview": "To debug tail latency, compare P50/P95/P99 in metrics, find the slow span in tra..."}, "event": "response_sent", "user_id_hash": "2f015d970c0b", "env": "dev", "feature": "qa", "session_id": "s08", "model": "claude-sonnet-4-5", "correlation_id": "req-d2446706", "level": "info", "ts": "2026-04-20T09:56:42.876796Z"}
{"service": "api", "payload": {"message_preview": "What is the policy for PII and credit card [REDACTED_CREDIT_CARD]?"}, "event": "request_received", "user_id_hash": "4d14d5d4f719", "env": "dev", "feature": "qa", "session_id": "s09", "model": "claude-sonnet-4-5", "correlation_id": "req-a1200b48", "level": "info", "ts": "2026-04-20T09:56:42.891773Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 37, "tokens_out": 532, "cost_usd": 0.008091, "payload": {"answer_preview": "Based on our documentation: Do not expose PII in logs. Use sanitized summaries o..."}, "event": "response_sent", "user_id_hash": "4d14d5d4f719", "env": "dev", "feature": "qa", "session_id": "s09", "model": "claude-sonnet-4-5", "correlation_id": "req-a1200b48", "level": "info", "ts": "2026-04-20T09:56:43.048678Z"}
{"service": "api", "payload": {"message_preview": "How should alerts be designed?"}, "event": "request_received", "user_id_hash": "105a9cef3903", "env": "dev", "feature": "qa", "session_id": "s10", "model": "claude-sonnet-4-5", "correlation_id": "req-906f7bd9", "level": "info", "ts": "2026-04-20T09:56:43.056778Z"}
{"service": "api", "latency_ms": 150, "tokens_in": 29, "tokens_out": 488, "cost_usd": 0.007407, "payload": {"answer_preview": "Alerts should be symptom-based with clear thresholds, severity levels, runbook l..."}, "event": "response_sent", "user_id_hash": "105a9cef3903", "env": "dev", "feature": "qa", "session_id": "s10", "model": "claude-sonnet-4-5", "correlation_id": "req-906f7bd9", "level": "info", "ts": "2026-04-20T09:56:43.211516Z"}
```

```powershell
python scripts/inject_incident.py --scenario cost_spike --disable
```