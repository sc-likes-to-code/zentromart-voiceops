"""Build and persist the local knowledge base vector index."""
import sys
import time
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import INDEX_DIR
from src.ingestion import KnowledgeBaseIngestion
from src.retrieval import KnowledgeBaseRetriever


def main():
    print("=== Building ZentroMart Knowledge Base Index ===")
    start_time = time.time()

    # 1. Ingest documents (excluding superseded returns policy)
    print("1. Ingesting KB markdown files and product catalog...")
    ingestion = KnowledgeBaseIngestion()
    chunks = ingestion.ingest_all(exclude_superseded=True)
    print(f"   -> Successfully created {len(chunks)} authoritative chunks.")
    if ingestion.ingestion_errors:
        print("   -> Ingestion warnings/errors:")
        for err in ingestion.ingestion_errors:
            print(f"      ! {err}")

    # 2. Build semantic and lexical index
    print("2. Generating local embeddings and BM25 index...")
    retriever = KnowledgeBaseRetriever()
    count = retriever.build_index(chunks)
    print(f"   -> Embedded {count} chunks.")

    # 3. Persist index
    print(f"3. Persisting index artifacts to {INDEX_DIR}...")
    retriever.save(INDEX_DIR)
    elapsed = time.time() - start_time
    print(f"=== Index build complete in {elapsed:.2f}s ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
