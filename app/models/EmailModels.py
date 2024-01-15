from pydantic import BaseModel
from sqlalchemy import Boolean, Column, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import DateTime, func


class CustomBase:
    __abstract__ = True
    created_date = Column(DateTime, server_default=func.now())
    edited_date = Column(DateTime, server_default=func.now(), onupdate=func.now())


Base = declarative_base(cls=CustomBase)


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Text, primary_key=True)
    time_sensitive = Column(Boolean)
    requires_response = Column(Boolean)
    payment_required = Column(Boolean)
    payment_received = Column(Boolean)
    attention_req = Column(Boolean)


class Acknowledge(Base):
    __tablename__ = "acknowledge"

    id = Column(Text, primary_key=True)
    acknowledge = Column(Boolean)


class Email(Base):
    __tablename__ = "emails"
    id = Column(Text, primary_key=True)
    sender = Column(Text)
    recipient = Column(Text)
    subject = Column(Text)
    body = Column(Text)
    date = Column(Text)
    snippet = Column(Text)
    link = Column(Text)


class EmailErrors(Base):
    __tablename__ = "email_errors"
    id = Column(Text, primary_key=True)
    description = Column(Text)


class Logs(Base):
    __tablename__ = "logs"
    id = Column(Text, primary_key=True)
    description = Column(Text)


if __name__ == "__main__":
    from sqlalchemy.schema import CreateTable
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("postgresql://admin:password@localhost/MyRightHand")
    Session = sessionmaker(bind=engine)
    session = Session()

    with open("schema_v0.sql", "w") as f:
        f.writelines(str("CREATE SCHEMA IF NOT EXISTS v0;"))
        f.writelines(str("SET search_path TO v0;"))
        f.write(str(CreateTable(Assessment.__table__).compile(engine)))
        f.write(str(CreateTable(Acknowledge.__table__).compile(engine)))
        f.write(str(CreateTable(Email.__table__).compile(engine)))
        f.write(str(CreateTable(EmailErrors.__table__).compile(engine)))
        f.write(str(CreateTable(Logs.__table__).compile(engine)))
