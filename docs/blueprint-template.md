# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata
- [GROUP_NAME]: Team 6
- [REPO_URL]: https://github.com/West2light/Lab13-E403-Team06-Observability
- [MEMBERS]: Vương Hoàng Giang, Dương Quang Đông, Phạm Anh Dũng, Nguyễn Lê Trung
  - Member A: Nguyễn Lê Trung | Role: Logging & PII
  - Member B: Nguyễn Lê Trung | Role: Tracing & Enrichment
  - Member C: Phạm Anh Dũng | Role: SLO & Alerts
  - Member D: Dương Quang Đông | Role: Load Test & Dashboard
  - Member E: Vương Hoàng Giang | Role: Demo & Report

---

## 2. Group Performance (Auto-Verified)
```
- [VALIDATE_LOGS_FINAL_SCORE]: 100/100
- [TOTAL_TRACES_COUNT]: 271
- [PII_LEAKS_FOUND]: 0
```
---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
```
- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: ![correlation_id.png](https://github.com/West2light/Lab13-E403-Team06-Observability/blob/main/correlation_id.png)
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: ![pii_redaction.png](https://github.com/West2light/Lab13-E403-Team06-Observability/blob/main/pii_redaction.png)
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: ![trace_waterfall.png](https://github.com/West2light/Lab13-E403-Team06-Observability/blob/main/trace_waterfall.png)
- [TRACE_WATERFALL_EXPLANATION]: Span `run` bao phủ toàn bộ pipeline agent gồm RAG retrieval
  và LLM generation, hoàn thành trong 0.16s ở điều kiện bình thường. Khi kích hoạt incident
  rag_slow, span này kéo dài lên ~2.65s do bị delay cưỡng bức 2.5s ở bước retrieval, trở
  thành span chiếm thời gian lớn nhất trong waterfall.
```

### 3.2 Dashboard & SLOs
```
- [DASHBOARD_6_PANELS_SCREENSHOT]: ![dashboard_6panels.png](https://github.com/West2light/Lab13-E403-Team06-Observability/blob/main/dashboard_6panels.png)
```
- [SLO_TABLE]:

  | SLI | Target | Window | Current Value |
  |---|---:|---|---:|
  | Latency P95 | < 3000ms | 28d | 156ms |
  | Error Rate | < 2% | 28d | 0.0% |
  | Cost Budget | < $2.5/day | 1d | $0.024/day |

### 3.3 Alerts & Runbook
```
- [ALERT_RULES_SCREENSHOT]: ![alert_rules.png](https://github.com/West2light/Lab13-E403-Team06-Observability/blob/main/alert_rules.png)
- [SAMPLE_RUNBOOK_LINK]: docs/alerts.md#1-high-latency-p95
```
---

## 4. Incident Response (Group)
```
- [SCENARIO_NAME]: rag_slow
- [SYMPTOMS_OBSERVED]: Latency P95 tăng từ ~156ms lên ~2651ms, vượt ngưỡng SLO 3000ms. Tất
  cả request đều bị chậm đồng loạt, không có lỗi HTTP nhưng response time tăng gấp 17 lần.
- [ROOT_CAUSE_PROVED_BY]: Log line correlation_id=req-a802381a cho thấy latency_ms=2651 tại
  ts=2026-04-20T09:47:22. Span `run` trên Langfuse kéo dài 2.65s, xác nhận bottleneck nằm ở
  bước RAG retrieval (mock_rag.py sleep 2.5s khi STATE["rag_slow"]=True).
- [FIX_ACTION]: Tắt incident bằng lệnh `python scripts/inject_incident.py --scenario rag_slow
  --disable`. Latency trở về ~155ms ngay sau đó.
- [PREVENTIVE_MEASURE]: Đặt timeout cho RAG retrieval, thêm circuit breaker khi latency vượt
  ngưỡng, và alert tự động khi P95 > 5000ms trong 30 phút liên tiếp (đã định nghĩa trong
  config/alert_rules.yaml).
```
---

## 5. Individual Contributions & Evidence

### [Nguyễn Lê Trung] — Member A: Logging & PII
- [TASKS_COMPLETED]:
  - Implement `CorrelationIdMiddleware` (`app/middleware.py`): sinh `x-request-id` duy nhất cho mỗi request (lấy từ header hoặc tự sinh `req-{uuid8}`), bind vào structlog context để tất cả log trong request tự động mang `correlation_id`, trả về header `x-request-id` và `x-response-time-ms` trong response.
  - Implement PII scrubber (`app/pii.py`): 15 regex pattern bao phủ email, phone VN, CCCD, CMND, credit card, passport, MST, số tài khoản, BHXH, BHYT, GPLX, biển số xe, ngày sinh, IP, địa chỉ; hàm `scrub_text()` thay thế bằng `[REDACTED_<TYPE>]`, `summarize_text()` kết hợp scrub + truncate, `hash_user_id()` dùng SHA-256.
  - Cấu hình structlog pipeline (`app/logging_config.py`): gắn `scrub_event` processor vào chain để tự động scrub PII trong mọi log, `JsonlFileProcessor` ghi song song ra `data/logs.jsonl`, đảm bảo output JSON đúng schema `config/logging_schema.json`.
  - Enrich log context (`app/main.py`): `bind_contextvars` với `user_id_hash`, `session_id`, `feature`, `model`, `env` cho mỗi request; thêm `load_dotenv()` để app load đúng biến môi trường khi khởi động.
- [EVIDENCE_LINK]: [app/middleware.py](../app/middleware.py), [app/pii.py](../app/pii.py), [app/logging_config.py](../app/logging_config.py), [app/main.py](../app/main.py), https://github.com/West2light/Lab13-E403-Team06-Observability/commit/77c8b42a1d54b8ddb74f3a7cbf38aa3c6e993dd5

### [Nguyễn Lê Trung] — Member B: Tracing & Enrichment
- [TASKS_COMPLETED]:
  - Adapt `app/tracing.py` tương thích Langfuse SDK v3: thay `langfuse.decorators` (SDK v2) bằng `from langfuse import observe, get_client`; implement `_LangfuseContext` wrapper map `update_current_trace` → `update_current_span` và `update_current_observation` → `update_current_generation` để giữ nguyên interface cho `agent.py`.
  - Đảm bảo `@observe()` decorator trên `LabAgent.run()` (`app/agent.py`) gửi trace lên Langfuse với đầy đủ tags `["lab", feature, model]`, metadata RAG (`doc_count`, `query_preview`), và `usage_details` token.
  - Debug và fix lỗi 500 do API breaking change của Langfuse SDK v3 (`update_current_trace`, `update_current_observation` không còn tồn tại).
  - Xác nhận `tracing_enabled: true` qua `/health` endpoint và verify 20+ traces xuất hiện trên Langfuse cloud dashboard.
- [EVIDENCE_LINK]: [app/tracing.py](../app/tracing.py), [app/agent.py](../app/agent.py), https://github.com/West2light/Lab13-E403-Team06-Observability/commit/63f714fdb9c64bd5246e27587e6731d328ea2aa9

### [Phạm Anh Dũng]
- [TASKS_COMPLETED]: Định nghĩa SLO/SLI cho latency P95, error rate, daily cost budget và quality score; thiết kế alert rules symptom-based cho `high_latency_p95`, `high_error_rate`, `cost_budget_spike`; liên kết alert với dashboard panel, runbook và incident lab tương ứng; viết runbook điều tra theo luồng metrics -> traces -> logs bằng `correlation_id`; chuẩn bị evidence cho phần Alerts & Runbook của group report.
- [EVIDENCE_LINK]: [docs/C_report.md](C_report.md), [docs/alerts.md](alerts.md), [config/slo.yaml](../config/slo.yaml), [config/alert_rules.yaml](../config/alert_rules.yaml), https://github.com/West2light/Lab13-E403-Team06-Observability/commit/2aac768d9d1b8aa06d821a1f375df04ce7bf1db3

### Dương Quang Đông
- [TASKS_COMPLETED]: Executed baseline load testing and incident injection for `rag_slow`,
  `tool_fail`, and `cost_spike`; collected terminal output and structured log evidence from
  `data/logs.jsonl`; compared latency, error, token, and cost behavior across scenarios;
  prepared evidence for dashboard and incident response analysis.
- [EVIDENCE_LINK]: https://github.com/West2light/Lab13-E403-Team06-Observability/commit/256e28f7105d69632eca796563e68893fd110c8e, [docs/D_report.md](docs/D_report.md)

### [Vương Hoàng Giang]
- [TASKS_COMPLETED]: Xây dựng in-memory metrics helpers (app/metrics.py) với các hàm
  record_request, snapshot, percentile; viết dashboard-spec.md định nghĩa 6 panel; thu thập
  evidence chấm điểm (docs/grading-evidence.md); xây dựng dashboard HTML 6 panel tự động
  refresh từ /metrics endpoint (scripts/dashboard.html); hoàn thiện báo cáo
  blueprint-template.md; chạy load test và inject incident rag_slow để lấy evidence; chạy
  validate_logs.py đạt 100/100.
- [EVIDENCE_LINK]: https://github.com/VinUni-AI20k/Lab13-Observability/commit/97117795181b0267da86e6806b87e67069340e62, https://github.com/VinUni-AI20k/Lab13-Observability/commit/02e95f442e5440d56da387092e404f4c56c321b4

---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: (Description + Evidence)
- [BONUS_AUDIT_LOGS]: (Description + Evidence)
- [BONUS_CUSTOM_METRIC]: (Description + Evidence)
