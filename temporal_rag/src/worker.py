import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from .activities import parse_and_index, retrieve, synthesize_answer
from .workflows import RagWorkflow


async def main() -> None:
    address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    task_queue = os.getenv("TASK_QUEUE", "rag-task-queue")

    client = await Client.connect(address)

    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[RagWorkflow],
        activities=[parse_and_index, retrieve, synthesize_answer],
    )

    print(f"Worker started. Address={address} TaskQueue={task_queue}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

