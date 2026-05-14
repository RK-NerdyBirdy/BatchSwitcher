from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student import Student
from app.schemas.student import StudentCreate


async def create_student(db: AsyncSession, payload: StudentCreate) -> Student:
    student = Student(
        register_number=payload.register_number,
        student_name=payload.student_name,
        email=payload.email,
        phone_number=payload.phone_number,
        pfp_url=payload.pfp_url,
    )
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return student


async def get_student(db: AsyncSession, register_number: str) -> Student | None:
    result = await db.execute(
        select(Student).where(Student.register_number == register_number)
    )
    return result.scalar_one_or_none()


async def get_student_by_email(db: AsyncSession, email: str) -> Student | None:
    result = await db.execute(
        select(Student).where(Student.email == email)
    )
    return result.scalar_one_or_none()


async def list_students(db: AsyncSession) -> list[Student]:
    result = await db.execute(select(Student))
    return list(result.scalars().all())
