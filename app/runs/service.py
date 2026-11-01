# AI contribution: 50% or more AI-generated
"""Run a saved pipeline revision with durable telemetry (#27).

This is the engine-side entry point that trigger and execute APIs (#29) call;
it exposes no HTTP route itself.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.execution import Cancellation, ExecutionContext, Executor, InvalidPipeline
from app.metadata.database import Database
from app.metadata.models import PipelineRevision
from app.pipelines.models import PipelineDefinition
from app.runs.recorder import RunRecorder

logger = logging.getLogger(__name__)


class RevisionNotFound(LookupError):
    pass


@dataclass(frozen=True)
class RunOutcome:
    run_id: str
    state: str
    context: ExecutionContext


def load_definition(db: Database, revision_id: str) -> PipelineDefinition:
    with db.transaction() as session:
        revision = session.get(PipelineRevision, revision_id)
        if revision is None:
            raise RevisionNotFound(revision_id)
        stored = revision.definition
    return PipelineDefinition.from_json(json.dumps(stored))


def execute_revision(
    db: Database,
    executor: Executor,
    revision_id: str,
    *,
    cancellation: Cancellation | None = None,
    resolve_resource: Callable[[str], Path] | None = None,
    workspace_root: Path | None = None,
) -> RunOutcome:
    """Execute one immutable revision; invalid pipelines create no run row."""
    definition = load_definition(db, revision_id)
    run_id = str(uuid4())
    token = cancellation or Cancellation()
    recorder = RunRecorder(db, run_id, revision_id, definition)
    try:
        context = executor.execute(
            definition,
            run_id=run_id,
            resolve_resource=resolve_resource,
            cancellation=token,
            workspace_root=workspace_root,
            on_state=recorder.on_state,
        )
    except InvalidPipeline:
        logger.info("Refused run for revision %s: validation failed", revision_id)
        raise
    except BaseException as exc:
        # Includes KeyboardInterrupt: never leave a live-looking row behind.
        # Log the type only; exception text may carry paths or credentials.
        logger.error("Run %s stopped unexpectedly: %s", run_id, type(exc).__name__)
        recorder.abort("execution_failed", "Execution stopped unexpectedly.")
        raise
    state = recorder.finish(context, cancelled=token.is_cancelled())
    log = logger.info if state == "succeeded" else logger.warning
    log("Run %s for revision %s finished: %s", run_id, revision_id, state)
    return RunOutcome(run_id, state, context)
