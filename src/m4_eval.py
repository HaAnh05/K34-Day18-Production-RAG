from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation."""
    from config import OPENAI_API_KEY, OPENAI_BASE_URL, LLM_MODEL

    default_result = {
        "faithfulness": 0.0,
        "answer_relevancy": 0.0,
        "context_precision": 0.0,
        "context_recall": 0.0,
        "per_question": []
    }

    if not questions:
        return default_result

    try:
        from ragas import evaluate, RunConfig
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from datasets import Dataset

        # Set strictness=1 so Gemini doesn't reject n>1 candidate generations
        answer_relevancy.strictness = 1

        dataset = Dataset.from_dict({
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        })

        eval_kwargs = {}
        if OPENAI_API_KEY:
            from langchain_openai import ChatOpenAI
            from langchain_community.embeddings import HuggingFaceEmbeddings
            from ragas.llms import LangchainLLMWrapper
            from ragas.embeddings import LangchainEmbeddingsWrapper

            chat_llm = ChatOpenAI(
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_BASE_URL,
                model=LLM_MODEL,
                temperature=0.0
            )
            ragas_llm = LangchainLLMWrapper(chat_llm)
            hf_emb = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            ragas_emb = LangchainEmbeddingsWrapper(hf_emb)

            eval_kwargs["llm"] = ragas_llm
            eval_kwargs["embeddings"] = ragas_emb
            eval_kwargs["run_config"] = RunConfig(max_workers=1, timeout=60, max_retries=10, max_wait=60)

        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            **eval_kwargs
        )
        df = result.to_pandas()
        per_question = [
            EvalResult(
                question=str(row["question"]),
                answer=str(row["answer"]),
                contexts=list(row["contexts"]),
                ground_truth=str(row["ground_truth"]),
                faithfulness=float(row.get("faithfulness", 0.0) if not (isinstance(row.get("faithfulness"), float) and str(row.get("faithfulness")) == "nan") else 0.0),
                answer_relevancy=float(row.get("answer_relevancy", 0.0) if not (isinstance(row.get("answer_relevancy"), float) and str(row.get("answer_relevancy")) == "nan") else 0.0),
                context_precision=float(row.get("context_precision", 0.0) if not (isinstance(row.get("context_precision"), float) and str(row.get("context_precision")) == "nan") else 0.0),
                context_recall=float(row.get("context_recall", 0.0) if not (isinstance(row.get("context_recall"), float) and str(row.get("context_recall")) == "nan") else 0.0),
            )
            for _, row in df.iterrows()
        ]

        def _mean(metric_name):
            vals = [getattr(r, metric_name) for r in per_question if getattr(r, metric_name) is not None]
            return float(sum(vals) / len(vals)) if vals else 0.0

        return {
            "faithfulness": round(_mean("faithfulness"), 4),
            "answer_relevancy": round(_mean("answer_relevancy"), 4),
            "context_precision": round(_mean("context_precision"), 4),
            "context_recall": round(_mean("context_recall"), 4),
            "per_question": per_question,
        }
    except Exception as e:
        print(f"  ⚠️  RAGAS evaluation failed: {e}")
        return default_result


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    if not eval_results:
        return []

    diagnostic_tree = {
        "faithfulness": ("LLM hallucinating / ungrounded answer", "Tighten prompt, lower temperature"),
        "context_recall": ("Missing relevant chunks in retrieval", "Improve chunking or add BM25/Dense fusion"),
        "context_precision": ("Too many irrelevant chunks in context", "Add reranking or metadata filter"),
        "answer_relevancy": ("Answer doesn't match question intent", "Improve prompt template and instructions"),
    }

    scored_items = []
    for r in eval_results:
        metrics = {
            "faithfulness": r.faithfulness,
            "answer_relevancy": r.answer_relevancy,
            "context_precision": r.context_precision,
            "context_recall": r.context_recall,
        }
        avg_score = sum(metrics.values()) / len(metrics)
        worst_metric = min(metrics.keys(), key=lambda k: metrics[k])
        diagnosis, suggested_fix = diagnostic_tree.get(
            worst_metric, ("Unknown issue", "Review pipeline logs")
        )
        scored_items.append({
            "question": r.question,
            "answer": r.answer,
            "ground_truth": r.ground_truth,
            "worst_metric": worst_metric,
            "score": float(metrics[worst_metric]),
            "avg_score": float(avg_score),
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
        })

    scored_items.sort(key=lambda x: x["avg_score"])
    return scored_items[:bottom_n]


def save_report(results: dict, failures: list[dict], path: str = "ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
