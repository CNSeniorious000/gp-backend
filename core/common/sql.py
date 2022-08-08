from sqlmodel import SQLModel, create_engine
from .secret import *

engine = create_engine(f"{dialect}+{driver}://{user}:{password}@{host}:{port}/{db}")


def create_db_and_tables():
    return SQLModel.metadata.create_all(engine)


__all__ = ["engine", "create_db_and_tables"]
