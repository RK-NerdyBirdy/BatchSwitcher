"""
Student management routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Student
from schemas import StudentResponse, EligibleStudentResponse, StudentUpdate
from auth import get_current_user
from config import settings
from typing import List

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/eligible", response_model=List[EligibleStudentResponse])
async def get_eligible_students(
    current_user: Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of eligible swap partners
    
    Students are eligible if their CGPA difference is within tolerance
    and they are not the current user
    """
    min_cgpa = current_user.cgpa - settings.CGPA_TOLERANCE
    max_cgpa = current_user.cgpa + settings.CGPA_TOLERANCE
    
    result = await db.execute(
        select(Student).where(
            Student.id != current_user.id,
            Student.cgpa >= min_cgpa,
            Student.cgpa <= max_cgpa
        ).order_by(Student.cgpa.desc())
    )
    eligible_students = result.scalars().all()
    
    # Calculate CGPA difference and build response
    response = []
    for student in eligible_students:
        response.append(
            EligibleStudentResponse(
                id=student.id,
                email=student.email,
                first_name=student.first_name,
                last_name=student.last_name,
                cgpa=student.cgpa,
                current_batch=student.current_batch,
                cgpa_difference=abs(student.cgpa - current_user.cgpa)
            )
        )
    
    return response


@router.get("/me", response_model=StudentResponse)
async def get_my_profile(
    current_user: Student = Depends(get_current_user)
):
    """
    Get current user's profile
    """
    return current_user


@router.put("/me", response_model=StudentResponse)
async def update_my_profile(
    update_data: StudentUpdate,
    current_user: Student = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's profile
    
    Currently only allows updating CGPA
    """
    if update_data.cgpa is not None:
        current_user.cgpa = update_data.cgpa
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student_by_id(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    """
    Get a specific student's profile by ID
    
    Requires: Authentication
    """
    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    return student


@router.get("/", response_model=List[StudentResponse])
async def get_all_students(
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """
    Get all students (paginated)
    
    Requires: Authentication
    """
    result = await db.execute(
        select(Student)
        .order_by(Student.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    students = result.scalars().all()
    
    return students