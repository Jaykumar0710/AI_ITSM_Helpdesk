
import os
from dotenv import load_dotenv
from groq import Groq

from modules.ai_analyzer import analyze_issue

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

test_issue = (
    "The entire office network is down. "
    "No employee can access the company systems."
)

result = analyze_issue(
    client=client,
    user_query=test_issue,
    ai_response="I will help you troubleshoot the network."
)

print("\nAI Analysis Result:")
print(result)
