"""
routes/chat.py — Chat & Swarm SSE endpoint
"""
from __future__ import annotations

import asyncio
import json
import uuid
import logging

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse

from nexus.models.schemas import ChatRequest
from nexus.observability.agent_tracer import trace_store
from nexus.agents.blackboard import Blackboard
from nexus.agents.orchestrator import SwarmEngine
from nexus.utils.security import check_rate_limit, get_client_id, verify_api_key, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW
from nexus.logic.booster import NEXUSBooster
from nexus.config import get_max_prompt_length

router = APIRouter(tags=["chat"])
logger = logging.getLogger("nexus")

MAX_PROMPT_LENGTH = get_max_prompt_length()


@router.post("/plan")
async def generate_swarm_plan(request: ChatRequest, auth: str = Depends(verify_api_key)):
    """Generate a strategy plan WITHOUT executing it."""
    blackboard = Blackboard(session_id=request.session_id, user_id=request.user_id)
    engine = SwarmEngine(blackboard)
    plan = await engine.plan(request.prompt)
    return {"plan": plan}


@router.post("/chat")
async def chat(request: ChatRequest, http_request: Request, auth: str = Depends(verify_api_key)):
    """Main SSE endpoint for agent swarm execution."""
    client_id = get_client_id(http_request)
    if not check_rate_limit(client_id):
        raise HTTPException(429, detail=f"Rate limit exceeded. Max {RATE_LIMIT_REQUESTS} per {RATE_LIMIT_WINDOW}s.")

    if len(request.prompt) > MAX_PROMPT_LENGTH:
        raise HTTPException(413, detail=f"Prompt too long. Max {MAX_PROMPT_LENGTH} characters.")

    # Fast-path: deterministic local booster (run in executor to avoid blocking event loop)
    loop = asyncio.get_running_loop()
    boosted = await loop.run_in_executor(None, NEXUSBooster.try_boost, request.prompt)
    if boosted:
        async def _boosted():
            yield f"data: {json.dumps({'type':'trace','agent':'booster','action':'Local boost active','status':'done'})}\n\n"
            yield f"data: {json.dumps({'type':'response','result':boosted})}\n\n"
        return StreamingResponse(_boosted(), media_type="text/event-stream")

    request_id = str(uuid.uuid4())
    tracer = trace_store.create(request.session_id)

    async def event_generator():
        orch_task = None
        try:
            blackboard = Blackboard(session_id=request.session_id, user_id=request.user_id)
            await blackboard.load()
            engine = SwarmEngine(blackboard)

            orch_task = asyncio.create_task(engine.run(request.prompt, plan=request.plan))

            # Stream trace events as they arrive
            async for chunk in tracer.stream():
                yield chunk

            # Then emit the final result
            result_dict = await asyncio.wait_for(orch_task, timeout=120.0)
            yield f"data: {json.dumps({'type':'response','result':result_dict})}\n\n"

        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type':'error','error':'Request timed out after 120s'})}\n\n"
        except asyncio.CancelledError:
            logger.info(f"Request {request_id} cancelled")
            if orch_task and not orch_task.done():
                orch_task.cancel()
                try:
                    await orch_task
                except asyncio.CancelledError:
                    pass
            raise
        except Exception as e:
            logger.error(f"Orchestration error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type':'error','error':str(e)})}\n\n"
        finally:
            if orch_task and not orch_task.done():
                orch_task.cancel()
            tracer.cleanup()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Request-ID": request_id},
    )


@router.get("/trace/{session_id}", tags=["trace"])
async def get_trace(session_id: str, auth: str = Depends(verify_api_key)):
    tracer = trace_store.get(session_id)
    if not tracer:
        raise HTTPException(404, f"Session '{session_id}' not found")
    return tracer.get_trace()


@router.get("/mcp-detail/{session_id}/{tool}", tags=["trace"])
async def get_mcp_detail(session_id: str, tool: str, auth: str = Depends(verify_api_key)):
    tracer = trace_store.get(session_id)
    if not tracer:
        raise HTTPException(404, f"Session '{session_id}' not found")
    detail = tracer.get_mcp_detail(tool)
    if not detail:
        raise HTTPException(404, f"No detail for tool '{tool}'")
    return detail.model_dump()
