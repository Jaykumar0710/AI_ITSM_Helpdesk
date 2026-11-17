import json
from groq import Groq


MODEL_NAME = "openai/gpt-oss-20b"


def analyze_issue(
    client: Groq,
    user_query: str,
    ai_response: str = ""
) -> dict:
    """
    Analyze a helpdesk issue for sentiment, urgency,
    priority, and escalation recommendation.
    """

    prompt = f"""
You are an intelligent IT helpdesk analyst.

Analyze the user's IT support issue.

User issue:
{user_query}

AI support response:
{ai_response}

Return ONLY a valid JSON object with these fields:

{{
    "sentiment": "Frustrated | Neutral | Satisfied",
    "urgency": "Low | Medium | High | Critical",
    "priority": "P1 | P2 | P3 | P4",
    "escalation_required": true,
    "reason": "Short explanation",
    "recommended_action": "Recommended next action"
}}

HARMONIZED PRIORITY DEFINITIONS:
P4 (Low):
A minor inconvenience or nonessential issue. Essential work can continue,
and a simple, available workaround exists.

P3 (Medium):
A single user's normal work is affected, or a routine task is disrupted.
A workaround may exist, but it is temporary, inconvenient, or incomplete.
There is no evidence of a major business-function outage.

P2 (High):
An important business function or essential workflow is unavailable,
or a team/department is significantly affected. Productivity is materially
disrupted and no practical workaround is available.

P1 (Critical):
A widespread or organization-level outage, major business disruption,
or suspected/confirmed serious security incident requiring immediate
incident response.

URGENCY DEFINITIONS:
Low:
The issue is a minor inconvenience; essential work continues and a simple
workaround is available.

Medium:
A user's routine work is affected, but the impact is limited and a temporary
or partial workaround is available.

High:
The user or team cannot perform an important task, or an essential workflow
is materially disrupted and no practical workaround is available.

Critical:
A widespread outage, major business disruption, or serious security incident
requires immediate attention.

SENTIMENT DEFINITIONS:
Frustrated:
The user explicitly expresses anger, frustration, distress, or dissatisfaction.

Neutral:
The user reports the issue without clear positive or negative emotion.

Satisfied:
The user explicitly expresses appreciation, relief, or satisfaction.

ESCALATION RULES:
- Recommend escalation for P1/Critical incidents.
- Recommend escalation for serious security incidents.
- Recommend escalation for high-impact unresolved issues that exceed
  normal first-line support.
- Do not escalate a minor single-user inconvenience solely because the
  user uses emotional or urgent language.
- Set escalation_required to true only when the issue evidence supports it.

CONSISTENCY RULES:
1. Use the same impact and scope reasoning for urgency and priority.
2. Map priority consistently: P1=Critical, P2=High, P3=Medium, P4=Low.
3. A simple workaround that allows essential work to continue normally
   generally supports P4/Low.
4. A single-user issue affecting normal work generally supports P3/Medium,
   unless the described impact justifies a higher level.
5. Do not infer organization-wide impact unless the user describes it.
6. Do not treat emotional language as evidence of technical severity.
7. If evidence is insufficient, choose the least severe level supported
   by the available facts and explain the uncertainty briefly.

Return only valid JSON with all six requested fields.
"""

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise ITSM analyst. "
                        "Apply the harmonized impact rubric consistently. "
                        "Return valid JSON only."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=500
        )

        result = json.loads(
            completion.choices[0].message.content
        )

        return result

    except Exception as error:
        print(f"AI analysis error: {error}")

        return {
            "sentiment": "Neutral",
            "urgency": "Medium",
            "priority": "P3",
            "escalation_required": False,
            "reason": "AI analysis was unavailable.",
            "recommended_action": "Review the ticket manually."
        }
