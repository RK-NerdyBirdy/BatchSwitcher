from sqlalchemy import select, text
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
    await db.commit()


async def _create_student_and_assignment(
    db: AsyncSession,
    payload: StudentBatchAssignmentRow,
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
        semester_id=payload.semester_id,
        batch_id=payload.batch_id,
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
            # Validate semester exists BEFORE creating anything
            semester_result = await db.execute(
                select(Semester).where(Semester.semester_id == payload.semester_id)
            )
            semester = semester_result.scalar_one_or_none()
            if not semester:
                failed.append({
                    "payload": payload,
                    "error": f"Semester {payload.semester_id} not found",
                })
                continue
            
            # Validate batch exists AND belongs to the semester BEFORE creating anything
            batch_result = await db.execute(
                select(Batch).where(
                    (Batch.batch_id == payload.batch_id) &
                    (Batch.semester_id == payload.semester_id)
                )
            )
            batch = batch_result.scalar_one_or_none()
            if not batch:
                failed.append({
                    "payload": payload,
                    "error": f"Batch {payload.batch_id} not found in semester {payload.semester_id}",
                })
                continue
            
            student, assignment = await _create_student_and_assignment(db, payload)
            created.append({
                "student": student,
                "assignment": assignment,
            })
        except IntegrityError as e:
            await db.rollback()
            if "student_semester_assignment_pkey" in str(e.orig):
                await _reset_assignment_sequence(db)
                try:
                    student, assignment = await _create_student_and_assignment(db, payload)
                    created.append({
                        "student": student,
                        "assignment": assignment,
                    })
                    continue
                except IntegrityError:
                    await db.rollback()
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
                error_msg = f"Student already assigned to semester {payload.semester_id}"
            failed.append({"payload": payload, "error": error_msg})
        except Exception as e:
            await db.rollback()
            failed.append({"payload": payload, "error": str(e)})

    if created:
        await db.commit()

    return created, failed


async def student_exists(db: AsyncSession, email: str) -> bool:
    result = await db.execute(select(Student).where(Student.email == email))
    return result.scalar_one_or_none() is not None
