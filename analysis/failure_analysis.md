# Failure Analysis — Lab 18: Production RAG

**Học viên:** Hà Anh  
**Hình thức:** Bài tập cá nhân

---

## RAGAS Scores

| Metric | Naive Baseline | Production | Δ | Đạt chuẩn (≥0.75) |
|--------|:---:|:---:|:---:|:---:|
| Faithfulness | 0.9000 | 0.8615 | -0.0385 | ✅ Đạt |
| Answer Relevancy | 0.7186 | 0.7742 | +0.0556 | ✅ Đạt |
| Context Precision | 0.7500 | 0.7833 | +0.0333 | ✅ Đạt |
| Context Recall | 0.8250 | 0.8417 | +0.0167 | ✅ Đạt |

---

## Bottom-5 Failures (Phân tích từ Kết quả Thực nghiệm)

### #1
- **Question:** Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm và lương trong khoảng nào?
- **Expected:** 18 ngày phép (15 ngày cơ bản + 3 ngày thâm niên). Lương Senior (P3-P4): 20-35 triệu VNĐ/tháng.
- **Got:** 18 ngày phép. Thông tin lương không có trong context.
- **Worst metric:** Answer Relevancy = 0.00
- **Error Tree:** Output thiếu 1 vế → Context chỉ lấy văn bản Nghỉ phép năm, thiếu văn bản Bảng lương → Multi-hop query → `RETRIEVAL_ERROR`
- **Root cause:** Câu hỏi dạng Multi-hop (hỏi 2 thông tin từ 2 tài liệu khác nhau: Nghỉ phép và Lương). Retrieval chỉ lấy văn bản có độ tương đồng cao nhất về nghỉ phép.
- **Suggested fix:** Áp dụng Query Decomposition (tách câu hỏi đa ý thành 2 sub-queries) và mở rộng Top-k Retrieval.

### #2
- **Question:** Nếu cần mua một chiếc laptop 30 triệu cho nhân viên mới, ai phê duyệt và cần gì từ phòng CNTT?
- **Expected:** Laptop 30 triệu (5-50 triệu) cần Giám đốc phòng ban (Director) phê duyệt. Cần xác nhận cấu hình kỹ thuật từ CNTT và ít nhất 3 báo giá.
- **Got:** Cần cấp thẩm quyền phê duyệt (nêu hạn mức Trưởng phòng dưới 5 triệu), cần xác nhận cấu hình từ CNTT.
- **Worst metric:** Context Precision = 0.00
- **Error Tree:** Output chưa nêu rõ cấp Giám đốc → Context chứa lẫn bảng hạn mức chung → `RETRIEVAL_ERROR`
- **Root cause:** Bảng phân quyền mua sắm có nhiều cấp hạn mức (<5tr, 5-50tr, >50tr), chunking lấy được một phần bảng chưa phân cấp chi tiết.
- **Suggested fix:** Sử dụng Structure-Aware Chunking để bảo tồn trọn vẹn toàn bộ bảng Markdown quy định hạn mức mua sắm.

### #3
- **Question:** Bao lâu phải đổi mật khẩu một lần?
- **Expected:** Theo chính sách hiện hành (v2.0), mật khẩu phải được thay đổi mỗi 120 ngày.
- **Got:** Mật khẩu phải được thay đổi mỗi 120 ngày theo Chính sách mật khẩu v2.0.
- **Worst metric:** Faithfulness = 0.00 (LLM Judge gắt gao khi Ground Truth nhắc thêm câu giải thích về v1.0 cũ 90 ngày).
- **Error Tree:** Output đúng nội dung thực tế → LLM Judge bắt chéo chi tiết bổ sung của Ground Truth → `EVAL_BIAS`
- **Root cause:** Ground truth có thêm câu mô tả so sánh với phiên bản cũ, mô hình RAGAS faithfulness trừ điểm khi câu trả lời ngắn gọn không nhắc lại bản cũ.
- **Suggested fix:** Bổ sung Prompt hướng dẫn LLM giải thích rõ ràng lịch sử phiên bản khi gặp các câu hỏi liên quan đến chính sách cập nhật.

### #4
- **Question:** Nhân viên tạm ứng 15 triệu, sau 20 ngày mới thanh toán. Bị phạt bao nhiêu?
- **Expected:** Thời hạn 15 ngày, quá hạn 5 ngày, tính phí 2%/tháng pro-rata khoảng 50.000 VNĐ.
- **Got:** Tính toán chi tiết quá hạn 5 ngày là 50.000 VNĐ.
- **Worst metric:** Faithfulness = 0.23 (LLM diễn giải thêm các bước trung gian 150.000 VNĐ và 50.000 VNĐ).
- **Error Tree:** Output đúng kết quả cuối cùng → Bước diễn giải trung gian hơi dài dòng → `GENERATION_FORMAT`
- **Root cause:** LLM tự động suy luận các bước tính toán (CoT) khiến câu trả lời chứa thêm từ ngữ không có nguyên văn trong văn bản gốc.
- **Suggested fix:** Điều chỉnh system prompt yêu cầu trả lời trực tiếp con số cuối cùng và công thức rút gọn.

### #5
- **Question:** Nhân viên được tài trợ khóa học 25 triệu, nghỉ việc sau 8 tháng hoàn thành khóa học. Phải hoàn trả bao nhiêu?
- **Expected:** Cam kết làm việc 1 năm, nghỉ sau 8 tháng phải hoàn trả 100% chi phí = 25.000.000 VNĐ.
- **Got:** Nhân viên phải hoàn trả 25.000.000 VNĐ (100% chi phí).
- **Worst metric:** Faithfulness = 0.00
- **Error Tree:** Output đúng nội dung cốt lõi → Thiếu giải thích mốc cam kết 1 năm → `GENERATION_CONCISENESS`
- **Root cause:** LLM trả lời quá ngắn gọn (chỉ nêu kết quả 25 triệu), trong khi Ground Truth có thêm lời giải thích về điều kiện 1 năm.
- **Suggested fix:** Cân bằng prompt giữa tính súc tích và tính giải thích nguyên nhân.
- **Worst metric:** Faithfulness = 0.50
- **Error Tree:** Output sai → Context có nhắc đến bảng phân loại → LLM suy diễn sai → `GENERATION_ERROR`
- **Root cause:** Prompt Naive chưa đủ nghiêm ngặt về việc trích xuất chính xác nhãn phân loại từ bảng.
- **Suggested fix:** Tối ưu hóa System Prompt trong Production Pipeline: "Trả lời CHỈ dựa trên context. Không tự suy diễn."

---

## Case Study (cho presentation)

**Question chọn phân tích:** "Nếu cần mua một chiếc laptop 30 triệu cho nhân viên mới thì quy trình thế nào?"

**Error Tree walkthrough:**
1. **Output đúng?** $\rightarrow$ Sai (báo Tổng Giám Đốc duyệt thay vì Trưởng bộ phận).
2. **Context đúng?** $\rightarrow$ Context lấy về đoạn quy định mua sắm lớn $> 50$ triệu thay vì đoạn thiết bị tiêu chuẩn.
3. **Query rewrite OK?** $\rightarrow$ Query người dùng rõ ràng nhưng Dense Search bị nhiễu do vector của "mua sắm thiết bị" quá gần nhau.
4. **Fix ở bước:** Áp dụng Hybrid Search (BM25 bắt keyword "30 triệu") và Cross-Encoder Reranker (`bge-reranker-v2-m3`) để sắp xếp đúng đoạn hạn mức lên đầu (Rank 1).

**Nếu có thêm 1 giờ, sẽ optimize:**
- Tích hợp thêm Query Expansion (sinh đa truy vấn đồng nghĩa) trước khi đưa vào BM25.
- Fine-tune bộ trọng số RRF ($k=60$ và $\alpha$ kết hợp dense/sparse theo từng loại câu hỏi).
