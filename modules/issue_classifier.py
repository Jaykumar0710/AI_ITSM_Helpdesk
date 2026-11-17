import json

from groq import Groq


MODEL_NAME = "openai/gpt-oss-20b"


def classify_issue(
    client,
    user_query,
    ai_response
):
    """
    Classify an IT issue using Groq AI.

    Returns:
        Dictionary containing title, category,
        priority, summary, and recommended_action.
    """

    prompt = f"""
You are an IT Service Management ticket classification assistant.

Analyze the reported IT support issue. Base the category and priority
on the concrete impact described in the issue, not on emotional wording
or urgency words alone.

USER ISSUE:
{user_query}

PREVIOUS AI TROUBLESHOOTING RESPONSE:
{ai_response}

Allowed categories:
- Network Connectivity
- Hardware
- Software
- Account and Access
- Security
- Email
- Printer
- Other

Allowed priorities:
- Low
- Medium
- High
- Critical

Use these harmonized priority definitions:

Low:
A minor inconvenience or nonessential issue. Essential work can continue,
and a simple, available workaround exists. Examples include an intermittent
connection that is restored by reconnecting, a cosmetic issue, or access
to a nonessential resource.

Medium:
A single user's normal work is affected, or a routine task is disrupted.
A workaround may exist, but it is temporary, inconvenient, or incomplete.
The issue does not indicate a major business function outage.

High:
An important business function or essential workflow is unavailable,
or a team/department is significantly affected. Productivity is materially
disrupted and no practical workaround is available.

Critical:
A widespread or organization-level outage, major business disruption,
or suspected/confirmed serious security incident. Immediate incident
response or escalation is warranted.

Priority decision rules:
1. Consider scope (one user, team, department, multiple sites, organization).
2. Consider business impact and whether essential work can continue.
3. Consider whether a practical workaround exists.
4. Do not assign High or Critical solely because the user sounds frustrated.
5. Do not assign Critical to an ordinary single-user Wi-Fi or device issue
   without evidence of widespread impact or serious security risk.
6. If the issue is a minor inconvenience and a simple workaround restores
   work, choose Low rather than Medium.
7. If evidence is insufficient, choose the least severe level supported
   by the available facts; do not invent impact.

Return the following JSON structure:
{{
    "title": "Short issue title",
    "category": "One allowed category",
    "priority": "Low | Medium | High | Critical",
    "summary": "Short summary of the reported issue",
    "recommended_action": "Recommended next step"
}}

Return only valid JSON. Use exactly one allowed category and one allowed priority.
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise ITSM classification assistant. "
                    "Apply the supplied category and impact rubric consistently. "
                    "Return valid JSON only."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,
        max_completion_tokens=500,
        response_format={
            "type": "json_object"
        }
    )

    result = json.loads(
        response.choices[0].message.content
    )

    return result
