from datetime import datetime, timedelta
from fastapi import APIRouter
from app.core.mongodb import database

router = APIRouter()


@router.post("/clean_requests")
async def forward_emails():
    limit = datetime.now() - timedelta(days=30)

    metrics_collection = database.get_collection("requests")
    result = await metrics_collection.delete_many({
        "time": {"$lt": limit}
    })
    return {"result": "success", "deleted": result.deleted_count}