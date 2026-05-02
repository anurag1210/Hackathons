import json
import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CORPUS_DIR = BASE_DIR / "corpus"
CHROMA_DIR = BASE_DIR / "chroma_db"

EMBEDDING_MODEL = "text-embedding-3-small"

DOMAIN_CONFIG = {
    "hackerrank": {
        "chunks_path": CORPUS_DIR / "hackerrank" / "chunks.json",
        "collection_name": "hackerrank_support",
    },
    "claude": {
        "chunks_path": CORPUS_DIR / "claude" / "chunks.json",
        "collection_name": "claude_support",
    },
    "visa": {
        "chunks_path": CORPUS_DIR / "visa" / "chunks.json",
        "collection_name": "visa_support",
    },
}


def _get_embeddings():
    return OpenAIEmbeddings(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=EMBEDDING_MODEL,
    )


def _load_chunks(chunks_path: Path) -> List[dict]:
    if not chunks_path.exists():
        raise FileNotFoundError(f"Missing chunks file: {chunks_path}")

    with open(chunks_path, "r", encoding="utf-8") as f:
        return json.load(f)


def init_vectorstore(build_corpus: bool = False) -> Dict[str, Chroma]:
    """
    Build or load one Chroma collection per domain.

    Returns:
        dict mapping domain -> Chroma vectorstore
    """
    embeddings = _get_embeddings()
    vectorstores = {}

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    for domain, config in DOMAIN_CONFIG.items():
        collection_name = config["collection_name"]
        chunks_path = config["chunks_path"]

        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=str(CHROMA_DIR),
        )

        if build_corpus:
            chunks = _load_chunks(chunks_path)

            texts = [chunk["text"] for chunk in chunks]
            metadatas = [
                {
                    "source": chunk.get("source", ""),
                    "domain": chunk.get("domain", domain),
                }
                for chunk in chunks
            ]
            ids = [f"{domain}_{i}" for i in range(len(chunks))]

            existing = vectorstore.get()
            existing_ids = existing.get("ids", [])

            if existing_ids:
                vectorstore.delete(ids=existing_ids)

            if texts:
                vectorstore.add_texts(
                    texts=texts,
                    metadatas=metadatas,
                    ids=ids,
                )

        vectorstores[domain] = vectorstore

    return vectorstores


def query_vectorstore(
    ticket_text: str,
    domain: str,
    vectorstores: Dict[str, Chroma],
    top_k: int = 3,
) -> List[dict]:
    """
    Query the appropriate domain collection and return the top-k chunks.

    Returns:
        [
            {
                "text": "...",
                "source": "...",
                "domain": "...",
                "score": ...
            },
            ...
        ]
    """
    if domain not in vectorstores:
        raise ValueError(f"Unknown domain: {domain}")

    vectorstore = vectorstores[domain]

    results = vectorstore.similarity_search_with_score(ticket_text, k=top_k)

    formatted_results = []
    for doc, score in results:
        formatted_results.append(
            {
                "text": doc.page_content,
                "source": doc.metadata.get("source", ""),
                "domain": doc.metadata.get("domain", domain),
                "score": score,
            }
        )

    return formatted_results
