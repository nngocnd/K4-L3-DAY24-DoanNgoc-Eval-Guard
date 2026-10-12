from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import asdict, dataclass

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
    """Run RAGAS evaluation.

    Returns {<metric>: mean, "per_question": [EvalResult...], "metadata": {"evaluator_models": [...]}}.
    Rows whose metric came back NaN (evaluator parse/timeout errors) are re-scored;
    a metric that stays NaN raises instead of being replaced by a fake score.
    """
    metric_names = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    if not (len(questions) == len(answers) == len(contexts) == len(ground_truths)):
        raise ValueError("questions/answers/contexts/ground_truths must have equal length")

    import math
    from config import LLM_API_KEY, LLM_BASE_URL, EVAL_LLM_MODEL, EVAL_EMBEDDING_MODEL
    if not LLM_API_KEY:
        raise RuntimeError("Thiếu OPENAI_API_KEY cho RAGAS evaluator")

    from datasets import Dataset
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
    from ragas.run_config import RunConfig

    llm = ChatOpenAI(model=EVAL_LLM_MODEL, api_key=LLM_API_KEY, base_url=LLM_BASE_URL,
                     temperature=0, max_retries=8)
    embeddings = OpenAIEmbeddings(model=EVAL_EMBEDDING_MODEL, api_key=LLM_API_KEY,
                                  base_url=LLM_BASE_URL)
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]

    def _run(idx: list[int]) -> list[dict]:
        dataset = Dataset.from_dict({
            "question": [questions[i] for i in idx], "answer": [answers[i] for i in idx],
            "contexts": [list(contexts[i]) for i in idx],
            "ground_truth": [ground_truths[i] for i in idx],
        })
        result = evaluate(dataset, metrics=metrics, llm=llm, embeddings=embeddings,
                          run_config=RunConfig(max_workers=4, max_retries=10, max_wait=60,
                                               timeout=300))
        df = result.to_pandas()
        return [{m: (float(row[m]) if row.get(m) is not None else float("nan"))
                 for m in metric_names} for _, row in df.iterrows()]

    scores = _run(list(range(len(questions))))
    for attempt in range(2):
        pending = [i for i, s in enumerate(scores) if any(math.isnan(s[m]) for m in metric_names)]
        if not pending:
            break
        print(f"  ↻ Re-scoring {len(pending)} rows with NaN metrics (attempt {attempt + 1})")
        for i, fresh in zip(pending, _run(pending)):
            for m in metric_names:
                if math.isnan(scores[i][m]):
                    scores[i][m] = fresh[m]
    still_nan = [(i, m) for i, s in enumerate(scores) for m in metric_names if math.isnan(s[m])]
    if still_nan:
        raise ValueError(f"RAGAS returned NaN after retries for (row, metric): {still_nan}")

    per_question = [
        EvalResult(question=questions[i], answer=answers[i], contexts=list(contexts[i]),
                   ground_truth=ground_truths[i], **scores[i])
        for i in range(len(questions))
    ]
    aggregate = {m: sum(s[m] for s in scores) / len(scores) for m in metric_names}
    return {**aggregate, "per_question": per_question,
            "metadata": {"evaluator_models": [EVAL_LLM_MODEL, EVAL_EMBEDDING_MODEL]}}

def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    diagnostic_tree = {
        "faithfulness": ("LLM hallucinating", "Tighten prompt, lower temperature"),
        "context_recall": ("Missing relevant chunks", "Improve chunking or add BM25"),
        "context_precision": ("Too many irrelevant chunks", "Add reranking or metadata filter"),
        "answer_relevancy": ("Answer doesn't match question", "Improve prompt template"),
    }
    metric_names = list(diagnostic_tree)

    analyzed = []
    for r in eval_results:
        scores = {m: getattr(r, m) for m in metric_names}
        avg = sum(scores.values()) / len(scores)
        worst_metric = min(scores, key=scores.get)
        diagnosis, suggested_fix = diagnostic_tree[worst_metric]
        analyzed.append({
            "question": r.question,
            "answer": r.answer,
            "ground_truth": r.ground_truth,
            "avg_score": round(avg, 4),
            "worst_metric": worst_metric,
            "score": round(scores[worst_metric], 4),
            "scores": {m: round(v, 4) for m, v in scores.items()},
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
        })

    analyzed.sort(key=lambda x: x["avg_score"])
    return analyzed[:bottom_n]

def save_report(results: dict, failures: list[dict], path: str = "reports/ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
        "per_question": [asdict(r) for r in results.get("per_question", [])],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
