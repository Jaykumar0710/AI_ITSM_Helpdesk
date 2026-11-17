
from groq import Groq


MODEL_NAME = "openai/gpt-oss-20b"


def generate_support_response(
    client: Groq,
    user_query: str,
    knowledge_context: str,
    previous_ai_response: str = ""
) -> str:
    """
    Generate a professional, user-facing IT support response
    grounded in the retrieved knowledge-base context.
    """

    prompt = f"""
You are an IT support agent writing a response to an end user.

USER'S ISSUE:
{user_query}

KNOWLEDGE BASE CONTEXT:
{knowledge_context}

PREVIOUS AI TROUBLESHOOTING RESPONSE:
{previous_ai_response}

Instructions:
1. Write a professional, friendly, and clear response.
2. Use the knowledge base context as the source of technical guidance.
3. Provide numbered troubleshooting steps when appropriate.
4. Do not invent technical procedures or claim actions were performed.
5. Do not request passwords, OTPs, or confidential credentials.
6. If the knowledge base does not contain a confirmed solution,
   say so and recommend contacting the appropriate IT support team.
7. Do not claim the issue is resolved.
8. Keep the response concise and suitable for an IT support ticket.
9. Return only the response text, not JSON.
"""

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write accurate, professional IT support "
                        "responses using supplied knowledge."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_completion_tokens=800
        )

        return (
            completion.choices[0]
            .message.content.strip()
        )

    except Exception as error:
        print(f"Response generation error: {error}")

        return (
            "We have received your IT support request. "
            "Our support team will review the issue and "
            "provide further assistance."
        )
