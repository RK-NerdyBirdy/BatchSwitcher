from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.student_semester_assignment import StudentSemesterAssignment

settings = get_settings()


class SwapCandidateService:
    @staticmethod
    async def get_swap_candidates(
        db: AsyncSession,
        requester_assignment_id: int,
    ) -> list[StudentSemesterAssignment]:
        """Fetch eligible swap candidates for a requester.

        Rules:
        - Must be in the same semester as requester
        - Must NOT be in the same batch as requester
        - CGPA must be within requester_cgpa ± CGPA_TOL
        - Must be active in their assignment
        """

        requester_result = await db.execute(
            select(StudentSemesterAssignment).where(
                StudentSemesterAssignment.assignment_id == requester_assignment_id
            )
        )
        requester = requester_result.scalar_one_or_none()

        if requester is None:
            return []

        cgpa_threshold = settings.CGPA_TOL
        requester_cgpa = float(requester.cgpa)
        min_cgpa = max(0.0, requester_cgpa - cgpa_threshold)
        max_cgpa = min(10.0, requester_cgpa + cgpa_threshold)

        result = await db.execute(
            select(StudentSemesterAssignment).where(
                and_(
                    StudentSemesterAssignment.semester_id == requester.semester_id,
                    StudentSemesterAssignment.batch_id != requester.batch_id,
                    StudentSemesterAssignment.cgpa >= min_cgpa,
                    StudentSemesterAssignment.cgpa <= max_cgpa,
                    StudentSemesterAssignment.active.is_(True),
                    StudentSemesterAssignment.assignment_id != requester_assignment_id,
                )
            )
        )
        return list(result.scalars().all())


swap_candidate_service = SwapCandidateService()
