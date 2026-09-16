from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column, relationship
import numpy as np
from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, func, BigInteger, Text, String, ForeignKey  
import datetime


class Base(DeclarativeBase):
    pass

class Documents(Base):
    __tablename__ = "document"
    document_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_name: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str] = mapped_column(Text)
    upload_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
    file_size: Mapped[int] = mapped_column(BigInteger)
    number_of_pages: Mapped[int]


class Chunks(Base):
    __tablename__ = "chunk"
    chunk_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.document_id"),index=True) #foreign key 
    vector_embedding: Mapped[np.ndarray] = mapped_column(Vector(768)) 
    chunk_text: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int]
