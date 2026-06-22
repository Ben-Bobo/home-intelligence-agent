from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.queue import action_queue
from app.logger import get_logger
from fastapi import APIRouter, HTTPException, Depends
from app.auth import verify_api_key

logger = get_logger(__name__)
router = APIRouter(dependencies=[Depends(verify_api_key)])


class CompleteRequest(BaseModel):
    action_id: str


@router.get("/actions/pending")
async def get_pending():
    return {"actions": action_queue.get_pending()}


@router.post("/actions/complete")
async def complete_action(request: CompleteRequest):
    success = action_queue.complete(request.action_id)

    if not success:
        raise HTTPException(status_code=404, detail="Action not found")

    return {"success": True, "action_id": request.action_id}


@router.get("/actions/history")
async def get_history():
    return {"actions": action_queue.get_all()}