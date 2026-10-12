# Blueprint CI/CD cho RAG và guardrails

Nhóm: DoanNgoc (làm cá nhân)

Người phụ trách: Ngô Doãn Ngọc — 2A202602635

Đây là **đề xuất CI/CD**, không phải workflow đã được triển khai/chạy.
Nguồn kết quả: artifacts/ragas_50q.json, judge_results.json, guard_results.json.
Run timestamp: Phase C 2026-10-12T10:54:07.376686+00:00 (Phase A 10:58:54, Phase B 10:52:33 cùng
ngày, UTC); guard models: `openai/gpt-4o-mini` (NeMo Guardrails 0.10.0, engine openai qua OpenRouter).
Models generation/evaluator/judge từ A/B: generation `openai/gpt-4o-mini` (answers_50q.json);
evaluator `openai/gpt-4o-mini` + `openai/text-embedding-3-small` (ragas_50q.json, từ metadata m4);
judge `openai/gpt-4o-mini` (judge_results.json).

## Kiến trúc và failure action

Input → Presidio → NeMo input → RAG → NeMo output → response.
Request thực dừng sớm khi bị chặn; khác phép đo input layers chạy đủ hai tầng.

| Tầng | Kiểm tra | Khi chặn / lỗi | Log |
|---|---|---|---|
| 1. Presidio (local, ~8 ms) | VN_CCCD (12/9 số), VN_PHONE (0[3-9]xxxxxxxx), EMAIL_ADDRESS, PHONE_NUMBER, thẻ/IBAN; ngưỡng score ≥0.5 | Trả câu từ chối chuẩn, không gọi LLM | Chỉ log entity type + vị trí + bản `anonymized`, không log text gốc |
| 2. NeMo input (`self check input`) | Off-topic, jailbreak/override, giả danh, trích system prompt, xin PII người khác, credential, nội dung gây hại | Trả message `bot refuse to respond` trong `rails.co` | Log `activated_rails` (name, stop) + input đã redact |
| 3. RAG (m1–m5 + generation) | Hybrid search → rerank top-3 → gpt-4o-mini | Lỗi LLM: trả extractive fallback có gắn cờ `generation_mode=extractive_fallback`, hoặc từ chối nếu không có context | Log ids chunk, model, latency |
| 4. NeMo output (`self check output`) | CCCD/CMND, SĐT/email cá nhân, lương cá nhân, credential, hồ sơ mật; cho phép `helpdesk@cty.vn`, khung lương theo cấp | Thay answer bằng câu từ chối (đã kiểm chứng ở output 203, 204) | Log flagged_reason, không log answer gốc nhạy cảm |

Quyết định block đọc từ `result.log.activated_rails[*].stop`, không dò từ khóa "xin lỗi/không
thể" (clean 102 chứa đúng cụm này và vẫn được allowed). Presidio chỉ tính các entity type ở trên
vì recognizer spaCy tiếng Anh gán nhầm `PERSON` cho "Senior", "MFA", "VPN" trong câu sạch (đã thấy
khi thử). Nếu bật mọi entity thì 8/8 clean sẽ bị chặn. Secrets (`OPENAI_API_KEY`, `OPENAI_BASE_URL`)
chỉ nằm trong `.env` (bị `.gitignore`) hoặc secret store của CI. Fail-closed: nếu NeMo input lỗi
hoặc timeout, request bị chặn kèm thông báo thử lại, không cho đi thẳng vào RAG.

## Phạm vi và số đo latency

Bắt buộc Task 12: **input_layers_sequential**, Presidio + NeMo input, không
short-circuit. Engines tạo trước đo; có hai warm-up thật không tính vào mẫu.
Percentile nội suy tuyến tính từ raw samples; tổng từ tổng từng sample.

Số mẫu timed: 20; warm-up: 2;
phương pháp: linear (vị trí (n−1)·q trên raw samples, `perf_counter`), input là 8 câu clean xoay vòng.

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---|---|---|---|
| Presidio | 7.54 | 9.81 | 12.06 | Đo Task 12 — rất nhanh, local |
| NeMo input | 1400.57 | 1727.61 | 1789.54 | Đo Task 12 — 1 LLM call/sample qua OpenRouter |
| Input guard sequential | 1408.28 | 1735.10 | 1795.71 | Đo Task 12 — vượt target 500ms |
| RAG | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| NeMo output | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| Full guard / short-circuit request | chưa đo | chưa đo | chưa đo | Không suy từ input_guard_ms |

Input-layer budget target: 500ms; kết quả thực tế/budget_ok: P95 input guard = 1735.10 ms →
`latency_budget_ok = false`.
Bottleneck là NeMo input: >99% thời gian (P50 1400.57/1408.28 ms) là round-trip LLM self-check
qua gateway OpenRouter từ máy cá nhân ở Việt Nam. Presidio chỉ chiếm ~8 ms. Số đo được ghi đúng
như đo, không chỉnh cho đạt. Hướng giảm: (1) đặt guard gần endpoint model hoặc gọi trực tiếp
provider; (2) thay self-check LLM bằng classifier nhỏ local (ví dụ prompt-injection classifier
fine-tune) và chỉ gọi LLM khi classifier không chắc; (3) cache quyết định cho câu hỏi lặp;
(4) chạy NeMo input song song với retrieval và huỷ RAG nếu bị chặn. Kế hoạch đo phần chưa đo:
dùng cùng harness (engines tạo trước, 2 warm-up, ≥20 mẫu, `perf_counter`), gắn timestamp từng
tầng trong một request thật để có RAG, NeMo output và full-guard P50/P95/P99 riêng; full guard
mới là phép đo áp dụng budget 500ms.

## CI gates đề xuất

- RAGAS faithfulness ≥0.75, avg_score ≥0.65 trên 50 câu.
- Attacks ≥18/20 cho CI đề xuất; clean 8/8 allowed; output cases đúng.
- Full guard P95 <500ms chỉ áp dụng sau khi thực sự đo full guard.

Mốc bắt buộc lab vẫn attacks ≥15/20; bonus ≥18/20 kèm clean controls đạt.
Workflow **chưa triển khai**. Đề xuất một job GitHub Actions `eval-guard.yml` chạy khi PR đổi
`src/`, `guardrails/`, prompts hoặc `data/`:

1. `python -m pytest tests/ -q` (offline, mock), fail → chặn merge.
2. Job live (chạy tay hoặc nightly vì có chi phí API): `setup_answers.py --live`, rồi
   `run_experiments.py --phase a|b|c --live`, rồi `check_lab.py`.
3. Thêm script `scripts/ci_gates.py` (chưa viết) đọc ba JSON và `sys.exit(1)` nếu:
   faithfulness mean < MIN_FAITHFULNESS=0.75 hoặc avg_score < MIN_AVG=0.65; attacks passed < 18;
   clean false_positive_rate > 0; bất kỳ output case sai; κ < 0.6 trên bộ calibration.
   Các biến MIN_* chỉ có tác dụng khi script này tồn tại và được gọi trong job.

Theo số hiện tại, gate RAGAS sẽ **fail**: faithfulness mean toàn bộ = (0.883·20 + 0.485·20 +
0.600·10)/50 = 0.667 < 0.75, nhưng avg_score toàn bộ ≈ 0.731 ≥ 0.65. Gate guard pass (20/20,
8/8, 4/4). Như vậy pipeline hiện chưa đạt điều kiện merge theo đề xuất này.

## Monitoring và cải tiến

| Metric production | Cách lấy | Ngưỡng cảnh báo | Người xử lý |
|---|---|---|---|
| Tỷ lệ block input theo tầng (presidio / nemo_input) | Đếm từ log activated_rails | Lệch ±50% so với baseline 7 ngày | On-call guard |
| False positive (clean bị chặn) | Người review mẫu 1% request bị chặn mỗi ngày + user feedback "bị chặn nhầm" | >2% mẫu review | Owner guard prompt |
| Tỷ lệ answer "Không tìm thấy" | Đếm answer của RAG | >5% (eval hiện tại 7/50 = 14%) | Owner RAG |
| Faithfulness online | RAGAS trên mẫu 50 request/ngày, đã redact PII | Mean <0.75 hai ngày liên tiếp | Owner RAG |
| Latency P95 từng tầng | Timestamp từng tầng trong request | Input guard P95 >2000ms hoặc full guard vượt budget | Platform |
| Drift tài liệu | Hash `data/` + cảnh báo khi xuất hiện phiên bản policy mới | Có version mới mà eval chưa chạy lại | Owner RAG |

Privacy: log chỉ chứa text đã anonymize; lưu tối đa 30 ngày; không đưa PII thật vào bộ eval.

RAGAS mean/worst distribution: avg_score factual 0.816 / multi_hop 0.691 / adversarial 0.640
(worst = adversarial); worst_metric phổ biến nhất answer_relevancy (29/50, chủ yếu do giới hạn đo
trên tiếng Việt).
Cohen’s κ: 1.000 (10/10 nhãn khớp human trên đúng model_answer gốc).
Attacks passed: 20/20; clean false_positive_rate: 0.0 (8/8 allowed); output 4/4 đúng.

Cải tiến có thể kiểm tra, gắn với bằng chứng:

1. **Giảm over-refusal**: sửa prompt generation (tổng hợp nhiều context, ưu tiên bản hiện hành).
   Kiểm chứng: số answer "Không tìm thấy" giảm từ 7 (ids 9, 33, 39, 42, 44, 48, 50) và
   faithfulness adversarial tăng từ 0.600.
2. **Không cắt bảng khi chunk**: giữ nguyên bảng Markdown hoặc trả parent chunk. Kiểm chứng: id 5
   trả "CEO", context_recall id 5 từ 0.00 lên 1.00.
3. **Mở rộng bộ guard**: 20 attacks/8 clean còn nhỏ và guard prompt đã được chỉnh khi nhìn thấy
   bộ này (rủi ro overfit). Thêm ≥50 câu clean và attack mới chưa dùng khi chỉnh prompt (paraphrase,
   tiếng Anh/Việt trộn, injection trong tài liệu), báo cáo FPR riêng trên tập held-out.
4. **Latency**: thử classifier local cho input rail và đo lại Task 12. Mục tiêu NeMo/classifier
   P95 <400ms để còn budget cho RAG và output rail.
5. **Judge độc lập**: thêm judge khác họ model với gpt-4o-mini, đo κ trên ≥30 nhãn để giảm rủi ro
   self-preference.
