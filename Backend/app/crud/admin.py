from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin


async def get_admin_by_email(db: AsyncSession, admin_email: str) -> Admin | None:
    result = await db.execute(select(Admin).where(Admin.admin_email == admin_email))
    return result.scalar_one_or_none()


async def get_admin_by_id(db: AsyncSession, admin_id: int) -> Admin | None:
    result = await db.execute(select(Admin).where(Admin.admin_id == admin_id))
    return result.scalar_one_or_none()
