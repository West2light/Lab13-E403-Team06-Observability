# Quy tắc cảnh báo và Runbook

**Chủ sở hữu**: Member C - SLO & Alerts

Trang này là runbook được liên kết từ `config/alert_rules.yaml`. Khi demo hoặc xử lý incident, dùng cùng một luồng điều tra cho mọi cảnh báo: bắt đầu từ metrics, mở traces, sau đó xác nhận nguyên nhân trong logs bằng cùng `correlation_id`.

## Tóm tắt SLO

| SLI | Mục tiêu | Cửa sổ đo | Panel dashboard chính |
|---|---:|---|---|
| Latency P95 | < 3000 ms | 28d | Latency P50/P95/P99 |
| Error Rate | < 2% | 28d | Error rate with breakdown |
| Daily Cost Budget | < $2.50/day | 1d | Cost over time |
| Average Quality Score | >= 0.75 | 28d | Quality proxy |

<a id="1-high-latency-p95"></a>
## 1. Độ trễ P95 cao

- **Tên alert**: `high_latency_p95`
- **Mức độ nghiêm trọng**: P2
- **Điều kiện kích hoạt**: `latency_p95_ms > 5000 for 30m`
- **SLO liên quan**: Latency P95 < 3000 ms trong 28d
- **Incident lab có khả năng liên quan**: `rag_slow`
- **Tác động**: người dùng nhận phản hồi chậm, tail latency vượt ngưỡng burn của SLO.

### Kiểm tra ban đầu

1. Mở panel latency trên dashboard và xác nhận P95 vượt 5000 ms trong 30 phút gần nhất.
2. Mở các trace chậm nhất trong 1 giờ gần nhất trên Langfuse.
3. So sánh các span RAG, LLM và tool để xác định thành phần bị chậm.
4. Dùng `correlation_id` trong trace để tìm JSON log tương ứng.
5. Kiểm tra incident toggle `rag_slow` có đang bật hay không.

### Giảm thiểu

- Giảm kích thước prompt hoặc lượng context cho các request bị ảnh hưởng.
- Dùng nguồn retrieval nhanh hơn nếu span RAG là nguyên nhân chính.
- Tạm thời giảm concurrency hoặc rate-limit các request tốn tài nguyên.
- Sau khi giảm thiểu, chạy lại traffic và xác nhận P95 quay về dưới 3000 ms.

### Bằng chứng cần lưu

- Ảnh chụp panel latency có đường ngưỡng SLO.
- Trace waterfall thể hiện span bị chậm.
- Log line có cùng `correlation_id`.

<a id="2-high-error-rate"></a>
## 2. Tỷ lệ lỗi cao

- **Tên alert**: `high_error_rate`
- **Mức độ nghiêm trọng**: P1
- **Điều kiện kích hoạt**: `error_rate_pct > 5 for 5m`
- **SLO liên quan**: Error Rate < 2% trong 28d
- **Incident lab có khả năng liên quan**: `tool_fail`
- **Tác động**: người dùng nhận phản hồi lỗi, mục tiêu availability của service bị đe dọa.

### Kiểm tra ban đầu

1. Mở panel error rate trên dashboard và xác nhận tỷ lệ lỗi vượt 5%.
2. Nhóm các JSON log gần nhất theo `error_type`.
3. Dùng `correlation_id` để nối log lỗi với trace lỗi tương ứng.
4. Kiểm tra lỗi đến từ LLM, RAG retrieval, tool call hay response schema.
5. Kiểm tra thay đổi gần đây hoặc incident toggle trước khi rollback.

### Giảm thiểu

- Tắt hoặc bypass tool đang lỗi nếu có thể.
- Retry bằng fallback model hoặc fallback retrieval path.
- Rollback thay đổi rủi ro gần nhất nếu lỗi bắt đầu sau deployment.
- Xác nhận error rate giảm xuống dưới 2% sau khi sửa.

### Bằng chứng cần lưu

- Ảnh chụp panel error rate.
- Một trace lỗi đại diện.
- JSON log chứa `error_type` và `correlation_id`.

<a id="3-cost-budget-spike"></a>
## 3. Tăng đột biến chi phí

- **Tên alert**: `cost_budget_spike`
- **Mức độ nghiêm trọng**: P2
- **Điều kiện kích hoạt**: `hourly_cost_usd > 2x_baseline for 15m`
- **SLO liên quan**: Daily Cost Budget < $2.50/day
- **Incident lab có khả năng liên quan**: `cost_spike`
- **Tác động**: token usage hoặc model routing làm ngân sách bị tiêu thụ nhanh hơn dự kiến.

### Kiểm tra ban đầu

1. Mở panel cost trên dashboard và xác nhận hourly cost vượt 2 lần baseline.
2. Tách các trace gần nhất theo feature, model và user/session nếu có.
3. So sánh `tokens_in` và `tokens_out` giữa traffic bình thường và traffic tăng chi phí.
4. Dùng log có cùng `correlation_id` để xác nhận request shape và feature.
5. Kiểm tra incident toggle `cost_spike` có đang bật hay không.

### Giảm thiểu

- Rút ngắn prompt và giảm kích thước retrieved context.
- Route các request đơn giản sang model rẻ hơn.
- Giới hạn max output tokens cho endpoint bị ảnh hưởng.
- Bật hoặc cải thiện prompt caching nếu hệ thống hỗ trợ.
- Xác nhận projected daily cost quay về dưới $2.50/day.

### Bằng chứng cần lưu

- Ảnh chụp panel cost.
- Trace thể hiện token usage bất thường.
- Giá trị chi phí trước và sau khi giảm thiểu.
