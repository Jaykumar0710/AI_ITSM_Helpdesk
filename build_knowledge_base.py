
from modules.knowledge_base import build_knowledge_base

if __name__ == "__main__":

    print("Building IT Support Knowledge Base...")

    total_chunks = build_knowledge_base()

    print(
        f"Knowledge Base Created Successfully!"
    )

    print(
        f"Total Indexed Chunks: {total_chunks}"
    )
