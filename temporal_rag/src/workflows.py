from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Dict

from temporalio import workflow

# Import activity stubs for typing; actual calls use workflow.execute_activity
from . import activities


@dataclass
class RagRequest:
    question: str
    html_path: str
    top_k: int = 5
    chunk_size: int = 1200
    chunk_overlap: int = 200


@dataclass
class RagResponse:
    answer: str
    contexts: List[Dict]
    index_artifact: str


@workflow.defn
class RagWorkflow:
    @workflow.run
    async def run(self, req: RagRequest) -> RagResponse:
        # Step 1: parse + index
        index_artifact = await workflow.execute_activity(
            activities.parse_and_index,
            args = (req.html_path, req.chunk_size, req.chunk_overlap),
            schedule_to_close_timeout=workflow.timedelta(seconds=300),
        )

        # Step 2: retrieve
        contexts: List[Dict] = await workflow.execute_activity(
            activities.retrieve,
            args =(index_artifact, req.question,req.top_k),
            schedule_to_close_timeout=workflow.timedelta(seconds=60),
        )

        # Step 3: synthesize
        answer: str = await workflow.execute_activity(
            activities.synthesize_answer,
            args = (req.question,contexts),
            schedule_to_close_timeout=workflow.timedelta(seconds=60),
        )

        return RagResponse(answer=answer, contexts=contexts, index_artifact=index_artifact)

