from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Depends, status
from pypdf import PdfReader
import uuid
from datetime import datetime
from typing import Annotated, Any
from random import randint
from .models import Documents, Chunks
from .database import SessionLocal
from pathlib import Path
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from . import models
import os 
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
import io
from groq import Groq
import openai
from dotenv import load_dotenv

load_dotenv()

    
app = FastAPI()

@app.get("/")


def root():
    return {"message": "hello world"}


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def get_db(): 
    db = SessionLocal()
    try:
        yield db

    finally: 
        db.close()







@app.post("/upload")

async def upload_file(file: UploadFile, db: Session = Depends(get_db)):
    content = await file.read()
    file_extension = Path(file.filename).suffix
    unique_id = uuid.uuid1()
    filename = f"{unique_id}{file_extension}"
    filePath = str(UPLOAD_DIR / filename)

    try:
        reader = PdfReader(io.BytesIO(content))
        page_count = len(reader.pages)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid PDF file structure.")


    with open(filePath, "wb") as f:
        f.write(content)

    document = Documents(
        document_name=file.filename, 
        file_path = filePath, 
        upload_time = datetime.now(), 
        file_size = len(content), 
        number_of_pages = page_count
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@app.get("/getFile")
async def get_file(db: Session = Depends(get_db)):
    return db.query(Documents).order_by(Documents.document_id).all()



def extract_text(document_id: int, db: Session):

#
    my_document = db.get(Documents, document_id)

    if not my_document: 
            raise HTTPException(status_code=404, detail="document id not found")

    file_path = Path(my_document.file_path)
    
    if not file_path.exists():
            raise HTTPException(status_code=404, detail="Physical file missing on server")

    reader = PdfReader(file_path)

    max_num_of_pages = len(reader.pages)
    extracted_text_by_page = {}
       
    for i in range(max_num_of_pages):
        extracted_text_by_page[i] = reader.pages[i].extract_text()
    return extracted_text_by_page


@app.get("/getText/{document_id}")
async def get_text(document_id: int, db: Session = Depends(get_db)):
    txt = extract_text(document_id, db)
    return txt





# def hashing_function(chunk_text):

    

#     return ""

@app.post("/langchainChunks/{document_id}")

async def lang_chunks_trial(document_id: int, db: Session = Depends(get_db)):

    extracted_pages = extract_text(document_id, db)

    entire_text = [text for text in extracted_pages.values() if text]
    text = "\n".join(entire_text)

    text_splitter = RecursiveCharacterTextSplitter(
        separators=[
            "\n\n", 
            "\n", 
            " ", 
            ".", 
            ",", 
            "\u200b", 
            "\uff0c", 
            "\u3001", 
            "\uff0e", 
            "\u3002"
        ],
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,    
        is_separator_regex=False,
    )
    texts = text_splitter.create_documents(
        texts=[text],
        metadatas=[{"document_id": document_id}]
    )


    chunk_strings = [t.page_content for t in texts]
    # hashing_function(chunk_strings)
    model = SentenceTransformer("diwank/dfe-base-en-1")
    embeddings = (model.encode(chunk_strings, task='fact', show_progress_bar = True))

    

    

    # for i, t in enumerate(texts[:5]):
    #     # print(f"--- Chunk {i+1} ({len(t.page_content)} chars) ---")
    #     print(t.page_content) 
    #     embeddings[i] = model.encode(t.page_content)

        # print()

    for i, t in enumerate(texts):
        vector_list = embeddings[i].tolist() 
        
        new_chunk = Chunks(
            document_id=document_id, 
            vector_embedding=vector_list, 
            chunk_text=t.page_content, 
            page_number=1
        )
        db.add(new_chunk)
    
    db.commit()
   


    


    return texts


@app.post("/search")
async def search(user_query: str, document_id: int, db: Session = Depends(get_db)):

    
    model = SentenceTransformer("diwank/dfe-base-en-1")
    embeddings = model.encode(user_query, task='fact', show_progress_bar = True).tolist()

   
    results = (
        db.query(Chunks)
        .filter(Chunks.document_id == document_id)
        .order_by(Chunks.vector_embedding.cosine_distance(embeddings))
        .limit(5)
        .all()
    )

    matched_chunks = [
        {
            "text": item.chunk_text,
        }
        for item in results
    ]

    print("MATCHED CHUNKS TYPE", type(matched_chunks)) #it is a list. 



    client = openai.OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1"
    )


    context_string = '\n\n'.join(chunk['text'] for chunk in matched_chunks)

    chat_completion = client.chat.completions.create(
        messages = [
            {
                "role": "system",
                "content": "Your job is to take the user's query and the relevant excerpts from their pdf document and return an answer to the user's question. Include specific quotes or cite exactly where your answer is coming from. Respond clearly and patiently. If you are unable to determine an answer, say I don't know.    "
            },
            {
                "role": "user",
                "content": 
                (
                    f"User Question: {user_query}\n\n"
                    f"Relevant Document Exerpt(s):\n\n"
                    f"{context_string}"
                )
            }
        ],
        model = "openai/gpt-oss-20b"
    )


    response = chat_completion.choices[0].message.content
    return response



