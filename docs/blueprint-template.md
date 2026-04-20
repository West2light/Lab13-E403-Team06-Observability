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
- [VALIDATE_LOGS_FINAL_SCORE]: 100/100
- [TOTAL_TRACES_COUNT]: 271
- [PII_LEAKS_FOUND]: 0

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: ![correlation_id.png](https://github.com/West2light/Lab13-E403-Team06-Observability/blob/main/correlation_id.png)
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: ![pii_redaction.png](https://github.com/West2light/Lab13-E403-Team06-Observability/blob/main/pii_redaction.png)
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: ![trace_waterfall.png](https://github.com/West2light/Lab13-E403-Team06-Observability/blob/main/trace_waterfall.png)
- [TRACE_WATERFALL_EXPLANATION]: Span `run` bao phủ toàn bộ pipeline agent gồm RAG retrieval và LLM generation, hoàn thành trong 0.16s ở điều kiện bình thường. Khi kích hoạt incident rag_slow, span này kéo dài lên ~2.65s do bị delay cưỡng bức 2.5s ở bước retrieval, trở thành span chiếm thời gian lớn nhất trong waterfall.

### 3.2 Dashboard & SLOs
- [DASHBOARD_6_PANELS_SCREENSHOT]: ![dashboard_6panels.png](https://github.com/West2light/Lab13-E403-Team06-Observability/blob/main/dashboard_6panels.png)
- [SLO_TABLE]:
| SLI | Target | Window | Current Value |
|---|---:|---|---:|
| Latency P95 | < 3000ms | 28d | 156ms |
| Error Rate | < 2% | 28d | 0.0% |
| Cost Budget | < $2.5/day | 1d | $0.024/day |

### 3.3 Alerts & Runbook
- [ALERT_RULES_SCREENSHOT]: ![alert_rules.png](https://github.com/West2light/Lab13-E403-Team06-Observability/blob/main/alert_rules.png)
- [SAMPLE_RUNBOOK_LINK]: docs/alerts.md#1-high-latency-p95

---

## 4. Incident Response (Group)
- [SCENARIO_NAME]: rag_slow
- [SYMPTOMS_OBSERVED]: Latency P95 tăng từ ~156ms lên ~2651ms, vượt ngưỡng SLO 3000ms. Tất cả request đều bị chậm đồng loạt, không có lỗi HTTP nhưng response time tăng gấp 17 lần.
- [ROOT_CAUSE_PROVED_BY]: Log line correlation_id=req-a802381a cho thấy latency_ms=2651 tại ts=2026-04-20T09:47:22. Span `run` trên Langfuse kéo dài 2.65s, xác nhận bottleneck nằm ở bước RAG retrieval (mock_rag.py sleep 2.5s khi STATE["rag_slow"]=True).
- [FIX_ACTION]: Tắt incident bằng lệnh `python scripts/inject_incident.py --scenario rag_slow --disable`. Latency trở về ~155ms ngay sau đó.
- [PREVENTIVE_MEASURE]: Đặt timeout cho RAG retrieval, thêm circuit breaker khi latency vượt ngưỡng, và alert tự động khi P95 > 5000ms trong 30 phút liên tiếp (đã định nghĩa trong config/alert_rules.yaml).

---

## 5. Individual Contributions & Evidence

### [MEMBER_A_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: (Link to specific commit or PR)

### [MEMBER_B_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: 

### [MEMBER_C_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: 

### [MEMBER_D_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: 

### [MEMBER_E_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: 

---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: (Description + Evidence)
- [BONUS_AUDIT_LOGS]: (Description + Evidence)
- [BONUS_CUSTOM_METRIC]: (Description + Evidence)
