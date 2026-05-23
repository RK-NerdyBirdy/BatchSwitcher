import logging
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.student import Student
from app.models.student_semester_assignment import StudentSemesterAssignment
from app.models.semester import Semester
from app.models.batch import Batch
from app.services.csv_service import StudentBatchAssignmentRow

# ==========================================
# SET UP LOGGING
# ==========================================
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# If running locally, this ensures logs print to your terminal
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


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

async def _get_or_create_semester(db: AsyncSession, semester_name: str) -> Semester:
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

async def _get_or_create_batch(db: AsyncSession, semester_id: int, batch_name: str) -> Batch:
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
    batch_size: int = 100,  # <-- Configurable batch size
) -> tuple[list[dict], list[dict]]:
    created: list[dict] = []
    failed: list[dict] = []

    logger.info(f"🚀 Starting bulk upload of {len(payloads)} students in batches of {batch_size}...")

    # ==========================================
    # CACHING: The massive speed boost!
    # ==========================================
    semester_cache: dict[str, Semester] = {}
    batch_cache: dict[tuple[int, str], Batch] = {}

    for i in range(0, len(payloads), batch_size):
        batch_payloads = payloads[i : i + batch_size]
        logger.info(f"⏳ Processing batch {i // batch_size + 1} (Rows {i + 1} to {min(i + batch_size, len(payloads))})")

        for payload in batch_payloads:
            try:
                async with db.begin_nested():
                    # 1. Cached Semester Lookup
                    sem_name_norm = _normalize_name(payload.semester_name).lower()
                    if sem_name_norm in semester_cache:
                        semester = semester_cache[sem_name_norm]
                    else:
                        semester = await _get_or_create_semester(db, payload.semester_name)
                        semester_cache[sem_name_norm] = semester

                    # 2. Cached Batch Lookup
                    batch_name_norm = _normalize_name(payload.batch_name).lower()
                    cache_key = (semester.semester_id, batch_name_norm)
                    if cache_key in batch_cache:
                        batch = batch_cache[cache_key]
                    else:
                        batch = await _get_or_create_batch(db, semester.semester_id, payload.batch_name)
                        batch_cache[cache_key] = batch

                    # 3. Process Student
                    student, assignment = await _create_student_and_assignment(
                        db, payload, semester, batch
                    )
                    
                    created.append({
                        "student": student,
                        "assignment": assignment,
                        "semester": semester,
                        "batch": batch,
                    })

            except IntegrityError as e:
                # Handle sequence resets just in case
                if "student_semester_assignment_pkey" in str(e.orig):
                    await _reset_assignment_sequence(db)
                    logger.warning(f"⚠️ Sequence reset triggered for {payload.register_number}")
                    # A retry block can go here if needed, but it's usually skipped to preserve speed.
                    failed.append({"payload": payload, "error": "Assignment ID sequence reset. Please re-upload this row."})
                    continue

                error_msg = "Database constraint violation"
                if "register_number" in str(e.orig):
                    error_msg = f"Duplicate register_number: {payload.register_number}"
                elif "email" in str(e.orig):
                    error_msg = f"Duplicate email: {payload.email}"
                elif "semester_id" in str(e.orig):
                    error_msg = f"Student already assigned to semester {payload.semester_name}"
                
                logger.warning(f"❌ Failed to insert {payload.register_number}: {error_msg}")
                failed.append({"payload": payload, "error": error_msg})

            except Exception as e:
                logger.error(f"❌ Unexpected error for {payload.register_number}: {str(e)}")
                failed.append({"payload": payload, "error": str(e)})

        # Commit the chunk to clear database memory before moving to the next 100 rows
        try:
            await db.commit()
            logger.info(f"✅ Batch {i // batch_size + 1} committed successfully.")
        except Exception as e:
            await db.rollback()
            logger.error(f"💥 CRITICAL: Failed to commit batch {i // batch_size + 1}! Rolling back this chunk. Error: {str(e)}")

    logger.info(f"🏁 Bulk processing complete! Success: {len(created)} | Failed: {len(failed)}")
    return created, failed


async def student_exists(db: AsyncSession, email: str) -> bool:
    result = await db.execute(select(Student).where(Student.email == email))
    return result.scalar_one_or_none() is not None