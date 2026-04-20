# Member C Report - SLO & Alerts

## 1. Thông tin member

- **Member**: Phạm Anh Dũng
- **Vai trò**: SLO & Alerts
- **File chính**:
  - [config/slo.yaml](../config/slo.yaml)
  - [config/alert_rules.yaml](../config/alert_rules.yaml)
  - [docs/alerts.md](alerts.md)
  - [scripts/dashboard.html](../scripts/dashboard.html)
- **Ngữ cảnh triển khai hỗ trợ**:
  - SLO được định nghĩa tập trung trong [config/slo.yaml](../config/slo.yaml).
  - Alert rules được định nghĩa trong [config/alert_rules.yaml](../config/alert_rules.yaml) và trỏ về runbook tại [docs/alerts.md](alerts.md).
  - Dashboard 6 panel đọc dữ liệu từ endpoint `/metrics` trong [scripts/dashboard.html](../scripts/dashboard.html).
  - Evidence vận hành và incident injection được đối chiếu với [docs/D_report.md](D_report.md).

## 2. Phạm vi công việc Role C

Công việc của Member C tập trung vào việc biến dữ liệu observability thành mục tiêu vận hành có thể đo được và cảnh báo có thể hành động được. Các trách nhiệm chính gồm:

1. Định nghĩa SLO/SLI cho latency, error rate, cost và quality.
2. Thiết kế alert rules theo hướng symptom-based để tránh cảnh báo nhiễu.
3. Liên kết từng alert với dashboard panel, runbook và incident lab tương ứng.
4. Viết runbook điều tra theo luồng metrics -> traces -> logs với `correlation_id`.
5. Chuẩn bị nội dung có thể đưa vào phần Dashboard & SLOs, Alerts & Runbook và Individual Contributions của group report.

## 3. Thiết lập SLO

### 3.1 SLO được định nghĩa

| SLI | Mục tiêu | Cửa sổ | Alert liên quan | Panel dashboard |
|---|---:|---|---|---|
| Latency P95 | < 3000 ms | 28d | `high_latency_p95` | Latency P50/P95/P99 |
| Error Rate | < 2% | 28d | `high_error_rate` | Error rate with breakdown |
| Daily Cost Budget | < $2.50/day | 1d | `cost_budget_spike` | Cost over time |
| Average Quality Score | >= 0.75 | 28d | Không có alert trực tiếp | Quality proxy |

### 3.2 Lý do chọn SLO

- **Latency P95** bảo vệ trải nghiệm người dùng trước tail latency, không chỉ nhìn vào average latency.
- **Error Rate** theo dõi mức độ request thất bại và liên quan trực tiếp đến availability.
- **Daily Cost Budget** giúp phát hiện rủi ro token/model cost ngay cả khi request vẫn thành công.
- **Average Quality Score** là guardrail để tối ưu latency/cost nhưng không làm chất lượng câu trả lời tụt quá thấp.

## 4. Thiết kế alert rules

### 4.1 Alert: `high_latency_p95`

- **Severity**: P2
- **Trigger**: `latency_p95_ms > 5000 for 30m`
- **SLO liên quan**: Latency P95 < 3000 ms trong 28d
- **Incident lab liên quan**: `rag_slow`
- **Runbook**: [docs/alerts.md#1-high-latency-p95](alerts.md#1-high-latency-p95)

**Diễn giải**: Alert này phát hiện tình huống request vẫn trả về HTTP 200 nhưng người dùng phải chờ lâu. Với incident `rag_slow`, log evidence trong [docs/D_report.md](D_report.md) cho thấy server-side `latency_ms` tăng lên khoảng 2650 ms và client-observed latency dưới concurrency tăng lên khoảng 5.3s-13.3s.

### 4.2 Alert: `high_error_rate`

- **Severity**: P1
- **Trigger**: `error_rate_pct > 5 for 5m`
- **SLO liên quan**: Error Rate < 2% trong 28d
- **Incident lab liên quan**: `tool_fail`
- **Runbook**: [docs/alerts.md#2-high-error-rate](alerts.md#2-high-error-rate)

**Diễn giải**: Alert này có severity P1 vì lỗi trực tiếp làm request thất bại. Với incident `tool_fail`, evidence cho thấy request trả HTTP 500, log chuyển sang event `request_failed`, có `error_type="RuntimeError"` và detail `Vector store timeout`.

### 4.3 Alert: `cost_budget_spike`

- **Severity**: P2
- **Trigger**: `hourly_cost_usd > 2x_baseline for 15m`
- **SLO liên quan**: Daily Cost Budget < $2.50/day
- **Incident lab liên quan**: `cost_spike`
- **Runbook**: [docs/alerts.md#3-cost-budget-spike](alerts.md#3-cost-budget-spike)

**Diễn giải**: Alert này phát hiện bất thường chi phí khi hệ thống vẫn có vẻ khỏe theo latency và error rate. Với incident `cost_spike`, evidence cho thấy latency vẫn gần baseline nhưng `tokens_out` tăng lên khoảng 364-716 và `cost_usd` tăng lên khoảng $0.00555-$0.010842 mỗi request.

## 5. Runbook điều tra

Runbook trong [docs/alerts.md](alerts.md) dùng cùng một workflow cho cả ba alert:

1. **Metrics**: mở panel dashboard liên quan để xác nhận triệu chứng và ngưỡng.
2. **Traces**: mở trace chậm/lỗi/tốn chi phí để xác định span hoặc request bất thường.
3. **Logs**: dùng `correlation_id` để tìm JSON log tương ứng và xác nhận root cause.
4. **Mitigation**: áp dụng hành động giảm thiểu theo từng loại incident.
5. **Evidence**: lưu screenshot dashboard, trace waterfall và log line phục vụ báo cáo/demo.

## 6. Đối chiếu alert với incident evidence

| Incident | Alert cần kích hoạt | Tín hiệu chính | Kết luận vận hành |
|---|---|---|---|
| `rag_slow` | `high_latency_p95` | P95/tail latency tăng, request vẫn 200 | Cần điều tra RAG/tool span và giảm độ trễ |
| `tool_fail` | `high_error_rate` | HTTP 500, event `request_failed`, `RuntimeError` | Cần bypass/fallback tool hoặc rollback thay đổi gây lỗi |
| `cost_spike` | `cost_budget_spike` | `tokens_out` và `cost_usd` tăng, latency vẫn bình thường | Cần giới hạn output tokens, prompt/context hoặc model routing |

## 7. Kết luận

Member C đã hoàn thiện lớp SLO & Alerts cho hệ thống observability của lab. Bộ SLO bao phủ bốn rủi ro chính: chậm, lỗi, tăng chi phí và giảm chất lượng. Ba alert chính đều có severity, trigger, dashboard panel, runbook và incident mapping rõ ràng, giúp quá trình demo incident response có thể đi từ triệu chứng đến root cause một cách nhất quán.

---

