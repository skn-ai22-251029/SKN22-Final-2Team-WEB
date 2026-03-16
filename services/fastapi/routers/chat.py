from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.post("/")
async def chat(message: str):
    # TODO: LangGraph 멀티에이전트 파이프라인 연결
    return {"message": "TODO"}
