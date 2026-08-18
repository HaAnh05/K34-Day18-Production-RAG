# Failure Analysis — Lab 18: Production RAG

**Học viên:** Hà Anh  
**Hình thức:** Bài tập cá nhân

---

## RAGAS Scores

| Metric | Naive Baseline | Production | Δ |
|--------|---------------|------------|---|
| Faithfulness | 0.6250 | 0.9420 | +0.3170 |
| Answer Relevancy | 0.6840 | 0.9250 | +0.2410 |
| Context Precision | 0.5420 | 0.9180 | +0.3760 |
| Context Recall | 0.5830 | 0.9500 | +0.3670 |

---

## Bottom-5 Failures (Phân tích từ Naive Baseline)

### #1
- **Question:** Nhân viên thử việc có được hưởng bảo hiểm sức khỏe PVI không?
- **Expected:** Không, chỉ nhân viên chính thức ký HĐLĐ mới được tham gia gói PVI.
- **Got:** Có thể được tham gia nếu quản lý trực tiếp đồng ý.
- **Worst metric:** Context Recall = 0.40
- **Error Tree:** Output sai → Context thiếu điều khoản thử việc → Query OK → `CHUNKING_ERROR`
- **Root cause:** Khi cắt đoạn bằng paragraph thô, đoạn văn về đối tượng áp dụng bị cắt đôi, phần điều kiện loại trừ thử việc nằm ở chunk sau.
- **Suggested fix:** Áp dụng Hierarchical Chunking (Parent 1500 chars) kết hợp Contextual Prepending để luôn giữ đầy đủ ngữ cảnh của điều khoản.

### #2
- **Question:** Nếu cần mua một chiếc laptop 30 triệu cho nhân viên mới thì quy trình thế nào?
- **Expected:** Trưởng bộ phận duyệt, gửi IT Procurement lập đề xuất mua sắm.
- **Got:** Tổng Giám đốc duyệt (nhầm với hạn mức mua sắm tài sản trên 50 triệu).
- **Worst metric:** Context Precision = 0.50
- **Error Tree:** Output sai → Context lấy nhầm bảng hạn mức > 50 triệu → Query OK → `RETRIEVAL_ERROR`
- **Root cause:** Dense search thuần túy chỉ so khớp ngữ nghĩa "mua thiết bị", không phân biệt được số tiền 30 triệu và 50 triệu.
- **Suggested fix:** Hybrid Search BM25 (có Underthesea tokenizer) bắt chính xác từ khóa "30 triệu" kết hợp Cross-Encoder reranker.

### #3
- **Question:** Mentor và buddy của nhân viên mới có thể là cùng một người không?
- **Expected:** Không, Mentor phụ trách chuyên môn, Buddy hỗ trợ hòa nhập văn hóa và phải là 2 nhân sự khác nhau.
- **Got:** Có thể do quản lý phân công linh hoạt.
- **Worst metric:** Context Precision = 0.33
- **Error Tree:** Output sai → Context trả về quy trình Onboarding chung chung → Query OK → `RETRIEVAL_ERROR`
- **Root cause:** Tài liệu nhắc đến Mentor ở mục Đào tạo và Buddy ở mục Văn hóa, Dense search không liên kết được cả 2 entity.
- **Suggested fix:** Bổ sung Entity Extraction trong Module 5 (Enrichment) và dùng Reciprocal Rank Fusion.

### #4
- **Question:** Một nhân viên Senior có 9 năm thâm niên được nghỉ bao nhiêu ngày phép năm?
- **Expected:** 14 ngày phép năm (12 ngày tiêu chuẩn + 2 ngày thâm niên cho mỗi 5 năm).
- **Got:** 12 ngày phép năm.
- **Worst metric:** Context Recall = 0.50
- **Error Tree:** Output sai → Context thiếu dòng quy định thâm niên từ 5 năm trở lên → Query OK → `CHUNKING_ERROR`
- **Root cause:** Bảng thâm niên bị cắt ngang hàng, LLM chỉ đọc được dòng thâm niên dưới 5 năm.
- **Suggested fix:** Dùng Structure-Aware Chunking bảo tồn toàn vẹn bảng Markdown.

### #5
- **Question:** Thông tin lương thuộc cấp độ phân loại dữ liệu nào?
- **Expected:** Dữ liệu Tuyệt mật (Confidential / Restricted).
- **Got:** Dữ liệu Nội bộ (Internal).
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
