"""
JourneyX Evaluation Metrics Script
====================================
Computes ROUGE, BLEU, and BERT Score on the 72 frozen eval queries.
Also runs RAG vs Vanilla LLM comparison and Top-K retrieval analysis.

Usage:
    python scripts/run_evaluation_metrics.py [--limit N] [--bert] [--topk] [--vanilla]

Options:
    --limit N     Only evaluate first N queries (default: all 72)
    --bert        Also compute BERT score (requires GPU or is slow on CPU)
    --topk        Run Top-K retrieval analysis (K=1,3,5)
    --vanilla     Run RAG vs Vanilla LLM comparison
    --dry-run     Use heuristic planner (no live LLM calls)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

os.environ.setdefault("JOURNEYX_EMBEDDING_FALLBACK", "true")
os.environ.setdefault("JOURNEYX_DISABLE_RERANK", "true")


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_eval_set(path: Path) -> list[dict]:
    items = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def run_agent(query: str, dry_run: bool = False) -> dict:
    """Run the JourneyX agent on a single query."""
    if dry_run:
        os.environ["JOURNEYX_AGENT_DRY_RUN"] = "true"
    else:
        os.environ["JOURNEYX_AGENT_DRY_RUN"] = "false"

    from journeyx.orchestration.graph import run_turn
    try:
        result = run_turn(query)
        return result
    except Exception as exc:
        return {"response": "", "status": "error", "error": str(exc)}


def run_vanilla_llm(query: str) -> str:
    """Run vanilla LLM (no RAG, no tools) on a single query."""
    try:
        from journeyx.llm.client import ChatMessage, LLMClient
        llm = LLMClient()
        if not llm.configured:
            return "[vanilla_llm_not_configured]"
        resp = llm.chat(
            [
                ChatMessage(
                    role="system",
                    content="You are a travel planning assistant. Answer the user's question.",
                ),
                ChatMessage(role="user", content=query),
            ],
            temperature=0.3,
        )
        return resp.content
    except Exception as exc:
        return f"[error: {exc}]"


# ── ROUGE ─────────────────────────────────────────────────────────────────────

def compute_rouge(predictions: list[str], references: list[str]) -> dict[str, float]:
    """Compute ROUGE-1, ROUGE-2, ROUGE-L F1 scores."""
    try:
        from rouge_score import rouge_scorer
        scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
        r1_scores, r2_scores, rl_scores = [], [], []
        for pred, ref in zip(predictions, references):
            if not pred.strip() or not ref.strip():
                continue
            scores = scorer.score(ref, pred)
            r1_scores.append(scores["rouge1"].fmeasure)
            r2_scores.append(scores["rouge2"].fmeasure)
            rl_scores.append(scores["rougeL"].fmeasure)
        n = max(len(r1_scores), 1)
        return {
            "rouge1": round(sum(r1_scores) / n, 4),
            "rouge2": round(sum(r2_scores) / n, 4),
            "rougeL": round(sum(rl_scores) / n, 4),
            "n_scored": n,
        }
    except ImportError:
        print("  [WARN] rouge-score not installed. Run: pip install rouge-score")
        return {"rouge1": 0.0, "rouge2": 0.0, "rougeL": 0.0, "n_scored": 0}


# ── BLEU ──────────────────────────────────────────────────────────────────────

def compute_bleu(predictions: list[str], references: list[str]) -> dict[str, float]:
    """Compute corpus BLEU score."""
    try:
        import nltk
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt", quiet=True)
        try:
            nltk.data.find("tokenizers/punkt_tab")
        except LookupError:
            nltk.download("punkt_tab", quiet=True)

        from nltk.translate.bleu_score import SmoothingFunction, corpus_bleu, sentence_bleu

        smoothie = SmoothingFunction().method4
        sentence_scores = []
        for pred, ref in zip(predictions, references):
            if not pred.strip() or not ref.strip():
                continue
            pred_tokens = nltk.word_tokenize(pred.lower())
            ref_tokens = nltk.word_tokenize(ref.lower())
            score = sentence_bleu([ref_tokens], pred_tokens, smoothing_function=smoothie)
            sentence_scores.append(score)

        n = max(len(sentence_scores), 1)
        avg_bleu = sum(sentence_scores) / n

        return {
            "bleu": round(avg_bleu, 4),
            "n_scored": n,
        }
    except ImportError:
        print("  [WARN] nltk not installed. Run: pip install nltk")
        return {"bleu": 0.0, "n_scored": 0}


# ── BERT Score ────────────────────────────────────────────────────────────────

def compute_bert_score(predictions: list[str], references: list[str]) -> dict[str, float]:
    """Compute BERT score (semantic similarity). Requires GPU for speed."""
    try:
        from bert_score import score as bert_score_fn
        print("  Computing BERT score (this may take a while on CPU)...")
        valid_pairs = [(p, r) for p, r in zip(predictions, references) if p.strip() and r.strip()]
        if not valid_pairs:
            return {"bert_precision": 0.0, "bert_recall": 0.0, "bert_f1": 0.0, "n_scored": 0}
        preds, refs = zip(*valid_pairs)
        P, R, F1 = bert_score_fn(list(preds), list(refs), lang="en", verbose=False)
        return {
            "bert_precision": round(P.mean().item(), 4),
            "bert_recall": round(R.mean().item(), 4),
            "bert_f1": round(F1.mean().item(), 4),
            "n_scored": len(valid_pairs),
        }
    except ImportError:
        print("  [WARN] bert-score not installed. Run: pip install bert-score")
        return {"bert_precision": 0.0, "bert_recall": 0.0, "bert_f1": 0.0, "n_scored": 0}
    except Exception as exc:
        print(f"  [WARN] BERT score failed: {exc}")
        return {"bert_precision": 0.0, "bert_recall": 0.0, "bert_f1": 0.0, "n_scored": 0}


# ── Top-K Retrieval Analysis ──────────────────────────────────────────────────

def run_topk_analysis(eval_items: list[dict]) -> dict[str, Any]:
    """Compare retrieval recall at K=1, 3, 5 using labeled queries."""
    print("\n[Top-K Retrieval Analysis]")
    labeled = [e for e in eval_items if e.get("relevant_doc_ids")]
    if not labeled:
        print("  No labeled queries found for retrieval analysis.")
        return {}

    try:
        from journeyx.rag.models import SearchRequest
        from journeyx.rag.retrieve import load_retriever

        retriever = load_retriever()
        results: dict[str, list[float]] = {"recall@1": [], "recall@3": [], "recall@5": []}

        for item in labeled:
            query = item["query"]
            relevant = set(item["relevant_doc_ids"])
            dest_id = None
            # Try to infer dest_id from relevant doc IDs
            for doc_id in relevant:
                if "jaipur" in doc_id:
                    dest_id = "dest_jaipur"
                elif "goa" in doc_id:
                    dest_id = "dest_goa"
                elif "manali" in doc_id:
                    dest_id = "dest_manali"
                elif "delhi" in doc_id:
                    dest_id = "dest_delhi"
                elif "kochi" in doc_id:
                    dest_id = "dest_kochi"
                if dest_id:
                    break

            for k in [1, 3, 5]:
                hits = retriever.search(SearchRequest(query=query, dest_id=dest_id, top_k=k))
                retrieved_ids = {h.doc_id for h in hits}
                recall = len(relevant & retrieved_ids) / len(relevant) if relevant else 0.0
                results[f"recall@{k}"].append(recall)

        summary = {
            k: round(sum(v) / max(len(v), 1), 4)
            for k, v in results.items()
        }
        summary["n_labeled_queries"] = len(labeled)
        print(f"  Recall@1:  {summary['recall@1']:.4f}")
        print(f"  Recall@3:  {summary['recall@3']:.4f}")
        print(f"  Recall@5:  {summary['recall@5']:.4f}")
        print(f"  Queries:   {summary['n_labeled_queries']}")
        return summary

    except Exception as exc:
        print(f"  [ERROR] Top-K analysis failed: {exc}")
        return {"error": str(exc)}


# ── Main Evaluation Loop ──────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="JourneyX Evaluation Metrics")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of queries")
    parser.add_argument("--bert", action="store_true", help="Compute BERT score")
    parser.add_argument("--topk", action="store_true", help="Run Top-K retrieval analysis")
    parser.add_argument("--vanilla", action="store_true", help="Run RAG vs Vanilla LLM comparison")
    parser.add_argument("--dry-run", action="store_true", help="Use heuristic planner (no LLM)")
    args = parser.parse_args()

    eval_path = ROOT / "data/eval/eval_v1.jsonl"
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)

    print(f"Loading eval set from {eval_path}")
    eval_items = load_eval_set(eval_path)
    if args.limit:
        eval_items = eval_items[: args.limit]
    print(f"Evaluating {len(eval_items)} queries\n")

    # ── Run agent on all queries ──────────────────────────────────────────────
    print("[Agent Evaluation]")
    agent_results = []
    predictions_rag: list[str] = []
    references: list[str] = []
    task_completions = 0
    failure_counts: dict[str, int] = {}

    for i, item in enumerate(eval_items):
        query = item["query"]
        ref = item.get("reference_answer_short", "")
        print(f"  [{i+1:02d}/{len(eval_items)}] {item['category']:20s} | {query[:60]}")

        t0 = time.perf_counter()
        result = run_agent(query, dry_run=args.dry_run)
        latency = time.perf_counter() - t0

        response = result.get("response", "")
        status = result.get("status", "error")

        # Determine success
        category = item.get("category", "")
        expected_refusal = item.get("expected_refusal", False)
        success = False
        failure_class = "ok"

        if expected_refusal:
            success = status == "refuse"
            failure_class = "refusal_miss" if not success else "ok"
        elif category == "clarify":
            success = status == "clarify"
            failure_class = "clarify_miss" if not success else "ok"
        elif status == "error":
            success = False
            failure_class = "agent_error"
        elif not response or len(response) < 20:
            success = False
            failure_class = "empty_response"
        else:
            success = True
            failure_class = "ok"

        if success:
            task_completions += 1
        failure_counts[failure_class] = failure_counts.get(failure_class, 0) + 1

        agent_results.append({
            "id": item["id"],
            "query": query,
            "category": category,
            "status": status,
            "success": success,
            "failure_class": failure_class,
            "response_length": len(response),
            "step_count": result.get("step_count", 0),
            "tool_calls": result.get("tool_calls", 0),
            "latency_s": round(latency, 3),
            "planner_intent": result.get("planner_intent"),
        })

        predictions_rag.append(response)
        references.append(ref)

    n = len(eval_items)
    task_completion_rate = task_completions / n if n > 0 else 0.0
    avg_steps = sum(r["step_count"] for r in agent_results) / max(n, 1)
    avg_tools = sum(r["tool_calls"] for r in agent_results) / max(n, 1)
    avg_latency = sum(r["latency_s"] for r in agent_results) / max(n, 1)

    print(f"\n  Task completion rate: {task_completion_rate:.1%} ({task_completions}/{n})")
    print(f"  Avg steps/query:      {avg_steps:.2f}")
    print(f"  Avg tool calls/query: {avg_tools:.2f}")
    print(f"  Avg latency (s):      {avg_latency:.2f}")
    print(f"  Failure taxonomy:     {failure_counts}")

    # ── ROUGE ─────────────────────────────────────────────────────────────────
    print("\n[ROUGE Metrics]")
    rouge_scores = compute_rouge(predictions_rag, references)
    print(f"  ROUGE-1: {rouge_scores['rouge1']:.4f}")
    print(f"  ROUGE-2: {rouge_scores['rouge2']:.4f}")
    print(f"  ROUGE-L: {rouge_scores['rougeL']:.4f}")

    # ── BLEU ──────────────────────────────────────────────────────────────────
    print("\n[BLEU Metrics]")
    bleu_scores = compute_bleu(predictions_rag, references)
    print(f"  BLEU:    {bleu_scores['bleu']:.4f}")

    # ── BERT Score (optional) ─────────────────────────────────────────────────
    bert_scores: dict[str, float] = {}
    if args.bert:
        print("\n[BERT Score]")
        bert_scores = compute_bert_score(predictions_rag, references)
        print(f"  BERT-P:  {bert_scores.get('bert_precision', 0):.4f}")
        print(f"  BERT-R:  {bert_scores.get('bert_recall', 0):.4f}")
        print(f"  BERT-F1: {bert_scores.get('bert_f1', 0):.4f}")

    # ── Vanilla LLM Comparison (optional) ────────────────────────────────────
    vanilla_comparison: dict[str, Any] = {}
    if args.vanilla:
        print("\n[RAG vs Vanilla LLM Comparison]")
        predictions_vanilla: list[str] = []
        vanilla_completions = 0

        for i, item in enumerate(eval_items):
            query = item["query"]
            print(f"  [vanilla {i+1:02d}/{len(eval_items)}] {query[:60]}")
            vanilla_resp = run_vanilla_llm(query)
            predictions_vanilla.append(vanilla_resp)

            # Simple success check: non-empty response
            if vanilla_resp and len(vanilla_resp) > 20 and not vanilla_resp.startswith("["):
                vanilla_completions += 1

        vanilla_rouge = compute_rouge(predictions_vanilla, references)
        vanilla_bleu = compute_bleu(predictions_vanilla, references)
        vanilla_completion_rate = vanilla_completions / n if n > 0 else 0.0

        vanilla_comparison = {
            "task_completion_rate": round(vanilla_completion_rate, 4),
            "rouge1": vanilla_rouge["rouge1"],
            "rouge2": vanilla_rouge["rouge2"],
            "rougeL": vanilla_rouge["rougeL"],
            "bleu": vanilla_bleu["bleu"],
        }

        print(f"\n  Vanilla LLM task completion: {vanilla_completion_rate:.1%}")
        print(f"  Vanilla ROUGE-1: {vanilla_rouge['rouge1']:.4f}  |  RAG ROUGE-1: {rouge_scores['rouge1']:.4f}")
        print(f"  Vanilla ROUGE-L: {vanilla_rouge['rougeL']:.4f}  |  RAG ROUGE-L: {rouge_scores['rougeL']:.4f}")
        print(f"  Vanilla BLEU:    {vanilla_bleu['bleu']:.4f}  |  RAG BLEU:    {bleu_scores['bleu']:.4f}")

    # ── Top-K Retrieval Analysis (optional) ──────────────────────────────────
    topk_results: dict[str, Any] = {}
    if args.topk:
        topk_results = run_topk_analysis(eval_items)

    # ── Save Results ──────────────────────────────────────────────────────────
    output = {
        "eval_set": str(eval_path.relative_to(ROOT)),
        "n_queries": n,
        "dry_run": args.dry_run,
        "agent_metrics": {
            "task_completion_rate": round(task_completion_rate, 4),
            "task_completions": task_completions,
            "avg_steps_per_query": round(avg_steps, 3),
            "avg_tool_calls_per_query": round(avg_tools, 3),
            "avg_latency_s": round(avg_latency, 3),
            "failure_taxonomy": failure_counts,
        },
        "lexical_metrics": {
            "rouge1": rouge_scores["rouge1"],
            "rouge2": rouge_scores["rouge2"],
            "rougeL": rouge_scores["rougeL"],
            "bleu": bleu_scores["bleu"],
            "n_scored": rouge_scores.get("n_scored", n),
        },
        "semantic_metrics": bert_scores if bert_scores else {"note": "Run with --bert to compute"},
        "rag_vs_vanilla": vanilla_comparison if vanilla_comparison else {"note": "Run with --vanilla to compute"},
        "topk_retrieval": topk_results if topk_results else {"note": "Run with --topk to compute"},
        "per_query_results": agent_results,
    }

    out_path = reports_dir / "evaluation_metrics.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Results saved to {out_path.relative_to(ROOT)}")

    # ── Print Summary Table ───────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"{'Metric':<35} {'Value':>10}")
    print("-" * 60)
    print(f"{'Task Completion Rate':<35} {task_completion_rate:>9.1%}")
    print(f"{'Avg Steps / Query':<35} {avg_steps:>10.2f}")
    print(f"{'Avg Tool Calls / Query':<35} {avg_tools:>10.2f}")
    print(f"{'ROUGE-1':<35} {rouge_scores['rouge1']:>10.4f}")
    print(f"{'ROUGE-2':<35} {rouge_scores['rouge2']:>10.4f}")
    print(f"{'ROUGE-L':<35} {rouge_scores['rougeL']:>10.4f}")
    print(f"{'BLEU':<35} {bleu_scores['bleu']:>10.4f}")
    if bert_scores:
        print(f"{'BERT-F1':<35} {bert_scores.get('bert_f1', 0):>10.4f}")
    if topk_results and "recall@1" in topk_results:
        print(f"{'Retrieval Recall@1':<35} {topk_results['recall@1']:>10.4f}")
        print(f"{'Retrieval Recall@3':<35} {topk_results['recall@3']:>10.4f}")
        print(f"{'Retrieval Recall@5':<35} {topk_results['recall@5']:>10.4f}")
    if vanilla_comparison:
        print("-" * 60)
        print("RAG vs Vanilla LLM:")
        print(f"{'  RAG Task Completion':<35} {task_completion_rate:>9.1%}")
        print(f"{'  Vanilla Task Completion':<35} {vanilla_comparison.get('task_completion_rate', 0):>9.1%}")
        print(f"{'  RAG ROUGE-1':<35} {rouge_scores['rouge1']:>10.4f}")
        print(f"{'  Vanilla ROUGE-1':<35} {vanilla_comparison.get('rouge1', 0):>10.4f}")
    print("=" * 60)


if __name__ == "__main__":
    main()