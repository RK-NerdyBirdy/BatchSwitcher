from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.crud.student import get_student_by_email, get_student
from app.models.student import Student
from app.crud.swap_request import (
    create_swap_request as create_swap_request_crud,
    get_assignment_by_id,
    get_assignment_by_id_for_update,
    get_all_student_assignments,
    get_assignments_by_register_number_for_update,
    get_active_swap_request_between,
    get_swap_request_for_update,
    has_approved_request_for_assignments,
    has_accepted_request_for_assignments,
    list_swap_requests_for_assignments,
)
from app.crud.batch import get_semester
from app.models.student_semester_assignment import StudentSemesterAssignment
from app.dependencies.student_auth import get_current_student
from app.schemas.swap_request import (
    AssignmentResponse,
    SwapCandidateResponse,
    SwapRequestCreate,
    SwapRequestResponseWithDetails,
)
from app.services.swap_service import swap_candidate_service

router = APIRouter()


@router.get("/me", response_model=dict)
async def get_me(
    current_student: dict = Depends(get_current_student),
) -> dict:
    return {
        "email": current_student.get("email"),
        "name": current_student.get("name"),
        "pfp": current_student.get("pfp"),
    }


@router.get("/me/batch", response_model=list[AssignmentResponse])
async def get_my_batch(
    db: AsyncSession = Depends(get_db),
    current_student: dict = Depends(get_current_student),
) -> list[AssignmentResponse]:
    """Get all batch assignments for the current student across all semesters."""
    email = current_student.get("email")
    
    # Find student by email
    student = await get_student_by_email(db, email)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    
    # Get all assignments
    assignments = await get_all_student_assignments(db, student.register_number)
    return assignments


@router.get("/swap-eligible", response_model=dict)
async def get_my_eligible_swaps(
    db: AsyncSession = Depends(get_db),
    current_student: dict = Depends(get_current_student),
) -> dict:
    """Get all eligible swap candidates for the current student across all their semesters.
    
    Shows students grouped by semester that match CGPA tolerance (±CGPA_TOL).
    """
    email = current_student.get("email")
    
    # Find student by email
    student = await get_student_by_email(db, email)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    
    # Get all assignments for this student
    all_assignments = await get_all_student_assignments(db, student.register_number)
    
    if not all_assignments:
        return {
            "register_number": student.register_number,
            "student_name": student.student_name,
            "eligible_by_semester": {},
        }
    
    # For each semester, find eligible swap candidates
    eligible_by_semester = {}
    for assignment in all_assignments:
        candidates = await swap_candidate_service.get_swap_candidates(
            db,
            assignment.assignment_id,
        )
        
        if candidates:
            candidate_list = []
            for c in candidates:
                candidate_student = await get_student(db, c.register_number)
                candidate_list.append({
                    "assignment_id": c.assignment_id,
                    "register_number": c.register_number,
                    "student_name": candidate_student.student_name if candidate_student else "Unknown",
                    "email": candidate_student.email if candidate_student else "",
                    "phone_number": candidate_student.phone_number if candidate_student else None,
                    "batch_id": c.batch_id,
                    "cgpa": float(c.cgpa),
                })
            eligible_by_semester[assignment.semester_id] = candidate_list
    
    return {
        "register_number": student.register_number,
        "student_name": student.student_name,
        "eligible_by_semester": eligible_by_semester,
    }


@router.get("/swap-requests/incoming", response_model=list[SwapRequestResponseWithDetails])
async def list_incoming_swap_requests(
    db: AsyncSession = Depends(get_db),
    current_student: dict = Depends(get_current_student),
) -> list[SwapRequestResponseWithDetails]:
    email = current_student.get("email")
    student = await get_student_by_email(db, email)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    assignments = await get_all_student_assignments(db, student.register_number)
    assignment_ids = [assignment.assignment_id for assignment in assignments]
    return await list_swap_requests_for_assignments(db, assignment_ids, incoming=True)


@router.get("/swap-requests/outgoing", response_model=list[SwapRequestResponseWithDetails])
async def list_outgoing_swap_requests(
    db: AsyncSession = Depends(get_db),
    current_student: dict = Depends(get_current_student),
) -> list[SwapRequestResponseWithDetails]:
    email = current_student.get("email")
    student = await get_student_by_email(db, email)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    assignments = await get_all_student_assignments(db, student.register_number)
    assignment_ids = [assignment.assignment_id for assignment in assignments]
    return await list_swap_requests_for_assignments(db, assignment_ids, incoming=False)


@router.post("/swap-requests", response_model=SwapRequestResponseWithDetails, status_code=status.HTTP_201_CREATED)
async def create_swap_request_endpoint(
    payload: SwapRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_student: dict = Depends(get_current_student),
) -> SwapRequestResponseWithDetails:
    email = current_student.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student token",
        )

    student = await get_student_by_email(db, email)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    student_assignments = await get_all_student_assignments(db, student.register_number)
    if await has_approved_request_for_assignments(
        db,
        [assignment.assignment_id for assignment in student_assignments],
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an approved swap request and cannot create a new one",
        )

    requester = await get_assignment_by_id(db, payload.requester_assignment_id)
    if not requester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requester assignment not found",
        )

    if requester.register_number != student.register_number:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requester assignment does not belong to current student",
        )

    target = await get_assignment_by_id(db, payload.target_assignment_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target assignment not found",
        )

    if requester.semester_id != target.semester_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both assignments must be in the same semester",
        )

    semester = await get_semester(db, requester.semester_id)
    if not semester or not semester.swap_allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Swaps are not allowed for this semester",
        )

    if requester.batch_id == target.batch_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Swap candidates must be in different batches",
        )

    eligible_candidates = await swap_candidate_service.get_swap_candidates(
        db,
        requester.assignment_id,
    )
    eligible_ids = {candidate.assignment_id for candidate in eligible_candidates}
    if target.assignment_id not in eligible_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target assignment is not eligible for swap",
        )

    existing_request = await get_active_swap_request_between(
        db,
        requester.assignment_id,
        target.assignment_id,
    )
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A swap request already exists between these students",
        )

    try:
        swap_request = await create_swap_request_crud(db, payload)
    except IntegrityError as error:
        await db.rollback()
        if "uq_swap_request_active_pair" in str(error.orig):
            translated_error = HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A swap request already exists between these students",
            )
            raise translated_error from error
        if "swap_request_pkey" in str(error.orig):
            await db.execute(
                text(
                    "SELECT setval("
                    "pg_get_serial_sequence('swap_request','request_id'),"
                    "COALESCE((SELECT MAX(request_id) FROM swap_request), 0)"
                    ")"
                )
            )
            await db.commit()
            try:
                swap_request = await create_swap_request_crud(db, payload)
            except IntegrityError as retry_error:
                await db.rollback()
                translated_error = HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Swap request id sequence was reset but insert still failed."
                    ),
                )
                raise translated_error from retry_error
        else:
            translated_error = HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Database constraint violation",
            )
            raise translated_error from error
    return SwapRequestResponseWithDetails(
        request_id=swap_request.request_id,
        requester_assignment_id=swap_request.requester_assignment_id,
        target_assignment_id=swap_request.target_assignment_id,
        status=swap_request.status,
        approved_by=swap_request.approved_by,
        approved_at=swap_request.approved_at,
        created_at=swap_request.created_at,
        requester_assignment=requester,
        target_assignment=target,
    )


@router.patch("/swap-requests/{request_id}/accept", response_model=SwapRequestResponseWithDetails)
async def accept_swap_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_student: dict = Depends(get_current_student),
) -> SwapRequestResponseWithDetails:
    email = current_student.get("email")
    student = await get_student_by_email(db, email)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    try:
        swap_request = await get_swap_request_for_update(db, request_id)
        if not swap_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Swap request not found",
            )

        if swap_request.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Swap request is not pending",
            )
        # Lock both assignment rows in deterministic order by assignment_id
        a_id = swap_request.requester_assignment_id
        b_id = swap_request.target_assignment_id
        first_id, second_id = (a_id, b_id) if a_id <= b_id else (b_id, a_id)

        first_assignment = await get_assignment_by_id_for_update(db, first_id)
        second_assignment = await get_assignment_by_id_for_update(db, second_id)

        # Map requester/target after locking
        if swap_request.target_assignment_id == first_assignment.assignment_id:
            target_assignment = first_assignment
            requester_assignment = second_assignment
        else:
            target_assignment = second_assignment
            requester_assignment = first_assignment

        if not target_assignment or target_assignment.register_number != student.register_number:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to accept this request",
            )

        semester = await get_semester(db, target_assignment.semester_id)
        if not semester or not semester.swap_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Swaps are not allowed for this semester",
            )

        # Lock both students to serialize accept operations per student
        # Lock in deterministic order by register_number
        reg_nums = sorted({requester_assignment.register_number, target_assignment.register_number})
        if reg_nums:
            for rn in reg_nums:
                await db.execute(
                    select(Student).where(Student.register_number == rn).with_for_update()
                )

        # Gather all assignment_ids for both students
        assignment_ids = set()
        result = await db.execute(
            select(StudentSemesterAssignment.assignment_id).where(
                StudentSemesterAssignment.register_number.in_(reg_nums)
            )
        )
        assignment_ids.update([row[0] for row in result.all()])
        has_active = await has_accepted_request_for_assignments(
            db,
            list(assignment_ids),
            exclude_request_id=request_id,
        )
        if has_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One of the students already has an accepted swap request",
            )

        swap_request.status = "ACCEPTED"
        await db.flush()
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise

    return SwapRequestResponseWithDetails(
        request_id=swap_request.request_id,
        requester_assignment_id=swap_request.requester_assignment_id,
        target_assignment_id=swap_request.target_assignment_id,
        status=swap_request.status,
        approved_by=swap_request.approved_by,
        approved_at=swap_request.approved_at,
        created_at=swap_request.created_at,
        requester_assignment=requester_assignment,
        target_assignment=target_assignment,
    )


@router.patch("/swap-requests/{request_id}/reject", response_model=SwapRequestResponseWithDetails)
async def reject_swap_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_student: dict = Depends(get_current_student),
) -> SwapRequestResponseWithDetails:
    email = current_student.get("email")
    student = await get_student_by_email(db, email)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    try:
        swap_request = await get_swap_request_for_update(db, request_id)
        if not swap_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Swap request not found",
            )

        if swap_request.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Swap request is not pending",
            )

        target_assignment = await get_assignment_by_id_for_update(
            db, swap_request.target_assignment_id
        )
        if not target_assignment or target_assignment.register_number != student.register_number:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to reject this request",
            )

        requester_assignment = await get_assignment_by_id_for_update(
            db, swap_request.requester_assignment_id
        )
        if not requester_assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requester assignment not found",
            )

        swap_request.status = "REJECTED"
        await db.flush()
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise

    return SwapRequestResponseWithDetails(
        request_id=swap_request.request_id,
        requester_assignment_id=swap_request.requester_assignment_id,
        target_assignment_id=swap_request.target_assignment_id,
        status=swap_request.status,
        approved_by=swap_request.approved_by,
        approved_at=swap_request.approved_at,
        created_at=swap_request.created_at,
        requester_assignment=requester_assignment,
        target_assignment=target_assignment,
    )


@router.patch("/swap-requests/{request_id}/cancel", response_model=SwapRequestResponseWithDetails)
async def cancel_swap_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_student: dict = Depends(get_current_student),
) -> SwapRequestResponseWithDetails:
    email = current_student.get("email")
    student = await get_student_by_email(db, email)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    try:
        swap_request = await get_swap_request_for_update(db, request_id)
        if not swap_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Swap request not found",
            )

        if swap_request.status == "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approved swap requests cannot be cancelled",
            )

        requester_assignment = await get_assignment_by_id_for_update(
            db, swap_request.requester_assignment_id
        )
        if not requester_assignment or requester_assignment.register_number != student.register_number:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to cancel this request",
            )

        target_assignment = await get_assignment_by_id_for_update(
            db, swap_request.target_assignment_id
        )
        if not target_assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target assignment not found",
            )

        swap_request.status = "CANCELLED"
        await db.flush()
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise

    return SwapRequestResponseWithDetails(
        request_id=swap_request.request_id,
        requester_assignment_id=swap_request.requester_assignment_id,
        target_assignment_id=swap_request.target_assignment_id,
        status=swap_request.status,
        approved_by=swap_request.approved_by,
        approved_at=swap_request.approved_at,
        created_at=swap_request.created_at,
        requester_assignment=requester_assignment,
        target_assignment=target_assignment,
    )
