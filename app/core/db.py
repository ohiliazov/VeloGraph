from sqlalchemy import create_engine

from app.core.models import Base

if __name__ == "__main__":
    engine = create_engine("postgresql://velograph:velograph@localhost:5433/velograph")
    Base.metadata.create_all(engine)
