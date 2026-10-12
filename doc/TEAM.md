# Nhóm thực hiện K4 Track 3A

Tên nhóm: DoanNgoc (làm cá nhân, 1 thành viên)

Repo chung: https://github.com/nngocnd/K4-L3-DAY24-DoanNgoc-Eval-Guard

Trưởng nhóm/người nộp: Ngô Doãn Ngọc — 2A202602635

Ngày lab/deadline áp dụng: 12/10/2026, 23:59 — Asia/Ho_Chi_Minh (UTC+07:00)

Commit dùng để chấm: commit mới nhất trên nhánh `main` tại thời điểm nộp link (SHA ghi trong mục "Cập nhật sau khi nộp").

Mỗi nhóm nộp một repo. Điền đủ thành viên và một mục INDIVIDUAL cho từng người.
Thêm/xóa rows để khớp nhóm thật; mẫu ba rows không ép nhóm phải có ba người.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Ngô Doãn Ngọc | 2A202602635 | Toàn bộ: tích hợp m1–m5 từ Day 18, Phase A (Tasks 1–4), Phase B (Tasks 5–8), Phase C (Tasks 9a–12), guard prompt, chạy batch live, 3 báo cáo + blueprint | Commits trên `main`; `artifacts/*.json`; `doc/reports/*.md` |

Người tích hợp/chạy batch/nộp link: Ngô Doãn Ngọc. Đã chạy `setup_answers.py --live`, rồi
`run_experiments.py --phase a/b/c --live` (Phase C với `--latency-samples 20`), rồi
`check_lab.py`; bằng chứng là 4 JSON trong `artifacts/`.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: Windows 11 Pro 10.0.26200; **Python 3.12.10** (máy không có Python 3.11);
**không có MSVC**, nên `annoy==1.17.3` build lỗi ("Microsoft Visual C++ 14.0 or greater is
required"). Cách xử lý: cài một gói shim `annoy==1.17.3` thuần numpy (brute-force, kết quả kNN chính
xác, cùng API `AnnoyIndex`) **chỉ trong virtualenv**, không commit vào repo. NeMo chỉ dùng annoy cho
embedding index nội bộ; lab chỉ bật built-in `self check input/output` nên quyết định rail không phụ
thuộc annoy. Đây là sai khác so với môi trường mục tiêu (3.11 + annoy thật).
Virtualenv/dependencies/imports: `python -m venv .venv`; cài
`pip install -r requirements/requirements.txt -c requirements/constraints-core.txt` (sau khi có shim);
thêm `pyarrow<20` và `pandas<3` vì pyarrow 26 cần NumPy 2 mà constraints pin `numpy==1.26.4`;
`pip check` → "No broken requirements found";
`python -c "import ragas, nemoguardrails, presidio_analyzer, spacy"` → imports OK;
`python -m spacy download en_core_web_lg` thành công; `pytest tests/ -q` → 86 passed, 3 deselected.
Models/Qdrant/50 answers đã chuẩn bị: Qdrant `qdrant/qdrant:v1.9.7` qua `infra/docker-compose.yml`
(Docker Desktop); BGE-M3 + bge-reranker-v2-m3 từ HF cache có sẵn (Day 18); m5 enrich 130 chunks bằng
LLM; 50 answers đều `generation_mode=llm`, `generation_model=openai/gpt-4o-mini`, không fallback.
Key là OpenRouter (OpenAI-compatible), nên `.env` đặt `OPENAI_BASE_URL=https://openrouter.ai/api/v1`;
model IDs trong `config.py` và `guardrails/config.yml` dùng tiền tố `openai/` (cùng model gpt-4o-mini).
Embedding evaluator là `openai/text-embedding-3-small` qua OpenRouter.

## INDIVIDUAL

### NgoDoanNgoc-2A202602635

- Phần được giao và phần thực tế đã làm: làm cá nhân toàn bộ bài.
  (1) Tích hợp m1–m5 Day 18: m2 dùng `client.search` khi qdrant-client <1.10 (không có
  `query_points`); m4 trả `metadata.evaluator_models`, chấm lại các dòng NaN và báo lỗi thay vì
  gán 0 giả; `config.py` thêm các biến cho m4/m5. (2) Phase A: `group_by_distribution`,
  `run_ragas_50q` (kiểm tra số dòng, metric hữu hạn trong [0,1]), `bottom_10` với `diagnose()` dựa
  trên bằng chứng (phân biệt over-refusal, retrieval miss, khẳng định suy ra), `cluster_analysis`
  chọn nhóm yếu theo mean. (3) Phase B: prompt pairwise có reference và tiêu chí
  accuracy > completeness > conciseness, swap-and-average quy đổi winner/scores, κ tự tính (báo lỗi
  khi p_e=1), bias report. (4) Phase C: `pii_scan` có whitelist entity, input/output rail đọc
  `activated_rails[].stop`, suite 28 inputs trong một event loop, latency 2 warm-up + 20 mẫu;
  viết lại prompt `self_check_input` trong `guardrails/config.yml`.
- Bằng chứng: commits trên `main`; `artifacts/answers_50q.json`, `ragas_50q.json`,
  `judge_results.json`, `guard_results.json`; `doc/reports/failure_clusters.md`, `bias_report.md`,
  `blueprint.md`.
- Cách kiểm tra: unit mock `pytest tests/ -q` → 86 passed. Live: Phase A avg factual 0.816 /
  multi_hop 0.691 / adversarial 0.640; Phase B κ=1.000, position inconsistency 2/5; Phase C attacks
  20/20, clean 8/8 (FPR 0.0), output 4/4, input guard P95 1735.10 ms. `check_lab.py` pass toàn bộ
  artifact checks.
- Điều đã học: (1) Metric RAGAS phải đọc cùng answer/context. Faithfulness=0 ở 7 câu bottom là do LLM
  từ chối dù context đủ, không phải hallucination, và answer_relevancy bị đo thấp có hệ thống trên
  tiếng Việt. (2) Pairwise judge cần swap. Hai cặp lệch vị trí đều là cặp chất lượng ngang nhau, nên
  tie là kết quả đúng. Pairwise winner và nhãn 0/1 là hai câu hỏi khác nhau. (3) Guard phải có clean
  controls. Prompt self-check gốc cho qua câu "viết bài thơ", còn Presidio bật mọi entity thì chặn
  nhầm câu sạch ("Senior", "MFA" bị gán PERSON).
- Giới hạn/cách xử lý: Python 3.12 + annoy shim thay cho 3.11 + annoy thật (đã ghi ở trên). Prompt
  input rail được chỉnh khi đã thấy bộ 28 inputs (nguy cơ overfit), nên blueprint đề xuất tập held-out.
  Latency input guard vượt 500ms do LLM self-check qua OpenRouter; số đo ghi nguyên trạng. Generation,
  evaluator và judge cùng là gpt-4o-mini, có rủi ro self-preference.
- Nguồn/AI hỗ trợ nếu có: dùng Claude Code (Anthropic) hỗ trợ viết code các Task, adapter m2/m4,
  guard prompt và bản nháp báo cáo. Tự kiểm chứng bằng unit tests, các lần chạy live, `check_lab.py`
  và đọc lại answer/contexts trong JSON trước khi viết kết luận.

## Cập nhật sau khi nộp

Không có cập nhật sau khi nộp. Phiên bản nộp là commit cuối trên `main` trước deadline 23:59 ngày
12/10/2026.
