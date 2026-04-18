"""
PawRank - Pet Leaderboard Server
FastAPI REST API | Hackathon Submission
"""

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
import statistics
import sqlite3
import time
import os
import shutil
import uuid
import hashlib

# ── Setup ──────────────────────────────────────────────────────────────────
os.makedirs("uploads", exist_ok=True)

app = FastAPI(title="PawRank API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static",  StaticFiles(directory="static"),  name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ── Database ───────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect("pawrank.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT UNIQUE NOT NULL,
            password     TEXT NOT NULL,
            pet_name     TEXT,
            pet_type     TEXT,
            pet_year     INTEGER,
            pet_bio      TEXT,
            pet_image    TEXT,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS posts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT NOT NULL,
            caption      TEXT,
            location     TEXT,
            image_url    TEXT NOT NULL,
            likes        INTEGER DEFAULT 0,
            theme        TEXT DEFAULT 'Bravest Pet',
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS likes (
            post_id      INTEGER,
            username     TEXT,
            PRIMARY KEY (post_id, username)
        );

        CREATE TABLE IF NOT EXISTS comments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id      INTEGER NOT NULL,
            username     TEXT NOT NULL,
            content      TEXT NOT NULL,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

init_db()

# ── Performance ────────────────────────────────────────────────────────────
endpoint_times: dict[str, list[float]] = {
    "add": [], "remove": [], "leaderboard": [], "info": [], "performance": []
}
def track(endpoint: str, fn):
    t0 = time.perf_counter()
    result = fn()
    endpoint_times[endpoint].append((time.perf_counter() - t0) * 1000)
    return result

# ── Helpers ────────────────────────────────────────────────────────────────
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

# ── Models ─────────────────────────────────────────────────────────────────
class RegisterBody(BaseModel):
    username: str
    password: str

class LoginBody(BaseModel):
    username: str
    password: str

class LikeBody(BaseModel):
    username: str

class CommentBody(BaseModel):
    username: str
    content:  str

class UpdateProfile(BaseModel):
    pet_name:  Optional[str] = None
    pet_type:  Optional[str] = None
    pet_year:  Optional[int] = None
    pet_bio:   Optional[str] = None

class RemoveEntry(BaseModel):
    username: str

# ── Page Routes ────────────────────────────────────────────────────────────
@app.get("/",            include_in_schema=False, response_class=HTMLResponse)
def page_login():       return FileResponse("static/login.html")

@app.get("/feed",        include_in_schema=False, response_class=HTMLResponse)
def page_feed():        return FileResponse("static/feed.html")

@app.get("/post",        include_in_schema=False, response_class=HTMLResponse)
def page_post():        return FileResponse("static/post.html")

@app.get("/leaderboard", include_in_schema=False, response_class=HTMLResponse)
def page_leaderboard(): return FileResponse("static/leaderboard.html")

@app.get("/profile",     include_in_schema=False, response_class=HTMLResponse)
def page_profile():     return FileResponse("static/profile.html")

# ── Auth ───────────────────────────────────────────────────────────────────
@app.post("/register", tags=["Auth"], summary="Register a new user")
def register(body: RegisterBody):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?,?)",
            (body.username, hash_password(body.password))
        )
        conn.commit()
        conn.close()
        return {"status": "registered", "username": body.username}
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(400, "Username already exists")

@app.post("/login", tags=["Auth"], summary="Login")
def login(body: LoginBody):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (body.username, hash_password(body.password))
    ).fetchone()
    conn.close()
    if not user:
        raise HTTPException(401, "Invalid username or password")
    return {"status": "ok", "username": user["username"], "pet_name": user["pet_name"]}

# ── Profile ────────────────────────────────────────────────────────────────
@app.get("/profile/{username}", tags=["Profile"], summary="Get user profile")
def get_profile(username: str):
    conn = get_db()
    user = conn.execute(
        "SELECT username,pet_name,pet_type,pet_year,pet_bio,pet_image FROM users WHERE username=?",
        (username,)
    ).fetchone()
    conn.close()
    if not user:
        raise HTTPException(404, "User not found")
    return dict(user)

@app.put("/profile/{username}", tags=["Profile"], summary="Update profile info")
def update_profile(username: str, body: UpdateProfile):
    conn = get_db()
    conn.execute("""
        UPDATE users SET
            pet_name = COALESCE(?, pet_name),
            pet_type = COALESCE(?, pet_type),
            pet_year = COALESCE(?, pet_year),
            pet_bio  = COALESCE(?, pet_bio)
        WHERE username=?
    """, (body.pet_name, body.pet_type, body.pet_year, body.pet_bio, username))
    conn.commit()
    conn.close()
    return {"status": "updated"}

@app.post("/profile/{username}/image", tags=["Profile"], summary="Upload pet profile image")
async def upload_profile_image(username: str, image: UploadFile = File(...)):
    ext      = image.filename.split(".")[-1]
    filename = f"profile_{username}.{ext}"
    filepath = f"uploads/{filename}"
    with open(filepath, "wb") as f:
        shutil.copyfileobj(image.file, f)
    conn = get_db()
    conn.execute("UPDATE users SET pet_image=? WHERE username=?", (f"/uploads/{filename}", username))
    conn.commit()
    conn.close()
    return {"status": "uploaded", "image_url": f"/uploads/{filename}"}

# ── Posts ──────────────────────────────────────────────────────────────────
@app.post("/upload", tags=["Posts"], summary="Upload a post")
async def upload_post(
    username: str      = Form(...),
    caption:  str      = Form(""),
    location: str      = Form(""),
    theme:    str      = Form("Bravest Pet"),
    image:    UploadFile = File(...)
):
    ext      = image.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    with open(f"uploads/{filename}", "wb") as f:
        shutil.copyfileobj(image.file, f)
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO posts (username, caption, location, image_url, theme) VALUES (?,?,?,?,?)",
        (username, caption, location, f"/uploads/{filename}", theme)
    )
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"status": "uploaded", "post_id": post_id}

@app.get("/posts", tags=["Posts"], summary="Get all posts")
def get_posts(username: Optional[str] = None, limit: int = 50, offset: int = 0):
    conn = get_db()
    if username:
        rows = conn.execute(
            "SELECT * FROM posts WHERE username=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (username, limit, offset)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM posts ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
    conn.close()
    return {"posts": [dict(r) for r in rows]}

@app.post("/like/{post_id}", tags=["Posts"], summary="Like or unlike a post")
def like_post(post_id: int, body: LikeBody):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO likes (post_id, username) VALUES (?,?)",
            (post_id, body.username)
        )
        conn.execute("UPDATE posts SET likes = likes + 1 WHERE id=?", (post_id,))
        conn.commit()
        likes = conn.execute("SELECT likes FROM posts WHERE id=?", (post_id,)).fetchone()[0]
        conn.close()
        return {"status": "liked", "likes": likes}
    except sqlite3.IntegrityError:
        conn.execute("DELETE FROM likes WHERE post_id=? AND username=?", (post_id, body.username))
        conn.execute("UPDATE posts SET likes = likes - 1 WHERE id=?", (post_id,))
        conn.commit()
        likes = conn.execute("SELECT likes FROM posts WHERE id=?", (post_id,)).fetchone()[0]
        conn.close()
        return {"status": "unliked", "likes": likes}

@app.post("/comment/{post_id}", tags=["Posts"], summary="Add a comment")
def add_comment(post_id: int, body: CommentBody):
    conn = get_db()
    conn.execute(
        "INSERT INTO comments (post_id, username, content) VALUES (?,?,?)",
        (post_id, body.username, body.content)
    )
    conn.commit()
    comments = conn.execute(
        "SELECT * FROM comments WHERE post_id=? ORDER BY created_at ASC",
        (post_id,)
    ).fetchall()
    conn.close()
    return {"status": "commented", "comments": [dict(c) for c in comments]}

@app.get("/comments/{post_id}", tags=["Posts"], summary="Get comments for a post")
def get_comments(post_id: int):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM comments WHERE post_id=? ORDER BY created_at ASC",
        (post_id,)
    ).fetchall()
    conn.close()
    return {"comments": [dict(r) for r in rows]}

# ── Leaderboard ────────────────────────────────────────────────────────────
@app.get("/api/leaderboard", tags=["Leaderboard"], summary="Get leaderboard by likes")
def get_leaderboard(limit: int = Query(default=20, ge=1, le=200)):
    def _():
        conn = get_db()
        rows = conn.execute("""
            SELECT p.username, u.pet_name, u.pet_type, u.pet_image,
                   SUM(p.likes) as total_likes
            FROM posts p
            LEFT JOIN users u ON p.username = u.username
            GROUP BY p.username
            ORDER BY total_likes DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        medals = ["🥇","🥈","🥉"]
        return {
            "total_entries": len(rows),
            "leaderboard": [
                {
                    "rank":        i + 1,
                    "medal":       medals[i] if i < 3 else None,
                    "username":    r["username"],
                    "pet_name":    r["pet_name"] or r["username"],
                    "pet_type":    r["pet_type"] or "",
                    "pet_image":   r["pet_image"] or "",
                    "total_likes": r["total_likes"] or 0,
                    "badge":       "🥇 Gold" if i == 0 else "🥈 Silver" if i == 1 else "🥉 Bronze" if i == 2 else ""
                }
                for i, r in enumerate(rows)
            ]
        }
    return track("leaderboard", _)

# ── Stats ──────────────────────────────────────────────────────────────────
@app.get("/info", tags=["Statistics"], summary="Get statistics")
def get_info():
    def _():
        conn = get_db()
        rows = conn.execute("SELECT likes FROM posts").fetchall()
        conn.close()
        if not rows:
            raise HTTPException(404, "No posts found")
        scores = sorted(r["likes"] for r in rows)
        n = len(scores)
        def pct(p):
            idx = p / 100 * (n - 1)
            lo, hi = int(idx), min(int(idx)+1, n-1)
            return round(scores[lo] + (idx - lo) * (scores[hi] - scores[lo]), 2)
        return {
            "total_posts": n,
            "statistics": {
                "mean":   round(statistics.mean(scores), 2),
                "median": round(statistics.median(scores), 2),
                "min":    min(scores),
                "max":    max(scores),
                "q1":     pct(25),
                "q3":     pct(75),
                "iqr":    round(pct(75) - pct(25), 2),
            }
        }
    return track("info", _)

@app.get("/performance", tags=["Statistics"], summary="Endpoint execution times")
def get_performance():
    def _():
        out = {}
        for ep, times in endpoint_times.items():
            if times:
                out[ep] = {"calls": len(times), "avg_ms": round(statistics.mean(times), 3),
                           "min_ms": round(min(times), 3), "max_ms": round(max(times), 3)}
            else:
                out[ep] = {"calls": 0, "avg_ms": None, "min_ms": None, "max_ms": None}
        return {"endpoint_performance": out}
    return track("performance", _)

@app.delete("/remove", tags=["Leaderboard"], summary="Remove user and all posts")
def remove_entry(body: RemoveEntry):
    def _():
        conn = get_db()
        conn.execute("DELETE FROM posts WHERE username=?", (body.username,))
        conn.execute("DELETE FROM users WHERE username=?", (body.username,))
        conn.commit()
        conn.close()
        return {"status": "removed", "username": body.username}
    return track("remove", _)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)