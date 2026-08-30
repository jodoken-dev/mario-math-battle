from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import datetime
import random

DATABASE_URL = "sqlite:///./database.sqlite"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PlayerRecord(Base):
    __tablename__ = "leaderboard"
    id = Column(Integer, primary_key=True, index=True)
    player_name = Column(String(50), nullable=False)
    total_coins = Column(Integer, default=0)
    rounds_cleared = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mario Math Battle Cloud API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class VerifyPayload(BaseModel):
    user_answer: int
    correct_answer: int
    difficulty: str

class SubmitScorePayload(BaseModel):
    player_name: str
    total_coins: int
    rounds_cleared: int

@app.get("/api/question")
def get_question(difficulty: str = "10"):
    is_plus = random.random() > 0.45
    if difficulty == "10":
        a = random.randint(0, 5) if is_plus else random.randint(1, 10)
        b = random.randint(0, 10 - a) if is_plus else random.randint(0, a)
        max_r = 10
    elif difficulty == "100":
        a = random.randint(10, 60) if is_plus else random.randint(20, 80)
        b = random.randint(0, 100 - a) if is_plus else random.randint(1, a - 5)
        max_r = 100
    else:
        a = random.randint(50, 500) if is_plus else random.randint(200, 700)
        b = random.randint(0, 1000 - a) if is_plus else random.randint(10, a - 20)
        max_r = 1000

    ans = a + b if is_plus else a - b
    options = {ans}
    while len(options) < 4:
        offset = random.choice([-3, -2, -1, 1, 2, 3]) * (10 if difficulty == "1000" else 1)
        fake = ans + offset
        if 0 <= fake <= max_r:
            options.add(fake)
        else:
            options.add(random.randint(0, max_r))

    opt_list = list(options)
    random.shuffle(opt_list)

    return {
        "question": f"{a} {'+' if is_plus else '-'} {b} = ?",
        "correct_answer": ans,
        "options": opt_list
    }

@app.post("/api/verify")
def verify_answer(data: VerifyPayload):
    is_correct = data.user_answer == data.correct_answer
    rewards = {"10": 5, "100": 15, "1000": 50}
    coin_earned = rewards.get(data.difficulty, 5) if is_correct else 0
    return {"is_correct": is_correct, "coin_earned": coin_earned}

@app.post("/api/score")
def submit_score(data: SubmitScorePayload, db: Session = Depends(get_db)):
    record = PlayerRecord(
        player_name=data.player_name.strip() or "Anonymous",
        total_coins=data.total_coins,
        rounds_cleared=data.rounds_cleared
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"status": "success", "id": record.id}

@app.get("/api/leaderboard")
def get_leaderboard(limit: int = 10, db: Session = Depends(get_db)):
    records = db.query(PlayerRecord)\
                .order_by(PlayerRecord.total_coins.desc(), PlayerRecord.rounds_cleared.desc())\
                .limit(limit)\
                .all()
    return [
        {
            "rank": idx + 1,
            "name": r.player_name,
            "coins": r.total_coins,
            "rounds": r.rounds_cleared
        }
        for idx, r in enumerate(records)
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)