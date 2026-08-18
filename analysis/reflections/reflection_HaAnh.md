# Individual Reflection — Lab 18: Production RAG Pipeline

**Học viên:** Hà Anh  
**Hình thức:** Bài tập Cá nhân  
**Phụ trách:** Toàn bộ Pipeline (M1: Chunking, M2: Search, M3: Reranking, M4: Eval, M5: Enrichment)  
**Ngày thực hiện:** 18/08/2026  

---

## Phần 1: Mapping Bài Giảng (Lecture Concept → Code Thực Tế)

Dưới đây là bảng ánh xạ toàn diện giữa các khái niệm lý thuyết trong bài giảng Production RAG và các hàm/lớp đã trực tiếp cài đặt trong mã nguồn:

| Lecture Concept | Module | Hàm / Class cụ thể | Observation & Phân tích thực nghiệm |
|---|:---:|---|---|
| **Semantic Chunking** | M1 | `chunk_semantic()` | Dùng cosine similarity ngưỡng `0.85` (với `all-MiniLM-L6-v2`) giúp nhóm các câu cùng ý trọn vẹn, không bị cắt đứt mạch suy nghĩ giữa đoạn. |
| **Hierarchical Chunking** | M1 | `chunk_hierarchical()` | Tạo cấu trúc Parent (2048 ký tự) và Child (256 ký tự). Đạt hiệu quả tối ưu cho Production nhờ cơ chế: *Search on Child (độ chính xác cao) $\rightarrow$ Return Parent (ngữ cảnh đầy đủ)*. |
| **Structure-Aware Chunking** | M1 | `chunk_structure_aware()` | Dùng Regex nhận diện Markdown headers (`#`, `##`, `###`), bảo toàn trọn vẹn 100% các bảng biểu (Markdown tables), tránh việc bảng lương và bảng hạn mức mua sắm bị xé vụn. |
| **Vietnamese Word Tokenization** | M2 | `segment_vietnamese()` | Tách từ ghép tiếng Việt bằng `underthesea`, giúp BM25 hiểu chính xác các thực thể như "nghỉ_phép", "bảo_hiểm_y_tế", "tạm_ứng" thay vì các từ đơn lẻ vô nghĩa. |
| **BM25 + Dense Fusion (RRF)** | M2 | `reciprocal_rank_fusion()` | Áp dụng công thức $RRF(d) = \sum \frac{1}{60 + rank + 1}$. Kết hợp mượt mà ưu thế bắt chính xác từ khóa số tiền ("30 triệu") của BM25 và hiểu ngữ nghĩa của Dense BGE-M3 mà không cần chuẩn hóa phân phối điểm số. |
| **Cross-Encoder Reranking** | M3 | `CrossEncoderReranker.rerank()` | Mô hình `BAAI/bge-reranker-v2-m3` cho phép Joint Self-Attention giữa Query và Document, lọc sạch 85% context nhiễu, thu hẹp từ Top-20 về Top-3 tài liệu tinh túy nhất. |
| **RAGAS 4 Metrics Triad** | M4 | `evaluate_ragas()` | Đánh giá định lượng 4 chỉ số: Faithfulness (0.8615), Answer Relevancy (0.7742), Context Precision (0.7833), Context Recall (0.8417). Cả 4 chỉ số đều vượt ngưỡng mục tiêu 0.75. |
| **Diagnostic Tree Failure Analysis** | M4 | `failure_analysis()` | Tự động phân loại nguyên nhân cốt lõi của các câu trả lời sai: Context Recall thấp $\rightarrow$ `CHUNKING_ERROR`, Context Precision thấp $\rightarrow$ `RETRIEVAL_ERROR`, Faithfulness thấp $\rightarrow$ `GENERATION_ERROR`. |
| **Contextual Prepending** | M5 | `contextual_prepend()` | Gắn 1 câu ngữ cảnh nguồn vào đầu chunk (Anthropic style), giải quyết triệt để vấn đề mất ngữ cảnh tài liệu nguồn (Context Loss). |
| **Hypothesis Questions (HyQA)** | M5 | `generate_hypothesis_questions()` | LLM sinh 2-3 câu hỏi tiềm năng cho mỗi chunk, bắc cầu khoảng cách từ vựng (Vocabulary Gap) giữa câu hỏi của người dùng và văn phong tài liệu. |
| **Single-Call Enrichment** | M5 | `_enrich_single_call()` | Gom 4 tác vụ làm giàu (Summary, HyQA, Context Prepend, Metadata) vào 1 API call JSON duy nhất, tiết kiệm 75% chi phí API và giảm tối đa nguy cơ dính Rate Limit (15 RPM). |

---

## Phần 2: Khó Khăn Gặp Phải & Cách Giải Quyết

Trong quá trình xây dựng hệ thống, tôi đã gặp và tự giải quyết các vấn đề kỹ thuật lớn sau:

### 1. Lỗi tương thích Google Gemini API qua OpenAI Client (`n > 1` & Rate Limit 15 RPM)
- **Thông báo lỗi (Exact error message):**
  ```text
  BadRequestError: Error code: 400 - [{'error': {'code': 400, 'message': 'Generating multiple candidate generations (n > 1) is not supported by the model.', 'status': 'INVALID_ARGUMENT'}}]
  RateLimitError: 429 Resource has been exhausted (check quota: 15 RPM limit).
  ```
- **Cách debug:**
  1. Khi chạy RAGAS evaluation, metric `answer_relevancy` mặc định yêu cầu LLM sinh ra $n=3$ câu hỏi giả định để đối chiếu embedding. Tuy nhiên, endpoint Google Gemini qua giao thức OpenAI không hỗ trợ tham số $n > 1$.
  2. Module 5 nếu gọi 4 API riêng biệt cho 104 chunks ($104 \times 4 = 416$ calls) sẽ lập tức làm cạn kiệt hạn mức 15 requests/phút (RPM).
- **Giải pháp xử lý:**
  - Thiết lập thuộc tính `answer_relevancy.strictness = 1` trong `src/m4_eval.py` để ép RAGAS chỉ sinh $n=1$ câu trả lời tại một thời điểm.
  - Sử dụng `LangchainLLMWrapper(ChatOpenAI(...))` kết hợp `LangchainEmbeddingsWrapper(HuggingFaceEmbeddings(...))` để nhúng embedding cục bộ bằng MiniLM thay vì gọi API ngoài.
  - Thiết kế hàm `_enrich_single_call()` gom toàn bộ 4 tác vụ làm giàu vào 1 prompt JSON duy nhất kèm cấu hình `RunConfig(max_workers=1, timeout=60, max_retries=10)`.

### 2. Sự cố Regex Parse Output Pytest trong Script Thẩm Định `check_lab.py`
- **Thông báo lỗi:** `ValueError: invalid literal for int() with base 10: '=================='`
- **Cách debug & sửa:** Pytest trên Windows trả về chuỗi summary có chứa các ký tự viền `===` và warning deprecation. Đã refactor hàm `run_tests()` trong `check_lab.py` sang dùng `re.search(r'(\d+)\s+passed', output)` giúp bắt chính xác 100% kết quả kiểm thử.

---

## Phần 3: Action Plan Ứng Dụng Vào Dự Án Thực Tế (Project Plan)

## Project: Trợ Lý Pháp Lý & Quy Chế Nội Bộ Doanh Nghiệp (Enterprise Legal & Policy Chatbot)

### 1. Hiện trạng & Vấn đề hiện tại
- **RAG Pipeline hiện tại:** Naive RAG dùng Paragraph Chunking thô và Vector Search thuần túy (ChromaDB + OpenAI Embeddings).
- **Vấn đề tồn đọng:**
  - Các bảng biểu phân quyền duyệt ngân sách và phụ lục hợp đồng bị cắt đứt giữa chừng khiến câu trả lời bị sai số tiền.
  - Các chính sách có nhiều phiên bản (v2023 vs v2024) thường bị LLM trả về phiên bản cũ do ngữ nghĩa vector quá giống nhau.
  - Tìm kiếm các câu hỏi chứa mã điều khoản luật (ví dụ: *Điều 13 Nghị định 13*) bị trượt do Dense Search không bắt chính xác từ khóa.

### 2. Kế hoạch áp dụng các kỹ thuật từ Lab 18
1. **Chunking Strategy:** 
   - Sử dụng **Structure-Aware Chunking** cho các văn bản quy định có cấu trúc Chương/Điều/Mục rõ ràng nhằm bảo tồn 100% bảng biểu.
   - Kết hợp **Hierarchical Chunking (Parent 2048 / Child 256)** cho các tài liệu sổ tay hướng dẫn dạng văn xuôi.
2. **Search Strategy:**
   - Triển khai **Hybrid Search (BM25 + Dense Qdrant)**. BM25 sử dụng `underthesea` tách từ để bắt chính xác số hiệu văn bản và mốc thời gian/số tiền.
   - Dung hợp kết quả bằng **Reciprocal Rank Fusion (RRF)** ($k=60$).
3. **Reranking Strategy:**
   - Tích hợp mô hình Cross-Encoder `BAAI/bge-reranker-v2-m3` để lọc Top-20 văn bản thu về từ Hybrid Search xuống Top-3 văn bản đưa vào LLM Context.
4. **Data Enrichment Strategy:**
   - Áp dụng **Contextual Prepending** và **Auto Metadata Extraction** (trích xuất ngày hiệu lực, phiên bản, phòng ban) trong giai đoạn Ingestion để lọc chính xác văn bản còn hiệu lực.
5. **Evaluation Framework:**
   - Xây dựng bộ test benchmark nội bộ gồm 50 câu hỏi đa dạng (Lookup, Multi-hop, Version Superseding, Negation) và đo lường định kỳ bằng **RAGAS Triad**.

### 3. Lộ trình triển khai (Timeline)
- **Tuần 1:** Chuẩn hóa Corpus dữ liệu, tích hợp `pypdf` OCR và triển khai Module Structure-Aware & Hierarchical Chunking.
- **Tuần 2:** Xây dựng cụm Qdrant Vector DB, tích hợp BM25 Tiếng Việt và thuật toán RRF.
- **Tuần 3:** Tích hợp Cross-Encoder Reranker, tinh chỉnh Prompt bảo vệ chống ảo giác (Hallucination Guardrails).
- **Tuần 4:** Chạy RAGAS benchmark, phân tích Failure Tree và triển khai lên môi trường thử nghiệm UAT.

---

## Phần 4: Tự Đánh Giá Cá Nhân

| Tiêu chí | Tự chấm (1-5) | Ghi chú & Minh chứng |
|---|:---:|---|
| **Hiểu bài giảng** | **5 / 5** | Nắm vững toàn bộ 5 tầng kiến trúc Production RAG và bản chất toán học của RRF, Cross-Encoder, RAGAS Triad. |
| **Chất lượng Code (Code Quality)** | **5 / 5** | Code sạch, cấu trúc module rõ ràng, xử lý typing đầy đủ, vượt qua 37/37 tests (100% PASS), 0 TODO sót lại. |
| **Khả năng giải quyết vấn đề (Problem Solving)** | **5 / 5** | Tự xử lý triệt để lỗi Gemini API rate limit, strictness=1 và tối ưu hàm Single-Call JSON. |
| **Tính ứng dụng thực tế (Practical Impact)** | **5 / 5** | Kế hoạch dự án chi tiết, có tính khả thi cao và giải quyết đúng các bài toán RAG doanh nghiệp. |
