"""
Knowledge-base utilities for the AI IT Helpdesk.

Articles are stored as UTF-8 text files in the project's data directory.
ChromaDB is rebuilt from these files so the source files remain the system of record.
"""

import os
import re
import hashlib

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
COLLECTION_NAME = "it_support_knowledge"

os.makedirs(DATA_DIR, exist_ok=True)

embedding_function = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_function,
    metadata={"description": "IT Support Knowledge Base"}
)


def _safe_filename(title):
    """Convert an article title to a safe, stable TXT filename."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", title.strip()).strip("_").lower()
    if not slug:
        slug = "knowledge_article"
    return f"{slug[:70]}.txt"


def _article_category(content):
    """Read CATEGORY: from an article, or return a safe default."""
    match = re.search(
        r"(?im)^\s*CATEGORY\s*:\s*(.+?)\s*$",
        content or ""
    )
    return match.group(1).strip() if match else "General"


def load_documents():
    """Load UTF-8 TXT articles from the data directory."""
    documents = []
    if not os.path.isdir(DATA_DIR):
        return documents

    for filename in sorted(os.listdir(DATA_DIR)):
        if not filename.lower().endswith(".txt"):
            continue

        path = os.path.join(DATA_DIR, filename)
        if not os.path.isfile(path):
            continue

        with open(path, "r", encoding="utf-8") as file:
            content = file.read().strip()

        if content:
            documents.append({
                "content": content,
                "source": filename,
                "category": _article_category(content)
            })

    return documents


def list_knowledge_articles():
    """Return editable article records from the data directory."""
    return [
        {
            "source": document["source"],
            "content": document["content"],
            "category": document["category"],
            "title": _article_title(document["content"], document["source"])
        }
        for document in load_documents()
    ]


def _article_title(content, source):
    match = re.search(r"(?im)^\s*TITLE\s*:\s*(.+?)\s*$", content or "")
    return match.group(1).strip() if match else os.path.splitext(source)[0]


def save_knowledge_article(title, category, content, source=None):
    """
    Create or update an article.

    For edits, pass the existing source filename. For new articles, a
    title-based filename is created. Returns the saved filename.
    """
    title = (title or "").strip()
    category = (category or "General").strip() or "General"
    content = (content or "").strip()

    if not title:
        raise ValueError("Article title is required.")
    if not content:
        raise ValueError("Article content is required.")

    # Ensure the structured fields exist in the article text.
    title_line = f"TITLE: {title}"
    category_line = f"CATEGORY: {category}"

    content = re.sub(
        r"(?im)^\s*TITLE\s*:.*(?:\n|$)", "", content
    ).strip()
    content = re.sub(
        r"(?im)^\s*CATEGORY\s*:.*(?:\n|$)", "", content
    ).strip()

    final_content = f"{title_line}\n{category_line}\n\n{content}\n"

    filename = source if source else _safe_filename(title)
    if not filename.lower().endswith(".txt"):
        filename += ".txt"

    # Prevent path traversal and keep writes inside DATA_DIR.
    filename = os.path.basename(filename)
    os.makedirs(DATA_DIR, exist_ok=True)
    destination = os.path.join(DATA_DIR, filename)

    # Avoid silently overwriting another article when two new articles share
    # the same title-derived filename.
    if source is None and os.path.exists(destination):
        digest = hashlib.sha256(
            f"{title}|{content}".encode("utf-8")
        ).hexdigest()[:8]
        stem = os.path.splitext(filename)[0]
        filename = f"{stem}_{digest}.txt"
        destination = os.path.join(DATA_DIR, filename)
        if os.path.exists(destination):
            raise FileExistsError(
                "An article with this title and content already exists."
            )

    with open(destination, "w", encoding="utf-8") as file:
        file.write(final_content)

    return filename


def delete_knowledge_article(source):
    """Delete one TXT article safely; returns True if it existed."""
    filename = os.path.basename(source or "")
    if not filename.lower().endswith(".txt"):
        return False

    path = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(path):
        return False

    os.remove(path)
    return True


def split_text(text, chunk_size=700, overlap=100):
    """
    Split text into overlapping chunks, preferring a nearby whitespace
    boundary to avoid cutting words where possible.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between 0 and chunk_size - 1.")

    chunks = []
    start = 0
    text = (text or "").strip()

    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start + int(chunk_size * 0.65):
                end = boundary

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break
        start = max(end - overlap, start + 1)

    return chunks


def build_knowledge_base():
    """
    Rebuild the ChromaDB collection from all TXT articles.
    Returns the number of indexed chunks.
    """
    documents = load_documents()
    all_chunks = []
    all_ids = []
    all_metadata = []

    for document in documents:
        chunks = split_text(document["content"])
        for chunk_number, chunk in enumerate(chunks):
            stable_key = (
                f'{document["source"]}:{chunk_number}:'
                f'{hashlib.sha1(chunk.encode("utf-8")).hexdigest()[:10]}'
            )
            all_chunks.append(chunk)
            all_ids.append(stable_key)
            all_metadata.append({
                "source": document["source"],
                "category": document.get("category", "General"),
                "chunk_number": chunk_number
            })

    # Preserve the current index if the source directory is empty or all
    # documents are blank. This avoids accidentally wiping a working index.
    if not all_chunks:
        raise ValueError(
            "No non-empty knowledge articles found in the data directory. "
            "Add a TXT article before rebuilding the index."
        )

    # Replace the collection only after source files have been read and
    # chunked successfully. (The index is rebuilt from the source TXT files.)
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass

    global collection
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"description": "IT Support Knowledge Base"}
    )

    if all_chunks:
        collection.add(
            documents=all_chunks,
            ids=all_ids,
            metadatas=all_metadata
        )

    return len(all_chunks)


def get_knowledge_status():
    """Return article and indexed-chunk counts."""
    articles = load_documents()
    try:
        indexed_chunks = collection.count()
    except Exception:
        indexed_chunks = 0

    return {
        "article_count": len(articles),
        "indexed_chunks": indexed_chunks
    }


def search_knowledge(query, top_k=3, category=None):
    """
    Retrieve relevant chunks. ChromaDB returns nearest results first;
    distance is preserved so callers can inspect retrieval quality.
    """
    query = (query or "").strip()
    if not query or collection.count() == 0:
        return []

    count = min(max(int(top_k), 1), collection.count())
    query_args = {
        "query_texts": [query],
        "n_results": count
    }

    if category and category != "All":
        query_args["where"] = {"category": category}

    results = collection.query(**query_args)

    retrieved = []
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    seen = set()
    for document, metadata, distance in zip(documents, metadatas, distances):
        metadata = metadata or {}
        source = metadata.get("source", "Unknown source")
        key = (source, document)
        if not document or key in seen:
            continue
        seen.add(key)

        retrieved.append({
            "content": document,
            "source": source,
            "category": metadata.get("category", "General"),
            "chunk_number": metadata.get("chunk_number"),
            "distance": distance
        })

    # Chroma query output is already ordered by increasing distance.
    return retrieved
