# Phân tích lỗi Phase A

Nhóm: DoanNgoc (làm cá nhân)

Người phụ trách: Ngô Doãn Ngọc — 2A202602635

Nguồn: `artifacts/ragas_50q.json`; run timestamp: 2026-10-12T10:58:54.785900+00:00.
Generation mode/fallback và điều kiện chạy: 50/50 câu `generation_mode=llm`, không có
extractive fallback. Pipeline Day 18 (m1 hierarchical chunking 2048/256 → m5 enrichment
1 LLM call/chunk, 130 chunks → m2 hybrid BM25 + BGE-M3 trên Qdrant v1.9.7 → m3
bge-reranker-v2-m3 top-3) chạy local CPU; LLM gọi qua OpenRouter (OpenAI-compatible).
Models generation/evaluator: generation `openai/gpt-4o-mini`; evaluator (từ
`m4_eval.evaluate_ragas(...)["metadata"]["evaluator_models"]`) `openai/gpt-4o-mini` +
`openai/text-embedding-3-small`. RAGAS 0.1.22, 4 metric × 50 câu = 200 lượt chấm, không còn NaN.

## Điểm theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---|---|---|
| faithfulness | 0.883 | 0.485 | 0.600 |
| answer_relevancy | 0.490 | 0.484 | 0.343 |
| context_precision | 0.992 | 0.950 | 0.967 |
| context_recall | 0.900 | 0.846 | 0.650 |
| avg_score | **0.816** | **0.691** | **0.640** |

Retrieval mạnh ở cả ba nhóm (precision ≥0.95, recall ≥0.65). Điểm yếu nằm ở generation
(faithfulness multi_hop/adversarial) và ở answer_relevancy thấp đồng loạt (xem mục giới hạn).

## Bottom 10 và nguyên nhân

Rows lấy nguyên văn từ `bottom_10` (Task 3). Diagnosis do hàm `diagnose()` của Task 3 tạo
từ bằng chứng (answer có phải từ chối không + context_recall), không phải bản mặc định.
F/AR/CP/CR = faithfulness/answer_relevancy/context_precision/context_recall.

| Rank | id | Distribution | avg | F / AR / CP / CR | worst_metric | Diagnosis (Task 3) | Suggested fix (Task 3) |
|---|---|---|---|---|---|---|---|
| 1 | 39 | multi_hop | 0.125 | 0.00 / 0.00 / 0.00 / 0.50 | faithfulness | Over-refusal ở generation (CR=0.50) | Sửa prompt generation, tổng hợp nhiều context, ưu tiên phiên bản hiện hành |
| 2 | 50 | adversarial | 0.333 | 0.00 / 0.00 / 1.00 / 0.33 | faithfulness | Retrieval miss: thiếu chunk chứa đáp án | Tăng recall: hybrid top_k lớn hơn, query rewriting |
| 3 | 5 | factual | 0.340 | 0.00 / 0.36 / 1.00 / 0.00 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 4 | 44 | adversarial | 0.375 | 0.00 / 0.00 / 0.83 / 0.67 | faithfulness | Over-refusal ở generation (CR=0.67) | Như rank 1 |
| 5 | 33 | multi_hop | 0.375 | 0.00 / 0.00 / 1.00 / 0.50 | faithfulness | Over-refusal ở generation (CR=0.50) | Như rank 1 |
| 6 | 48 | adversarial | 0.417 | 0.00 / 0.00 / 1.00 / 0.67 | faithfulness | Over-refusal ở generation (CR=0.67) | Như rank 1 |
| 7 | 42 | adversarial | 0.417 | 0.00 / 0.00 / 1.00 / 0.67 | faithfulness | Over-refusal ở generation (CR=0.67) | Như rank 1 |
| 8 | 9 | factual | 0.500 | 0.00 / 0.00 / 1.00 / 1.00 | faithfulness | Over-refusal ở generation (CR=1.00) | Như rank 1 |
| 9 | 31 | multi_hop | 0.539 | 0.00 / 0.49 / 1.00 / 0.67 | faithfulness | Khẳng định không được context hỗ trợ trực tiếp (số suy ra qua tính toán) | Trích câu nguồn + trình bày phép tính; temperature=0; kiểm tra bảng bị cắt |
| 10 | 24 | multi_hop | 0.597 | 0.00 / 0.39 / 1.00 / 1.00 | faithfulness | Như rank 9 | Như rank 9 |

Đối chiếu answer/contexts/reference cho từng nhóm lỗi:

1. **Over-refusal khi context đã đủ (7 câu: 9, 33, 39, 42, 44, 48, 50).** Cả 7 answer là
   nguyên văn `Không tìm thấy.`. Ví dụ id 9 (CR=1.00): context #1 ghi "**Sinh con** (nam
   giới): 5 ngày làm việc liên tục" nhưng LLM vẫn từ chối. Id 48: context #1 ghi "Nhân viên
   thử việc ... chưa được hưởng gói bảo hiểm sức khỏe PVI". Id 50: context #1 ghi "Không sử
   dụng VPN cá nhân (NordVPN, ExpressVPN)". Faithfulness/relevancy = 0 là hệ quả của câu
   từ chối không có khẳng định nào, không phải hallucination. Task 3 gán id 50 là "retrieval
   miss" vì CR=0.33, nhưng đọc context cho thấy ý cấm đã có; CR thấp vì reference thêm chi
   tiết (v1.3, WireGuard) mà top-3 không chứa → đây là giới hạn của luật chẩn đoán dựa vào
   ngưỡng, nguyên nhân chính vẫn là generation. Prompt setup "Trả lời CHỈ dựa trên context.
   Nếu không có → nói 'Không tìm thấy.'" quá chặt: khi context có hai phiên bản mâu thuẫn
   (42, 44: chunk v2024 và v2023, v2.0 và v1.0 cùng xuất hiện) hoặc câu hỏi cần phủ định/
   kết hợp nhiều chunk (33, 39, 48, 50), model chọn từ chối thay vì tổng hợp.
2. **Chunking cắt bảng → hallucination thật (id 5).** Answer "Giám đốc phòng ban
   (Director)" sai; reference là CEO. Child chunk 256 ký tự chứa bảng thẩm quyền chỉ tới dòng
   "5.000.000 - 50.000.000 → Director"; dòng "Trên 50.000.000 → CEO" (`data/mua_sam.md:9`)
   rơi sang chunk khác không được rerank lên top-3. CR=0.00 xác nhận context thiếu dòng cần
   thiết; model ngoại suy từ dòng cuối cùng nhìn thấy.
3. **Faithfulness thấp do câu trả lời có tính toán (id 24, 31).** Cả hai answer **đúng** theo
   reference (2.400.000 VNĐ; 50.000 VNĐ) nhưng F=0: RAGAS tách answer thành statements như
   "2 × 1.200.000 = 2.400.000" mà context không chứa nguyên văn, nên không được NLI xác nhận.
   Đây là giới hạn đo lường của faithfulness với câu multi-hop cần tính toán.

## Matrix và nhóm yếu nhất

Mỗi câu được đếm một lần theo metric thấp nhất của chính nó (không coi mọi câu là failure):

| worst_metric | factual | multi_hop | adversarial | Tổng |
|---|---|---|---|---|
| faithfulness | 2 | 12 | 4 | 18 |
| answer_relevancy | 17 | 7 | 5 | 29 |
| context_precision | 0 | 0 | 0 | 0 |
| context_recall | 1 | 1 | 1 | 3 |
| Tổng (= kích thước nhóm) | 20 | 20 | 10 | 50 |

Nhóm yếu theo mean thấp nhất: adversarial; mean: 0.640 (multi_hop 0.691, factual 0.816).
Worst metric xuất hiện nhiều nhất: answer_relevancy; số câu: 29/50.

Adversarial yếu nhất vì 4/10 câu (42, 44, 48, 50) bị từ chối dù context đúng; 6 câu còn lại
đều trả đúng phiên bản hiện hành và F=1.00. Multi_hop gần như ngang: faithfulness chỉ 0.485
do 12/20 câu có worst_metric là faithfulness, gồm 2 câu từ chối (33, 39), các câu có tính toán
(24, 31, 38) và vài câu sai thật (27: tính thâm niên 7÷3 ra +1 ngày thay vì +2; 21: tự thêm
"chỉ 12 ngày có lương"). Answer_relevancy dominant nhưng **không nên** đọc là "answer không
khớp câu hỏi": factual có 17/20 câu worst là AR dù answer đúng và ngắn (id 3 "Phụ cấp ăn trưa
hàng tháng là 1.000.000 VNĐ." có AR=0.41). Không dùng tổng cột 20/20/10 để chọn nhóm yếu.

Đề xuất sửa và cách kiểm chứng:

1. Sửa system prompt của `run_query`: "Tổng hợp từ tất cả context; nếu có nhiều phiên bản,
   trả theo phiên bản hiện hành và nói rõ bản cũ đã hết hiệu lực; chỉ trả 'Không tìm thấy'
   khi không context nào liên quan". Chạy lại `setup_answers.py --live` + Phase A; kỳ vọng
   số câu `Không tìm thấy` giảm từ 7 về ≤1 và faithfulness adversarial tăng.
2. Chunking giữ nguyên bảng Markdown (không tách giữa các dòng `|...|`) hoặc trả parent chunk
   (2048) cho LLM thay vì child 256. Kiểm chứng bằng id 5 và CR của factual.
3. Với câu tính toán, yêu cầu answer trích số gốc rồi mới tính, để faithfulness đo được.

## Bẫy adversarial và giới hạn

Adversarial mean (0.640) < factual mean (0.816), đạt điều kiện so sánh của bonus Phase A,
nhưng điều này chỉ cho thấy nhóm adversarial khó hơn. Bằng chứng cho thấy pipeline **chưa**
xử lý bẫy một cách chủ động: ở hai bẫy phiên bản (42 thâm niên, 44 chu kỳ đổi mật khẩu),
retriever đã đưa cả chunk mới và cũ vào top-3 (v2024 "từ 3 năm" + v2023 "từ 5 năm"; v2.0 "120
ngày" + v1.0 "90 ngày"), và LLM bỏ cuộc thay vì chọn bản hiện hành. Ở bẫy phủ định (48 thử
việc/PVI, 50 VPN cá nhân), context chứa câu phủ định đúng nhưng model vẫn từ chối. Các câu
bẫy được trả đúng (41, 43, 45, 46, 47, 49) đều là câu chỉ cần một chunk hiện hành.

Giới hạn: (1) 50 câu, adversarial chỉ 10 câu, nên một câu đổi kết quả làm mean nhóm đổi
khoảng 0.03–0.04; (2) evaluator là gpt-4o-mini (cùng họ model với generation) và RAGAS
0.1.22 dùng prompt tiếng Anh để sinh câu hỏi ngược cho answer_relevancy, rồi so cosine bằng
text-embedding-3-small trên tiếng Việt, nên AR bị kéo thấp hệ thống (mean 0.458); hai lần
chạy Phase A cho số rất gần nhau (avg factual 0.817 → 0.816) nhưng AR không phải tín hiệu
chất lượng đáng tin cho tiếng Việt; (3) diagnosis của Task 3 là luật dựa vào ngưỡng, cần
người đọc lại (như id 50).
