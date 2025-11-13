"""
Swap request management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from database import get_db
from models import Student, SwapRequest, SwapRequestStatus
from schemas import SwapRequestCreate, SwapRequestResponse
from auth import get_current_user
from config import settings
from typing import List

router = APIRouter(prefix="/swap-requests", tags=["Swap Requests"])


@router.post("", response_model=SwapRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_swap_request(
    swap_data: SwapRequestCreate,
    current_user: Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a swap request to another student
    
    Validates:
    - Target student exists
    - CGPA eligibility
    - No existing pending request
    - Not requesting yourself
    """
    # Check not requesting self
    if swap_data.target_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send swap request to yourself"
        )
    
    # Get target student
    result = await db.execute(
        select(Student).where(Student.id == swap_data.target_id)
    )
    target = result.scalar_one_or_none()
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target student not found"
        )
    
    # Check CGPA eligibility
    cgpa_diff = abs(current_user.cgpa - target.cgpa)
    if cgpa_diff > settings.CGPA_TOLERANCE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CGPA difference ({cgpa_diff:.3f}) exceeds tolerance ({settings.CGPA_TOLERANCE})"
        )
    
    # Check for existing pending request (both directions)
    result = await db.execute(
        select(SwapRequest).where(
            or_(
                (SwapRequest.requester_id == current_user.id) & 
                (SwapRequest.target_id == swap_data.target_id),
                (SwapRequest.requester_id == swap_data.target_id) & 
                (SwapRequest.target_id == current_user.id)
            ),
            SwapRequest.status == SwapRequestStatus.PENDING
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A pending swap request already exists between you and this student"
        )
    
    # Create swap request
    swap_request = SwapRequest(
        requester_id=current_user.id,
        target_id=swap_data.target_id,
        message=swap_data.message,
        status=SwapRequestStatus.PENDING
    )
    
    db.add(swap_request)
    await db.commit()
    await db.refresh(swap_request)
    
    # Load relationships
    await db.refresh(swap_request, ['requester', 'target'])
    
    return swap_request


@router.get("/sent", response_model=List[SwapRequestResponse])
async def get_sent_requests(
    current_user: Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_filter: SwapRequestStatus | None = None
):
    """
    Get all swap requests sent by current user
    
    Optional status filter
    """
    query = select(SwapRequest).where(
        SwapRequest.requester_id == current_user.id
    )
    
    if status_filter:
        query = query.where(SwapRequest.status == status_filter)
    
    query = query.order_by(SwapRequest.created_at.desc())
    
    result = await db.execute(query)
    requests = result.scalars().all()
    
    # Load relationships
    for req in requests:
        await db.refresh(req, ['requester', 'target'])
    
    return requests


@router.get("/received", response_model=List[SwapRequestResponse])
async def get_received_requests(
    current_user: Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_filter: SwapRequestStatus | None = None
):
    """
    Get all swap requests received by current user
    
    Optional status filter
    """
    query = select(SwapRequest).where(
        SwapRequest.target_id == current_user.id
    )
    
    if status_filter:
        query = query.where(SwapRequest.status == status_filter)
    
    query = query.order_by(SwapRequest.created_at.desc())
    
    result = await db.execute(query)
    requests = result.scalars().all()
    
    # Load relationships
    for req in requests:
        await db.refresh(req, ['requester', 'target'])
    
    return requests


@router.post("/{request_id}/accept", response_model=SwapRequestResponse)
async def accept_swap_request(
    request_id: int,
    current_user: Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept a swap request and perform the batch swap
    
    This swaps the current_batch for both students
    """
    # Get swap request
    result = await db.execute(
        select(SwapRequest).where(SwapRequest.id == request_id)
    )
    swap_request = result.scalar_one_or_none()
    
    if not swap_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Swap request not found"
        )
    
    # Verify current user is the target
    if swap_request.target_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to accept this request"
        )
    
    # Check if already processed
    if swap_request.status != SwapRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request already {swap_request.status.value}"
        )
    
    # Get requester
    result = await db.execute(
        select(Student).where(Student.id == swap_request.requester_id)
    )
    requester = result.scalar_one_or_none()
    
    if not requester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requester not found"
        )
    
    # Perform batch swap
    requester_batch = requester.current_batch
    target_batch = current_user.current_batch
    
    requester.current_batch = target_batch
    current_user.current_batch = requester_batch
    
    # Update request status
    swap_request.status = SwapRequestStatus.ACCEPTED
    
    await db.commit()
    await db.refresh(swap_request, ['requester', 'target'])
    
    return swap_request


@router.post("/{request_id}/reject", response_model=SwapRequestResponse)
async def reject_swap_request(
    request_id: int,
    current_user: Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reject a swap request
    """
    result = await db.execute(
        select(SwapRequest).where(SwapRequest.id == request_id)
    )
    swap_request = result.scalar_one_or_none()
    
    if not swap_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Swap request not found"
        )
    
    if swap_request.target_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to reject this request"
        )
    
    if swap_request.status != SwapRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request already {swap_request.status.value}"
        )
    
    swap_request.status = SwapRequestStatus.REJECTED
    await db.commit()
    await db.refresh(swap_request, ['requester', 'target'])
    
    return swap_request


@router.delete("/{request_id}")
async def cancel_swap_request(
    request_id: int,
    current_user: Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a sent swap request (only if pending)
    """
    result = await db.execute(
        select(SwapRequest).where(SwapRequest.id == request_id)
    )
    swap_request = result.scalar_one_or_none()
    
    if not swap_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Swap request not found"
        )
    
    if swap_request.requester_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this request"
        )
    
    if swap_request.status != SwapRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel {swap_request.status.value} request"
        )
    
    swap_request.status = SwapRequestStatus.CANCELLED
    await db.commit()
    
    return {
        "status": "success",
        "message": "Request cancelled successfully"
    }


@router.get("/{request_id}", response_model=SwapRequestResponse)
async def get_swap_request(
    request_id: int,
    current_user: Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific swap request by ID
    
    Only accessible by requester or target
    """
    result = await db.execute(
        select(SwapRequest).where(SwapRequest.id == request_id)
    )
    swap_request = result.scalar_one_or_none()
    
    if not swap_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Swap request not found"
        )
    
    # Verify access
    if swap_request.requester_id != current_user.id and swap_request.target_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this request"
        )
    
    await db.refresh(swap_request, ['requester', 'target'])
    
    return swap_request