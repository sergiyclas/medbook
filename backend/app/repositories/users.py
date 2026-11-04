from sqlalchemy import func, select

from app.models import User
from app.repositories.base import Repository


class UserRepository(Repository[User]):
    model = User

    def by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(func.lower(User.email) == email.lower()))
