from sqlalchemy.orm import Session

from app.db.base import Base


# Repository (PoEAA): hides SQLAlchemy queries behind intention-revealing methods.
# The shared Session is the Unit of Work – repositories flush, services commit.
class Repository[T: Base]:
    model: type[T]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: int) -> T | None:
        return self.session.get(self.model, entity_id)

    def add(self, entity: T) -> T:
        self.session.add(entity)
        self.session.flush()
        return entity

    def delete(self, entity: T) -> None:
        self.session.delete(entity)
        self.session.flush()
