"""Command-line interface for the ZentroMart VoiceOps Grounded RAG Assistant."""
import argparse
import sys
from pathlib import Path
from typing import Optional

# Reconfigure stdout/stderr for Unicode/UTF-8 support on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is on sys.path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.answering import GroundedAnswer, GroundedAnswerGenerator
from src.config import DEFAULT_TOP_K, INDEX_DIR
from src.retrieval import KnowledgeBaseRetriever, RetrievalResult


def print_formatted_result(result: GroundedAnswer):
    """Displays structured RAG response per Phase 2 requirements."""
    print("\n" + "=" * 60)
    print("1. USER QUESTION:")
    print(f"   {result.question}")
    print("\n2. GROUNDED ANSWER:")
    print(f"   {result.answer}")
    print("\n3. RETRIEVED SOURCES & CHUNK IDENTIFIERS:")
    if result.retrieved_chunks:
        for i, chunk in enumerate(result.retrieved_chunks, 1):
            print(f"   [{i}] Chunk ID : {chunk.chunk_id}")
            print(f"       Source   : {chunk.source_file} (Section: {chunk.section_id})")
            print(f"       Heading  : {chunk.heading}")
            print(f"       Score    : {chunk.score:.4f}")
    else:
        print("   (None retrieved)")

    print("\n4. EVIDENCE PREVIEWS:")
    if result.retrieved_chunks:
        for i, chunk in enumerate(result.retrieved_chunks, 1):
            preview = chunk.text.replace("\n", " ").strip()
            if len(preview) > 180:
                preview = preview[:180] + "..."
            print(f"   [{i}] {preview}")
    else:
        print("   (No evidence chunks available)")

    print("\n5. STATUS:")
    if result.insufficient_evidence:
        print("   DECLINED (Insufficient evidence in knowledge base)")
    else:
        print(f"   ANSWERED (Decision: {result.decision.upper()} | Sources: {', '.join(result.evidence_sources) if result.evidence_sources else 'Knowledge Base'})")
    print("=" * 60 + "\n")


def run_single_query(
    query: str,
    retriever: KnowledgeBaseRetriever,
    generator: GroundedAnswerGenerator,
    top_k: int = DEFAULT_TOP_K,
) -> GroundedAnswer:
    """Executes retrieval and grounded generation for a single user question."""
    chunks = retriever.retrieve(query, top_k=top_k)
    return generator.generate_answer(query, chunks)


def interactive_loop(
    retriever: KnowledgeBaseRetriever,
    generator: GroundedAnswerGenerator,
    top_k: int = DEFAULT_TOP_K,
):
    """Runs interactive console session."""
    print("=" * 60)
    print("ZentroMart Grounded Customer Support Assistant")
    print("Type your question and press Enter. Type 'exit' or 'quit' to stop.")
    print("=" * 60)

    while True:
        try:
            query = input("\nUser> ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit", "q"):
                print("Exiting assistant session. Goodbye!")
                break

            result = run_single_query(query, retriever, generator, top_k=top_k)
            print_formatted_result(result)
        except (KeyboardInterrupt, EOFError):
            print("\nSession interrupted. Goodbye!")
            break


def main():
    parser = argparse.ArgumentParser(description="ZentroMart VoiceOps Grounded RAG Assistant")
    parser.add_argument("--query", "-q", type=str, help="Single query to answer (one-shot mode)")
    parser.add_argument("--top-k", "-k", type=int, default=DEFAULT_TOP_K, help="Number of evidence chunks to retrieve")
    args = parser.parse_args()

    # Initialize retriever
    retriever = KnowledgeBaseRetriever()
    if not retriever.load(INDEX_DIR):
        print(f"Error: Index not found at {INDEX_DIR}. Run 'python scripts/build_index.py' first.", file=sys.stderr)
        return 1

    # Initialize answer generator
    try:
        generator = GroundedAnswerGenerator()
    except Exception as e:
        print(f"Error initializing Gemini answer generator: {e}", file=sys.stderr)
        return 1

    if args.query:
        # One-shot mode
        result = run_single_query(args.query, retriever, generator, top_k=args.top_k)
        print_formatted_result(result)
    else:
        # Interactive mode
        interactive_loop(retriever, generator, top_k=args.top_k)

    return 0


if __name__ == "__main__":
    sys.exit(main())
