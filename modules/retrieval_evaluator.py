"""Phase 9.1: evaluate expected-source retrieval using the app's search function."""
import json, os
from collections import Counter
from modules.knowledge_base import search_knowledge

BASE_DIR=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TEST_FILE=os.path.join(BASE_DIR,"data","retrieval_test_cases.json")

def load_test_cases(file_path=DEFAULT_TEST_FILE):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Evaluation test file not found: {file_path}")
    with open(file_path,"r",encoding="utf-8") as f:
        cases=json.load(f)
    if not isinstance(cases,list):
        raise ValueError("Test cases JSON must contain a list.")
    for i,case in enumerate(cases,1):
        if not isinstance(case,dict) or not case.get("query") or not case.get("expected_sources"):
            raise ValueError(f"Test case {i} needs query and expected_sources.")
        if not isinstance(case["expected_sources"],list):
            raise ValueError(f"expected_sources in test case {i} must be a list.")
    return cases

def evaluate_retrieval(test_cases=None,top_k=3):
    if top_k<1: raise ValueError("top_k must be at least 1.")
    cases=load_test_cases() if test_cases is None else test_cases
    if not cases: raise ValueError("No evaluation test cases found.")
    details=[]; hits=0; rr_total=0.0; precision_total=0.0; source_counts=Counter()
    for case in cases:
        query=case["query"].strip()
        expected={str(x).strip().lower() for x in case["expected_sources"] if str(x).strip()}
        retrieved=search_knowledge(query,top_k=top_k)
        sources=[str(x.get("source","")).strip() for x in retrieved]
        normalized=[x.lower() for x in sources]
        ranks=[rank for rank,source in enumerate(normalized,1) if source in expected]
        hit=bool(ranks); first_rank=min(ranks) if hit else None
        if hit:
            hits+=1
            rr_total+=1.0/first_rank
        relevant=sum(1 for source in normalized if source in expected)
        precision=relevant/len(normalized) if normalized else 0.0
        precision_total+=precision
        source_counts.update(sources)
        details.append({
            "query":query,"expected_sources":sorted(expected),
            "retrieved_sources":sources,f"hit@{top_k}":hit,
            "first_relevant_rank":first_rank,
            f"precision@{top_k}":round(precision,4),
            "distances":[round(float(x["distance"]),4) for x in retrieved if x.get("distance") is not None]
        })
    n=len(cases)
    summary={"total_queries":n,f"recall@{top_k}":round(hits/n,4),
             "mrr":round(rr_total/n,4),f"precision@{top_k}":round(precision_total/n,4),
             "top_retrieved_sources":source_counts.most_common(10)}
    return summary,details
