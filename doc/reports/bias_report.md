# Đánh giá LLM Judge Phase B

Nhóm: DoanNgoc (làm cá nhân)

Người phụ trách: Ngô Doãn Ngọc — 2A202602635

Nguồn: `artifacts/judge_results.json`; run timestamp: 2026-10-12T10:52:33.537414+00:00.
Models generation/judge: generation `openai/gpt-4o-mini` (answers A); judge
`openai/gpt-4o-mini` (pairwise và binary), temperature=0, `response_format=json_object`,
gọi qua OpenRouter.

## Năm cặp A/B và hai lượt

Nguồn cố định: A từ artifacts/answers_50q.json:answer; B từ
fixtures/human_labels_10q.json:model_answer; reference từ fixtures/test_set_50q.json:ground_truth.
Ids: 1, 5, 12, 21, 41. Không đổi nguồn sau khi xem kết quả judge.

Pass 2 đưa B vào vị trí đầu; `winner_pass2` và `scores_pass2` dưới đây đã quy về A/B gốc.

| id | Answer A (pipeline) | Answer B (model_answer) | Pass 1 (scores A/B) | Pass 2 quy đổi (scores A/B) | Final | Consistent |
|---|---|---|---|---|---|---|
| 1 | "nghỉ 3 ngày làm việc khi kết hôn" (48 ký tự) | "3 ngày làm việc **có lương**" (57) | B (0.8/1.0) | B (0.8/1.0) | **B** | ✔ |
| 5 | "Giám đốc phòng ban (Director)" (30) | "Cần Giám đốc phòng ban phê duyệt" (33) | B (0.2/0.4) | A (0.5/0.0) | tie | ✘ |
| 12 | "...có từ 6 tháng trở lên là 1 tháng lương" (85) | "thưởng Tết tối thiểu 1 tháng lương" (50) | A (1.0/0.5) | tie (1.0/1.0) | tie | ✘ |
| 21 | 18 ngày phép nhưng tự thêm "chỉ 12 ngày có lương, 6 ngày không lương" (304) | "18 ngày phép... Lương Senior 20–35 triệu" (82) | B (0.5/1.0) | B (0.0/1.0) | **B** | ✔ |
| 41 | "15 ngày phép năm" (37) | "12 ngày phép năm" (37) | A (1.0/0.0) | A (1.0/0.0) | **A** | ✔ |

Reasoning tóm tắt từ JSON: id 1, cả hai lượt chấm B hơn vì nêu "có lương" (reference ghi không
trừ phép năm). Id 21, cả hai lượt bắt được A sai ("số ngày phép có lương là 12" mâu thuẫn
reference) và A thiếu khoảng lương. Id 41, cả hai lượt nhận ra B dùng chính sách v2023 đã bị thay
thế. Id 5, cả hai lượt đều nói "cả hai sai vì không nêu CEO" nhưng chọn winner ngược nhau. Id 12,
pass 1 trừ B vì thiếu điều kiện "từ 6 tháng"; pass 2 coi hai answer tương đương.

Position bias count/rate: 2/5 = 0.40.
Verbosity win rate: 0.333 (1/3); decisive cases: 3 (a_wins_a_longer=0, b_wins_b_longer=1).

Hai case không nhất quán (5, 12) đều là cặp mà hai answer gần như **cùng chất lượng**: id 5 cả hai
cùng sai (cùng nói Director), id 12 cả hai cùng đúng số tiền và chỉ khác chi tiết điều kiện. Khi
không có khác biệt thực chất, lựa chọn của judge dao động theo vị trí. Đây là dấu hiệu position
sensitivity, nhưng 2/5 chưa đủ để kết luận judge có position bias hệ thống. Swap-and-average đã
xử lý đúng: cả hai thành tie, phù hợp với nội dung. Về verbosity, winner dài hơn chỉ thắng 1/3 case
decisive (id 1, B dài hơn 9 ký tự vì thêm ý "có lương" có trong reference). Ở id 21, answer dài nhất
(A, 304 ký tự) **thua** vì sai nội dung. Không thấy dấu hiệu judge thưởng cho độ dài.

## Calibration đúng model_answer

Helper đánh giá đúng question/model_answer đang có trong fixtures/human_labels_10q.json;
không lấy answer mới của pipeline. Prompt chỉ nhận question, answer, reference.
Không gửi human_label, human_note hoặc phân bố nhãn human vào prompt.

| # | question_id | model_answer (gốc) | Judge | Reasoning judge (rút gọn) | Human | Agree |
|---|---|---|---|---|---|---|
| 1 | 1 | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | 1 | Đúng số ngày và điều kiện | 1 | ✔ |
| 2 | 5 | Cần Giám đốc phòng ban phê duyệt. | 0 | Trên 50 triệu phải CEO | 0 | ✔ |
| 3 | 12 | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | 1 | Đúng, đủ ý thiết yếu | 1 | ✔ |
| 4 | 21 | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | 1 | Đúng phép và khoảng lương | 1 | ✔ |
| 5 | 23 | Hoàn trả 25 triệu vì chưa đủ 1 năm cam kết. | 1 | Đúng mức hoàn trả | 1 | ✔ |
| 6 | 29 | Trưởng phòng phê duyệt. Phạt 2% tháng trên 8 triệu. | 0 | Thiếu Kế toán trưởng; phí không pro-rata | 0 | ✔ |
| 7 | 33 | Phép: 19 ngày. Phụ cấp: 1.500.000 VNĐ/tháng. | 1 | Đúng cả hai phép tính | 1 | ✔ |
| 8 | 41 | Nhân viên được nghỉ 12 ngày phép năm. | 0 | Dùng chính sách cũ v2023 | 0 | ✔ |
| 9 | 46 | Nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần. | 1 | Giữ đúng phủ định | 1 | ✔ |
| 10 | 50 | Được, miễn là đảm bảo kết nối an toàn. | 0 | Reference cấm VPN cá nhân | 0 | ✔ |

Cohen’s κ: 1.000.
Observed/chance agreement và diễn giải: p_o = 10/10 = 1.00. Judge và human đều có 6 nhãn 1 và
4 nhãn 0, nên p_e = 0.6·0.6 + 0.4·0.4 = 0.52 và κ = (1.00 − 0.52)/(1 − 0.52) = 1.00 (almost
perfect, Landis–Koch). Reasoning của judge cho 4 nhãn 0 trùng lý do trong human_note (CEO,
Kế toán trưởng + pro-rata, phiên bản v2023, VPN cá nhân bị cấm), không chỉ trùng nhãn ngẫu nhiên.

## Giới hạn và cách dùng judge

- Mẫu rất nhỏ: 5 cặp pairwise và 10 nhãn binary. Với n=10, κ=1.0 vẫn có khoảng tin cậy rộng;
  chỉ một nhãn lệch đã làm κ giảm còn khoảng 0.78–0.80. Các case lỗi trong bộ này khá "rõ"
  (sai phiên bản, sai ngưỡng, phủ định), nên chưa kiểm tra được case khó như answer đúng một phần.
- Judge, generation và RAGAS evaluator đều là gpt-4o-mini, có rủi ro self-preference khi chấm
  answer của chính họ model (pairwise A là answer do gpt-4o-mini sinh). Ở id 21 judge vẫn chấm
  A thua, nhưng cần thêm judge khác họ model để kiểm chứng.
- Pairwise phụ thuộc reference: id 5 cả hai đều sai nên winner không có ý nghĩa; nên cho phép
  judge trả "both_bad" hoặc dùng điểm tuyệt đối theo reference thay vì ép A/B.
- Cách dùng: dùng judge để sàng lọc/regression trong CI, luôn chạy swap-and-average, coi kết quả
  lệch vị trí là tie, và định kỳ lấy mẫu để người gán nhãn đối chiếu lại κ. Không coi judge là
  đáp án tuyệt đối.
