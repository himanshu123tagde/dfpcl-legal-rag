from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.dependencies import CosmosRepoDep, CurrentUserDep, OpenAIServiceDep, RequestIdDep, SearchRepoDep
from app.graph.query_graph import execute_query_phase6
from app.models.queries import QueryRequest, QueryResponse

router = APIRouter()


@router.post("", response_model=QueryResponse)
async def query(
    req: QueryRequest,
    request_id: RequestIdDep,
    user: CurrentUserDep,
    openai: OpenAIServiceDep,
    search_repo: SearchRepoDep,
    cosmos_repo: CosmosRepoDep,
):
    try:
        return execute_query_phase6(
            openai=openai,
            search_repo=search_repo,
            cosmos_repo=cosmos_repo,
            user=user,
            req=req,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail=f"Query failed. request_id={request_id}")


@router.post("/embed")
async def embed_debug(req: QueryRequest, openai: OpenAIServiceDep):
    """
    Debug helper for Phase 1: verify embeddings are working and dimension is correct.
    """
    vec = openai.embed_text(req.question)
    return {"dim": len(vec)}