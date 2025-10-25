import argparse
import asyncio
import os
from temporalio.client import Client

from .workflows import RagWorkflow, RagRequest


async def run(question: str, html_path: str | None, top_k: int, chunk_size: int, chunk_overlap: int):
    address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    task_queue = os.getenv("TASK_QUEUE", "rag-task-queue")
    html = html_path or os.getenv("RAG_HTML_PATH", "JHU_AgenticAI_Project_1_Learners_Notebook.html")

    client = await Client.connect(address)

    handle = await client.start_workflow(
        RagWorkflow.run,
        RagRequest(
            question=question,
            html_path=html,
            top_k=top_k,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        ),
        id=f"rag-{abs(hash(question))}",
        task_queue=task_queue,
    )

    result = await handle.result()
    print("=== RAG RESULT ===")
    print(result.answer)
    print("\n--- Contexts (ids, scores truncated) ---")
    for c in result.contexts:
        print({k: c[k] for k in ["chunk_id", "score"]})


def main():
    ap = argparse.ArgumentParser(description="Temporal RAG client")
    ap.add_argument("--question", required=True, help="User question")
    ap.add_argument("--html", default=None, help="Path to HTML notebook")
    ap.add_argument("--top-k", type=int, default=int(os.getenv("TOP_K", 5)))
    ap.add_argument("--chunk-size", type=int, default=int(os.getenv("CHUNK_SIZE", 1200)))
    ap.add_argument("--chunk-overlap", type=int, default=int(os.getenv("CHUNK_OVERLAP", 200)))
    args = ap.parse_args()

    asyncio.run(run(args.question, args.html, args.top_k, args.chunk_size, args.chunk_overlap))


if __name__ == "__main__":
    main()

