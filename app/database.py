from sqlalchemy import create_engine
from dotenv import load_dotenv
import os 
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from .models import Base
load_dotenv()

database_url = os.getenv("DATABASE_URL")
engine = create_engine(database_url, pool_size=50, echo=True, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine)

Base.metadata.create_all(bind=engine)


