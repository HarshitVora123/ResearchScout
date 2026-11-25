"""Unit tests for Phase 6 — Benchmark Evaluator."""

from app.research.benchmark_evaluator import BenchmarkEvaluator


class TestBenchmarkEvaluator:
    """Test Precision@K, Recall@K, MRR@K, NDCG@K, extraction F1, and ablation runner."""

    def test_precision_at_k(self):
        recommended = ["item1", "item2", "item3", "item4", "item5"]
        relevant = {"item1", "item3", "item7"}

        p5 = BenchmarkEvaluator.precision_at_k(recommended, relevant, k=5)
        assert p5 == 2 / 5

    def test_recall_at_k(self):
        recommended = ["item1", "item2", "item3"]
        relevant = {"item1", "item3"}

        r3 = BenchmarkEvaluator.recall_at_k(recommended, relevant, k=3)
        assert r3 == 1.0

    def test_mrr_at_k(self):
        recommended = ["item1", "item2", "item3"]
        relevant = {"item2"}

        mrr = BenchmarkEvaluator.mrr_at_k(recommended, relevant, k=3)
        assert mrr == 1 / 2

    def test_ndcg_at_k(self):
        recommended = ["item1", "item2", "item3"]
        scores = {"item1": 3.0, "item2": 2.0, "item3": 1.0}

        ndcg = BenchmarkEvaluator.ndcg_at_k(recommended, scores, k=3)
        assert ndcg == 1.0  # Perfect ordering

    def test_evaluate_extraction_f1(self):
        pred = {"title": "PhD Position", "skills": ["Python", "PyTorch"]}
        truth = {"title": "PhD Position", "skills": ["Python", "PyTorch"]}

        metrics = BenchmarkEvaluator.evaluate_extraction(pred, truth)
        assert metrics["f1_score"] == 1.0

    def test_ablation_experiments_runner(self):
        evaluator = BenchmarkEvaluator()
        results = evaluator.run_ablation_experiments()

        assert "Full_System" in results
        assert "no_KnowledgeGraph" in results
        assert results["Full_System"]["MRR@10"] > results["Baseline_RulesOnly"]["MRR@10"]
