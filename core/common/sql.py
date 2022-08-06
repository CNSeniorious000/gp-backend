from sqlmodel import create_engine, SQLModel
from .secret import *

engine = create_engine(f"{dialect}+{driver}://{user}:{password}@{host}:{port}/{db}")


def create_all():
    return SQLModel.metadata.create_all(engine)


__all__ = {"engine", "create_all"}
