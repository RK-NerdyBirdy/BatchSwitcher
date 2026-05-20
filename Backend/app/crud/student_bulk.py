from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.student import Student
from app.models.student_semester_assignment import StudentSemesterAssignment
from app.models.semester import Semester
from app.models.batch import Batch
from app.services.csv_service import StudentBatchAssignmentRow


async def _reset_assignment_sequence(db: AsyncSession) -> None:
    await db.execute(
        text(
            "SELECT setval("
            "pg_get_serial_sequence('student_semester_assignment','assignment_id'),"
            "COALESCE((SELECT MAX(assignment_id) FROM student_semester_assignment), 0)"
            ")"
        )
    )


def _normalize_name(value: str) -> str:
    return " ".join(value.split()).strip()


async def _get_or_create_semester(
    db: AsyncSession,
    semester_name: str,
) -> Semester:
    normalized = _normalize_name(semester_name)
    result = await db.execute(
        select(Semester).where(func.lower(Semester.semester_name) == normalized.lower())
    )
    semester = result.scalar_one_or_none()
    if semester:
        return semester

    semester = Semester(semester_name=normalized, swap_allowed=False)
    db.add(semester)
    await db.flush()
    return semester


async def _get_or_create_batch(
    db: AsyncSession,
    semester_id: int,
    batch_name: str,
) -> Batch:
    normalized = _normalize_name(batch_name)
    result = await db.execute(
        select(Batch).where(
            (Batch.semester_id == semester_id)
            & (func.lower(Batch.batch_name) == normalized.lower())
        )
    )
    batch = result.scalar_one_or_none()
    if batch:
        return batch

    batch = Batch(batch_name=normalized, semester_id=semester_id)
    db.add(batch)
    await db.flush()
    return batch


async def _create_student_and_assignment(
    db: AsyncSession,
    payload: StudentBatchAssignmentRow,
    semester: Semester,
    batch: Batch,
) -> tuple[Student, StudentSemesterAssignment]:
    result = await db.execute(
        select(Student).where(Student.register_number == payload.register_number)
    )
    student = result.scalar_one_or_none()

    if not student:
        student = Student(
            register_number=payload.register_number,
            student_name=payload.student_name,
            email=payload.email,
            phone_number=payload.phone_number,
        )
        db.add(student)
        await db.flush()

    assignment = StudentSemesterAssignment(
        register_number=student.register_number,
        semester_id=semester.semester_id,
        batch_id=batch.batch_id,
        cgpa=payload.cgpa,
        active=True,
    )
    db.add(assignment)
    await db.flush()

    return student, assignment


async def bulk_create_students_with_assignments(
    db: AsyncSession,
    payloads: list[StudentBatchAssignmentRow],
) -> tuple[list[dict], list[dict]]:
    """Bulk create students and their semester batch assignments.

    Returns:
        Tuple of (created_records, failed_records)
        where created_records is a list of {student, assignment}
        and failed_records is a list of {"payload": StudentBatchAssignmentRow, "error": str}
    """
    created: list[dict] = []
    failed: list[dict] = []

    for payload in payloads:
        try:
            async with db.begin_nested():
                semester = await _get_or_create_semester(db, payload.semester_name)
                batch = await _get_or_create_batch(db, semester.semester_id, payload.batch_name)

                student, assignment = await _create_student_and_assignment(
                    db,
                    payload,
                    semester,
                    batch,
                )
                created.append({
                    "student": student,
                    "assignment": assignment,
                    "semester": semester,
                    "batch": batch,
                })
        except IntegrityError as e:
            if "student_semester_assignment_pkey" in str(e.orig):
                await _reset_assignment_sequence(db)
                try:
                    async with db.begin_nested():
                        semester = await _get_or_create_semester(db, payload.semester_name)
                        batch = await _get_or_create_batch(
                            db, semester.semester_id, payload.batch_name
                        )
                        student, assignment = await _create_student_and_assignment(
                            db,
                            payload,
                            semester,
                            batch,
                        )
                        created.append({
                            "student": student,
                            "assignment": assignment,
                            "semester": semester,
                            "batch": batch,
                        })
                        continue
                except IntegrityError:
                    failed.append({
                        "payload": payload,
                        "error": "Assignment id sequence was reset but insert still failed",
                    })
                    continue
            error_msg = "Database constraint violation"
            if "register_number" in str(e.orig):
                error_msg = f"Duplicate register_number: {payload.register_number}"
            elif "email" in str(e.orig):
                error_msg = f"Duplicate email: {payload.email}"
            elif "semester_id" in str(e.orig):
                error_msg = (
                    f"Student already assigned to semester {payload.semester_name}"
                )
            failed.append({"payload": payload, "error": error_msg})
        except Exception as e:
            failed.append({"payload": payload, "error": str(e)})

    if created:
        await db.commit()

    return created, failed


async def student_exists(db: AsyncSession, email: str) -> bool:
    result = await db.execute(select(Student).where(Student.email == email))
    return result.scalar_one_or_none() is not None
