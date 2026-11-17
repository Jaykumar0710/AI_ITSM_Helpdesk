
from modules.knowledge_base import search_knowledge

query = (
    "My laptop is connected to Wi-Fi "
    "but websites are not opening."
)

results = search_knowledge(
    query,
    top_k=3
)

print("\nUser Query:")
print(query)

print("\nRetrieved Knowledge:\n")

for index, result in enumerate(
    results,
    start=1
):

    print(
        f"\nResult {index}"
    )

    print(
        f"Source: {result['source']}"
    )

    print(
        f"Distance: {result['distance']:.4f}"
    )

    print(
        f"Content: {result['content']}"
    )

    print("-" * 60)
