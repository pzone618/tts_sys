"""History and statistics routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from packages.api.database import TTSRequestRecord, get_db
from packages.shared.enums import RequestStatus, TTSEngine
from packages.shared.models import ErrorResponse, HistoryRecord, HistoryResponse

router = APIRouter(prefix="/history", tags=["History"])


@router.get(
    "",
    response_model=HistoryResponse,
    summary="Get request history",
    description="Retrieve TTS request history with optional filters and pagination",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def get_history(
    limit: int = Query(50, ge=1, le=500, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    engine: TTSEngine | None = Query(None, description="Filter by engine"),
    status_filter: RequestStatus | None = Query(None, description="Filter by status", alias="status"),
    from_date: datetime | None = Query(None, description="Filter from date"),
    to_date: datetime | None = Query(None, description="Filter to date"),
    db: Session = Depends(get_db),
) -> HistoryResponse:
    """Get TTS request history.
    
    Args:
        limit: Maximum records to return
        offset: Pagination offset
        engine: Filter by engine
        status_filter: Filter by status
        from_date: Filter from date
        to_date: Filter to date
        db: Database session
    
    Returns:
        Paginated history records
    """
    try:
        # Build query
        query = db.query(TTSRequestRecord)

        # Apply filters
        if engine:
            query = query.filter(TTSRequestRecord.engine == engine.value)
        if status_filter:
            query = query.filter(TTSRequestRecord.status == status_filter.value)
        if from_date:
            query = query.filter(TTSRequestRecord.created_at >= from_date)
        if to_date:
            query = query.filter(TTSRequestRecord.created_at <= to_date)

        # Get total count
        total = query.count()

        # Get records with pagination
        records = (
            query.order_by(TTSRequestRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        # Convert to response models
        history_records = [
            HistoryRecord(
                request_id=r.id,
                text=r.text[:200] + "..." if len(r.text) > 200 else r.text,
                engine=TTSEngine(r.engine),
                voice=r.voice,
                status=RequestStatus(r.status),
                size_bytes=r.size_bytes,
                duration_ms=r.duration_ms,
                processing_time_ms=r.processing_time_ms,
                cached=r.cached,
                created_at=r.created_at,
            )
            for r in records
        ]

        logger.info(
            f"Retrieved history: total={total}, returned={len(history_records)}, "
            f"offset={offset}, limit={limit}"
        )

        return HistoryResponse(
            records=history_records,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Failed to retrieve history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}",
        )


@router.get(
    "/stats",
    summary="Get usage statistics",
    description="Get aggregated statistics for TTS requests",
)
async def get_stats(
    db: Session = Depends(get_db),
) -> dict:
    """Get usage statistics.
    
    Args:
        db: Database session
    
    Returns:
        Statistics dictionary
    """
    try:
        # Total requests
        total_requests = db.query(func.count(TTSRequestRecord.id)).scalar()

        # Requests by engine
        engine_stats = (
            db.query(
                TTSRequestRecord.engine,
                func.count(TTSRequestRecord.id).label("count"),
            )
            .group_by(TTSRequestRecord.engine)
            .all()
        )

        # Requests by status
        status_stats = (
            db.query(
                TTSRequestRecord.status,
                func.count(TTSRequestRecord.id).label("count"),
            )
            .group_by(TTSRequestRecord.status)
            .all()
        )

        # Cache hit rate
        cached_count = (
            db.query(func.count(TTSRequestRecord.id))
            .filter(TTSRequestRecord.cached == True)
            .scalar()
        )
        cache_hit_rate = (
            (cached_count / total_requests * 100) if total_requests > 0 else 0
        )

        # Average processing time
        avg_processing_time = (
            db.query(func.avg(TTSRequestRecord.processing_time_ms)).scalar() or 0
        )

        # Total audio size
        total_size = db.query(func.sum(TTSRequestRecord.size_bytes)).scalar() or 0

        return {
            "total_requests": total_requests,
            "by_engine": {e: c for e, c in engine_stats},
            "by_status": {s: c for s, c in status_stats},
            "cache_hit_rate_percent": round(cache_hit_rate, 2),
            "avg_processing_time_ms": round(avg_processing_time, 2),
            "total_audio_size_bytes": total_size,
        }

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}",
        )
