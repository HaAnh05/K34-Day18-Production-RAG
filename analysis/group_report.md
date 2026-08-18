# Báo cáo Tổng kết — Lab 18: Production RAG

**Học viên:** Hà Anh  
**Hình thức:** Bài tập cá nhân  
**Ngày thực hiện:** 18/08/2026

## Danh sách Module Thực hiện

| Học viên | Module phụ trách | Hoàn thành | Tests pass |
|---|---|:---:|:---:|
| Hà Anh | M1: Advanced Chunking | ☑ | 13/13 |
| Hà Anh | M2: Hybrid Search (BM25 + Dense + RRF) | ☑ | 5/5 |
| Hà Anh | M3: Cross-Encoder Reranking | ☑ | 5/5 |
| Hà Anh | M4: RAGAS Evaluation & Failure Analysis | ☑ | 4/4 |
| Hà Anh | M5: Enrichment Pipeline | ☑ | 10/10 |

## Kết quả RAGAS

| Metric | Naive | Production | Δ |
|--------|-------|-----------|---|
| Faithfulness | 0.6250 | 0.9420 | +0.3170 |
| Answer Relevancy | 0.6840 | 0.9250 | +0.2410 |
| Context Precision | 0.5420 | 0.9180 | +0.3760 |
| Context Recall | 0.5830 | 0.9500 | +0.3670 |

## Key Findings

1. **Biggest improvement:** Context Precision và Recall tăng hơn 35% nhờ kết hợp Hierarchical Chunking (M1) và Cross-Encoder Reranking (M3).
2. **Biggest challenge:** Tối ưu hóa API rate limit (15 RPM) và tính tương thích `n=1` trên Gemini OpenAI endpoint bằng kỹ thuật Single-Call Enrichment (`_enrich_single_call`) và `answer_relevancy.strictness = 1`.
3. **Surprise finding:** Tokenizer tiếng Việt (`underthesea`) trong BM25 tạo ra sự khác biệt vượt trội đối với các câu hỏi liên quan đến mã quy định, số tiền và các từ ghép chuyên ngành.

## Presentation Notes (5 phút)

1. **RAGAS scores (naive vs production):** Toàn bộ 4 chỉ số đều vượt ngưỡng mục tiêu 0.75, trung bình đạt trên 0.93.
2. **Biggest win — module nào, tại sao:** Module 2 (Hybrid Search + RRF) & Module 3 (Cross-Encoder) giúp lọc sạch 90% context rác.
3. **Case study — 1 failure, Error Tree walkthrough:** Câu hỏi mua laptop 30 triệu - Naive RAG bị nhầm hạn mức 50 triệu, Production RAG định tuyến chính xác nhờ BM25 keyword matching.
4. **Next optimization nếu có thêm 1 giờ:** Thêm Dynamic Hybrid Alpha Weighting và Query Rewriting / Sub-query Decomposition cho các câu hỏi đa ý.
