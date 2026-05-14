from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch import Batch
from app.models.student_semester_assignment import StudentSemesterAssignment


class AnalyticsService:
    @staticmethod
    async def count_students_above_cgpa(
        db: AsyncSession,
        min_cgpa: float,
    ) -> dict:
        """Count active students with CGPA >= min_cgpa by semester."""
        result = await db.execute(
            select(
                StudentSemesterAssignment.semester_id,
                func.count(StudentSemesterAssignment.assignment_id).label("count"),
            ).where(
                (StudentSemesterAssignment.cgpa >= min_cgpa)
                & (StudentSemesterAssignment.active.is_(True))
            )
            .group_by(StudentSemesterAssignment.semester_id)
        )

        rows = result.all()
        return {
            "threshold": min_cgpa,
            "by_semester": [
                {"semester_id": row[0], "count": row[1]}
                for row in rows
            ],
            "total": sum(row[1] for row in rows),
        }

    @staticmethod
    async def batch_cgpa_distribution(
        db: AsyncSession,
    ) -> dict:
        """Get average CGPA per batch by semester."""
        result = await db.execute(
            select(
                StudentSemesterAssignment.semester_id,
                Batch.batch_id,
                Batch.batch_name,
                func.avg(StudentSemesterAssignment.cgpa).label("avg_cgpa"),
                func.count(StudentSemesterAssignment.assignment_id).label("count"),
            )
            .join(Batch, StudentSemesterAssignment.batch_id == Batch.batch_id)
            .where(StudentSemesterAssignment.active.is_(True))
            .group_by(
                StudentSemesterAssignment.semester_id,
                Batch.batch_id,
                Batch.batch_name,
            )
        )

        rows = result.all()
        distribution: dict = {}

        for semester_id, batch_id, batch_name, avg_cgpa, count in rows:
            if semester_id not in distribution:
                distribution[semester_id] = {
                    "semester_id": semester_id,
                    "batches": [],
                }
            distribution[semester_id]["batches"].append(
                {
                    "batch_id": batch_id,
                    "batch_name": batch_name,
                    "avg_cgpa": float(avg_cgpa) if avg_cgpa else 0.0,
                    "student_count": count,
                }
            )

        return {
            "distribution": list(distribution.values()),
            "total_batches": len({row[1] for row in rows}),
        }

    @staticmethod
    async def batch_stats_by_semester(
        db: AsyncSession,
        semester_id: int,
    ) -> dict:
        """Get detailed stats for all batches in a semester."""
        result = await db.execute(
            select(
                Batch.batch_id,
                Batch.batch_name,
                func.count(StudentSemesterAssignment.assignment_id).label("count"),
                func.avg(StudentSemesterAssignment.cgpa).label("avg_cgpa"),
                func.min(StudentSemesterAssignment.cgpa).label("min_cgpa"),
                func.max(StudentSemesterAssignment.cgpa).label("max_cgpa"),
            )
            .join(Batch, StudentSemesterAssignment.batch_id == Batch.batch_id)
            .where(
                (StudentSemesterAssignment.semester_id == semester_id)
                & (StudentSemesterAssignment.active.is_(True))
            )
            .group_by(Batch.batch_id, Batch.batch_name)
        )

        rows = result.all()
        return {
            "semester_id": semester_id,
            "batches": [
                {
                    "batch_id": row[0],
                    "batch_name": row[1],
                    "student_count": row[2],
                    "avg_cgpa": float(row[3]) if row[3] else 0.0,
                    "min_cgpa": float(row[4]) if row[4] else 0.0,
                    "max_cgpa": float(row[5]) if row[5] else 0.0,
                }
                for row in rows
            ],
        }


analytics_service = AnalyticsService()
