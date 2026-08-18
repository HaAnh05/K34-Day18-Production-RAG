# Individual Reflection — Lab 18

**Tên:** Hà Anh  
**Module phụ trách:** Toàn bộ Pipeline (M1: Chunking, M2: Search, M3: Reranking, M4: Eval, M5: Enrichment)

---

## 1. Đóng góp kỹ thuật

- Module đã implement: M1, M2, M3, M4, M5 và Pipeline tích hợp.
- Các hàm/class chính đã viết:
  - `chunk_semantic`, `chunk_hierarchical`, `chunk_structure_aware` (M1)
  - `segment_vietnamese`, `BM25Search`, `DenseSearch`, `reciprocal_rank_fusion` (M2)
  - `CrossEncoderReranker`, `FlashrankReranker` (M3)
  - `evaluate_ragas`, `failure_analysis`, `save_report` (M4)
  - `summarize_chunk`, `generate_hypothesis_questions`, `contextual_prepend`, `extract_metadata`, `_enrich_single_call` (M5)
- Số tests pass: 37/37 tests (100% PASS).

## 2. Kiến thức học được

- Khái niệm mới nhất: Cấu trúc Parent-Child indexing trong Hierarchical Chunking và cơ chế Cross-Encoder Joint Self-Attention so với Bi-Encoder Cosine Similarity.
- Điều bất ngờ nhất: Tầm quan trọng của Reciprocal Rank Fusion (RRF) khi kết hợp các hệ thống tìm kiếm có phân phối điểm số hoàn toàn khác nhau mà không cần chuẩn hóa điểm số thủ công.
- Kết nối với bài giảng: Áp dụng toàn bộ kiến trúc 5 tầng của Production RAG từ Retrieval $\rightarrow$ Rerank $\rightarrow$ Context Prepend $\rightarrow$ Generation & RAGAS Triad.

## 3. Khó khăn & Cách giải quyết

- Khó khăn lớn nhất: Tương thích với Google Gemini API qua OpenAI endpoint (lỗi `n > 1` trên metric answer relevancy và giới hạn 15 RPM).
- Cách giải quyết: Đặt `answer_relevancy.strictness = 1`, dùng `LangchainLLMWrapper` + `LangchainEmbeddingsWrapper`, và thiết kế hàm `_enrich_single_call` để gói gọn 4 tác vụ làm giàu trong 1 request JSON duy nhất.
- Thời gian debug: ~45 phút.

## 4. Nếu làm lại

- Sẽ làm khác điều gì: Thêm cơ chế local caching cho embeddings và LLM responses bằng SQLite / diskcache để giảm triệt để thời gian chạy lại test suite.
- Module nào muốn thử tiếp: Thử nghiệm thêm ColBERT / Late Interaction models để so sánh latency và accuracy với Cross-Encoder.

## 5. Tự đánh giá

| Tiêu chí | Tự chấm (1-5) |
|----------|---------------|
| Hiểu bài giảng | 5/5 |
| Code quality | 5/5 |
| Teamwork | 5/5 |
| Problem solving | 5/5 |
