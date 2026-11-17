# Phase 9.1 — RAG Evaluation System

Copy `modules/retrieval_evaluator.py` into your project's `modules/` folder and
`data/retrieval_test_cases.json` into its `data/` folder.

Replace each `REPLACE_WITH_...` expected source with the exact TXT filename in
your knowledge base. This code uses your existing `search_knowledge()` function
and the `source` field it returns.

Add the import from `app_integration_snippet.py.txt` alongside your app imports:
`from modules.retrieval_evaluator import evaluate_retrieval, load_test_cases`

Paste the dashboard section from that snippet near the bottom of `app.py`.
It expects the existing `st` and `pd` imports.

Run your app normally, rebuild the knowledge base if needed, then click
**Run Retrieval Evaluation** in the dashboard.

Metrics: Recall@3 (expected source present in top 3), MRR (rank quality),
and Precision@3 (proportion of returned source entries that are expected).
These assess retrieval, not answer correctness. Use carefully labeled, realistic
questions for a meaningful evaluation score.
