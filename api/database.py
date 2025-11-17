from sqlmodel import SQLModel, create_engine, Session

engine = create_engine("sqlite:////tmp/grocery.db")

def get_session():
    with Session(engine) as session:
        yield session

SQLModel.metadata.create_all(engine)
