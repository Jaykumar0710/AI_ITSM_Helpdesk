"""
Evaluate the project's Groq-based IT helpdesk classifier and analyzer.

IMPORTANT:
- This script makes live Groq API calls and may incur API usage/cost.
- It does NOT run automatically when downloaded.
- Synthetic labels must be reviewed/adjudicated by humans before research claims.
- Priority mapping for analyzer is explicit and configurable below.
"""

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from groq import Groq
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)

MODEL_NAME = "openai/gpt-oss-20b"

# Explicit working mapping for comparing the analyzer's P1-P4 scale
# with the classifier's Low/Medium/High/Critical scale.
# Confirm this mapping with your supervisor/reviewers before final reporting.
ANALYZER_PRIORITY_MAP = {
    "P1": "Critical",
    "P2": "High",
    "P3": "Medium",
    "P4": "Low",
}

VALID_CATEGORIES = {
    "Network Connectivity", "Hardware", "Software", "Account and Access",
    "Security", "Email", "Printer", "Other"
}


def safe_json_loads(content):
    """Parse JSON returned by Groq; fail clearly if the response is invalid."""
    if not content:
        raise ValueError("Empty model response")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Recover a JSON object if the provider includes surrounding whitespace/text.
        start, end = content.find("{"), content.rfind("}")
        if start >= 0 and end > start:
            return json.loads(content[start:end + 1])
        raise


def call_classifier(client, query):
    prompt = f"""
You are an IT Service Management ticket classification assistant.
Analyze this IT support issue.

USER ISSUE:
{query}

Allowed categories:
- Network Connectivity
- Hardware
- Software
- Account and Access
- Security
- Email
- Printer
- Other

Allowed priorities: Low, Medium, High, Critical.

Priority guidelines:
Low: Minor inconvenience with a workaround.
Medium: A single user's issue affecting normal work.
High: Important functionality unavailable or significant productivity impact.
Critical: Major business disruption, widespread outage, or suspected serious security incident.

Do not classify an ordinary Wi-Fi problem as Critical without evidence of widespread impact.
Return only a JSON object with:
"title", "category", "priority", "summary", "recommended_action".
"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_completion_tokens=500,
        response_format={"type": "json_object"},
    )
    return safe_json_loads(response.choices[0].message.content)


def call_analyzer(client, query, ai_response=""):
    prompt = f"""
You are an intelligent IT helpdesk analyst.
Analyze the user's IT support issue.

User issue:
{query}

AI support response:
{ai_response}

Return ONLY a valid JSON object with:
"sentiment": "Frustrated | Neutral | Satisfied",
"urgency": "Low | Medium | High | Critical",
"priority": "P1 | P2 | P3 | P4",
"escalation_required": true,
"reason": "Short explanation",
"recommended_action": "Recommended next action"

Priority guidelines:
P1: Critical business outage, security incident, or major service disruption.
P2: High-impact issue affecting important work.
P3: Normal issue affecting an individual user.
P4: Low-impact request or informational query.

Urgency guidelines:
Critical: Major outage or serious security incident.
High: User cannot perform important work.
Medium: Work is affected but a workaround exists.
Low: Minor inconvenience or general information.

Sentiment:
Frustrated: User expresses anger, frustration, or distress.
Neutral: User expresses no strong emotion.
Satisfied: User expresses appreciation or satisfaction.

Do not classify an issue as critical only because the user uses emotional or urgent language.
Escalation should be recommended for critical incidents, serious security incidents,
or high-impact unresolved issues.
"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a precise ITSM analyst. Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=500,
    )
    return safe_json_loads(response.choices[0].message.content)


def normalize_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def add_metric_rows(rows, task, y_true, y_pred):
    valid = [
        (str(a), str(b)) for a, b in zip(y_true, y_pred)
        if normalize_text(a) and normalize_text(b)
    ]
    if not valid:
        return
    truth, pred = zip(*valid)
    report = classification_report(
        truth, pred, output_dict=True, zero_division=0
    )
    rows.append({
        "Task": task,
        "N": len(valid),
        "Accuracy": accuracy_score(truth, pred),
        "Macro_Precision": precision_recall_fscore_support(
            truth, pred, average="macro", zero_division=0
        )[0],
        "Macro_Recall": precision_recall_fscore_support(
            truth, pred, average="macro", zero_division=0
        )[1],
        "Macro_F1": precision_recall_fscore_support(
            truth, pred, average="macro", zero_division=0
        )[2],
    })
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Run live Groq evaluation for the synthetic IT helpdesk scenarios."
    )
    parser.add_argument("--input", required=True, help="Path to the dataset CSV")
    parser.add_argument("--output-dir", default="evaluation_results")
    parser.add_argument("--start", type=int, default=0, help="Zero-based start row")
    parser.add_argument("--limit", type=int, default=None, help="Rows to evaluate; use 3 for a smoke test")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between scenario API calls")
    parser.add_argument("--resume", action="store_true", help="Resume from existing predictions.csv")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise SystemExit(
            "GROQ_API_KEY is missing. Add it to a .env file or environment variable."
        )

    data = pd.read_csv(args.input)
    required = [
        "Scenario_ID", "User_Query", "Expected_Category", "Expected_Priority",
        "Expected_Sentiment", "Expected_Urgency", "Expected_Escalation"
    ]
    missing = [c for c in required if c not in data.columns]
    if missing:
        raise SystemExit(f"Dataset is missing required columns: {missing}")

    data = data.iloc[args.start:]
    if args.limit is not None:
        data = data.head(args.limit)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_path = out_dir / "predictions.csv"

    if args.resume and pred_path.exists():
        previous = pd.read_csv(pred_path)
        completed = set(previous["Scenario_ID"].astype(str))
        results = previous.to_dict("records")
    else:
        completed = set()
        results = []

    client = Groq(api_key=api_key)

    for _, row in data.iterrows():
        sid = str(row["Scenario_ID"])
        if sid in completed:
            continue

        query = normalize_text(row["User_Query"])
        result = {
            "Scenario_ID": sid,
            "User_Query": query,
            "Expected_Category": normalize_text(row["Expected_Category"]),
            "Expected_Priority": normalize_text(row["Expected_Priority"]),
            "Expected_Sentiment": normalize_text(row["Expected_Sentiment"]),
            "Expected_Urgency": normalize_text(row["Expected_Urgency"]),
            "Expected_Escalation": normalize_bool(row["Expected_Escalation"]),
        }

        try:
            classification = call_classifier(client, query)
            result.update({
                "Pred_Category": normalize_text(classification.get("category")),
                "Pred_Classifier_Priority": normalize_text(classification.get("priority")),
                "Pred_Title": normalize_text(classification.get("title")),
                "Pred_Summary": normalize_text(classification.get("summary")),
                "Classifier_Error": "",
            })
        except Exception as exc:
            result.update({
                "Pred_Category": "",
                "Pred_Classifier_Priority": "",
                "Pred_Title": "",
                "Pred_Summary": "",
                "Classifier_Error": repr(exc),
            })

        try:
            analysis = call_analyzer(client, query)
            analyzer_priority = normalize_text(analysis.get("priority")).upper()
            result.update({
                "Pred_Sentiment": normalize_text(analysis.get("sentiment")),
                "Pred_Urgency": normalize_text(analysis.get("urgency")),
                "Pred_Analyzer_Priority_Raw": analyzer_priority,
                "Pred_Analyzer_Priority_Mapped": ANALYZER_PRIORITY_MAP.get(analyzer_priority, ""),
                "Pred_Escalation": normalize_bool(analysis.get("escalation_required")),
                "Analyzer_Reason": normalize_text(analysis.get("reason")),
                "Analyzer_Error": "",
            })
        except Exception as exc:
            result.update({
                "Pred_Sentiment": "",
                "Pred_Urgency": "",
                "Pred_Analyzer_Priority_Raw": "",
                "Pred_Analyzer_Priority_Mapped": "",
                "Pred_Escalation": "",
                "Analyzer_Reason": "",
                "Analyzer_Error": repr(exc),
            })

        results.append(result)
        pd.DataFrame(results).to_csv(pred_path, index=False)
        print(f"Completed {sid} ({len(results)} saved rows)")
        time.sleep(max(args.delay, 0))

    pred = pd.DataFrame(results)
    metric_rows = []
    report_rows = []

    tasks = [
        ("Classifier category", "Expected_Category", "Pred_Category"),
        ("Classifier priority", "Expected_Priority", "Pred_Classifier_Priority"),
        ("Analyzer sentiment", "Expected_Sentiment", "Pred_Sentiment"),
        ("Analyzer urgency", "Expected_Urgency", "Pred_Urgency"),
        ("Analyzer priority mapped", "Expected_Priority", "Pred_Analyzer_Priority_Mapped"),
        ("Analyzer escalation", "Expected_Escalation", "Pred_Escalation"),
    ]

    for task, truth_col, pred_col in tasks:
        if truth_col not in pred or pred_col not in pred:
            continue
        y_true = pred[truth_col].tolist()
        y_pred = pred[pred_col].tolist()
        report = add_metric_rows(metric_rows, task, y_true, y_pred)
        if report:
            for label, values in report.items():
                if isinstance(values, dict):
                    report_rows.append({
                        "Task": task,
                        "Label": label,
                        "Precision": values.get("precision"),
                        "Recall": values.get("recall"),
                        "F1": values.get("f1-score"),
                        "Support": values.get("support"),
                    })

        # Confusion matrix with union of expected and predicted labels.
        valid_pairs = [
            (str(a), str(b)) for a, b in zip(y_true, y_pred)
            if normalize_text(a) and normalize_text(b)
        ]
        if valid_pairs:
            labels = sorted(set(a for a, _ in valid_pairs) | set(b for _, b in valid_pairs))
            truth, pred_labels = zip(*valid_pairs)
            cm = confusion_matrix(truth, pred_labels, labels=labels)
            cm_df = pd.DataFrame(cm, index=labels, columns=labels)
            safe_name = task.lower().replace(" ", "_")
            cm_df.to_csv(out_dir / f"confusion_{safe_name}.csv", index_label="Actual_Predicted")

    pd.DataFrame(metric_rows).to_csv(out_dir / "summary_metrics.csv", index=False)
    pd.DataFrame(report_rows).to_csv(out_dir / "per_class_metrics.csv", index=False)

    readme = f"""Evaluation run summary
======================
Rows evaluated/saved: {len(pred)}
Model: {MODEL_NAME}
Classifier/analyzer priority mapping used: {ANALYZER_PRIORITY_MAP}

Files:
- predictions.csv: row-level model outputs and errors
- summary_metrics.csv: aggregate accuracy, macro precision/recall/F1
- per_class_metrics.csv: per-label precision/recall/F1/support
- confusion_*.csv: confusion matrices

Research cautions:
1. The input dataset is synthetic. Describe results as a synthetic pilot.
2. Have two independent reviewers validate/adjudicate expected labels before treating them as gold labels.
3. Confirm the P1-P4 mapping with reviewers/supervisor. Do not silently assume equivalence.
4. Report failed API calls and missing predictions; do not silently drop failures from the study.
5. This script measures model outputs on isolated scenarios. It does not measure full RAG response quality.
6. The script makes two live Groq calls per scenario and may incur API usage/cost.
"""
    (out_dir / "RUN_NOTES.txt").write_text(readme, encoding="utf-8")
    print("\nEvaluation finished.")
    print(f"Results saved in: {out_dir.resolve()}")
    print(pd.DataFrame(metric_rows).to_string(index=False))


if __name__ == "__main__":
    main()
