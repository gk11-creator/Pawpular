from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
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
from datetime import datetime, timedelta

os.makedirs("uploads", exist_ok=True)

app = FastAPI(title="Pawdium API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static",  StaticFiles(directory="static"),  name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

def get_db():
    conn = sqlite3.connect("pawrank.db")
    conn.row_factory = sqlite3.Row
    return conn

def today_str() -> str:
    return datetime.now().strftime('%Y-%m-%d')

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def generate_daily_missions():
    conn = get_db()
    today = today_str()
    existing = conn.execute(
        "SELECT id FROM missions WHERE date=?", (today,)
    ).fetchone()
    if not existing:
        missions = [
            ("📸 Daily Post",        "Upload 1 post today",                    "post_today",       1,  1),
            ("❤️ Like Spree",         "Like 5 different posts today",           "likes_given",      5,  1),
            ("💬 Chatterbox",         "Leave 3 comments today",                 "comments_given",   3,  1),
            ("🔥 Viral Star",         "Get 5 likes within 1 hour on your post", "hourly_likes",     5,  5),
            ("👑 Fan Favorite",       "Get 10 total likes on your post",        "likes_received",   10, 7),
            ("💌 Conversation King",  "Get 5 comments on your post",            "comments_received",5,  3),
            ("🦁 Theme Champion",     "Post with this month's theme",           "theme_post",       1,  5),
            ("🌟 Theme Supporter",    "Like 3 posts with this month's theme",   "theme_likes",      3,  1),
        ]
        for title, desc, mtype, target, bonus in missions:
            conn.execute("""
                INSERT OR IGNORE INTO missions
                (title, description, mission_type, target_value, bonus_points, date)
                VALUES (?,?,?,?,?,?)
            """, (title, desc, mtype, target, bonus, today))
        conn.commit()
    conn.close()

def calculate_viral_score(post_id: int, conn) -> float:
    one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    post = conn.execute("SELECT likes FROM posts WHERE id=?", (post_id,)).fetchone()
    if not post:
        return 0.0
    total  = post["likes"]
    recent = conn.execute(
        "SELECT COUNT(*) as cnt FROM likes WHERE post_id=? AND created_at >= ?",
        (post_id, one_hour_ago)
    ).fetchone()["cnt"]
    if recent >= 50:   multiplier = 3.0
    elif recent >= 20: multiplier = 2.0
    elif recent >= 10: multiplier = 1.5
    else:              multiplier = 1.0
    return round(total + (recent * multiplier), 2)

def check_and_complete_mission(username: str, mission_type: str, conn) -> tuple:
    today        = today_str()
    one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')

    mission = conn.execute(
        "SELECT * FROM missions WHERE date=? AND mission_type=?",
        (today, mission_type)
    ).fetchone()
    if not mission:
        return None, 0

    already = conn.execute(
        "SELECT id FROM mission_completions WHERE mission_id=? AND username=?",
        (mission["id"], username)
    ).fetchone()
    if already:
        return None, 0

    count = 0

    if mission_type == "post_today":
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM posts WHERE username=? AND DATE(created_at)=?",
            (username, today)
        ).fetchone()["cnt"]

    elif mission_type == "likes_given":
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM likes WHERE username=? AND DATE(created_at)=?",
            (username, today)
        ).fetchone()["cnt"]

    elif mission_type == "comments_given":
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM comments WHERE username=? AND DATE(created_at)=?",
            (username, today)
        ).fetchone()["cnt"]

    elif mission_type == "hourly_likes":
        latest_post = conn.execute(
            "SELECT id FROM posts WHERE username=? ORDER BY created_at DESC LIMIT 1",
            (username,)
        ).fetchone()
        if latest_post:
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM likes WHERE post_id=? AND created_at >= ?",
                (latest_post["id"], one_hour_ago)
            ).fetchone()["cnt"]

    elif mission_type == "likes_received":
        latest_post = conn.execute(
            "SELECT likes FROM posts WHERE username=? ORDER BY likes DESC LIMIT 1",
            (username,)
        ).fetchone()
        if latest_post:
            count = latest_post["likes"]

    elif mission_type == "comments_received":
        latest_post = conn.execute(
            "SELECT id FROM posts WHERE username=? ORDER BY created_at DESC LIMIT 1",
            (username,)
        ).fetchone()
        if latest_post:
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM comments WHERE post_id=?",
                (latest_post["id"],)
            ).fetchone()["cnt"]

    elif mission_type == "theme_post":
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM posts WHERE username=? AND theme='Bravest Pet' AND DATE(created_at)=?",
            (username, today)
        ).fetchone()["cnt"]

    elif mission_type == "theme_likes":
        count = conn.execute(
            """SELECT COUNT(*) as cnt FROM likes l
               JOIN posts p ON l.post_id = p.id
               WHERE l.username=? AND p.theme='Bravest Pet' AND DATE(l.created_at)=?""",
            (username, today)
        ).fetchone()["cnt"]

    if count >= mission["target_value"]:
        conn.execute(
            "INSERT OR IGNORE INTO mission_completions (mission_id, username) VALUES (?,?)",
            (mission["id"], username)
        )
        conn.execute(
            "UPDATE users SET bonus_points = bonus_points + ? WHERE username=?",
            (mission["bonus_points"], username)
        )
        conn.commit()
        return mission["title"], mission["bonus_points"]

    return None, 0

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
            bonus_points INTEGER DEFAULT 0,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS posts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT NOT NULL,
            caption      TEXT,
            location     TEXT,
            image_url    TEXT NOT NULL,
            likes        INTEGER DEFAULT 0,
            viral_score  REAL DEFAULT 0,
            theme        TEXT DEFAULT 'Bravest Pet',
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS likes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id      INTEGER,
            username     TEXT,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_id, username)
        );
        CREATE TABLE IF NOT EXISTS comments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id      INTEGER NOT NULL,
            username     TEXT NOT NULL,
            content      TEXT NOT NULL,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS missions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT NOT NULL,
            description  TEXT NOT NULL,
            mission_type TEXT NOT NULL,
            target_value INTEGER NOT NULL,
            bonus_points INTEGER NOT NULL,
            date         TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS mission_completions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            mission_id   INTEGER NOT NULL,
            username     TEXT NOT NULL,
            completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(mission_id, username)
        );
    """)
    conn.commit()
    conn.close()

init_db()
generate_daily_missions()

endpoint_times: dict[str, list[float]] = {
    "add": [], "remove": [], "leaderboard": [], "info": [], "performance": []
}

def track(endpoint: str, fn):
    t0 = time.perf_counter()
    result = fn()
    endpoint_times[endpoint].append((time.perf_counter() - t0) * 1000)
    return result


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
    pet_name: Optional[str] = None
    pet_type: Optional[str] = None
    pet_year: Optional[int] = None
    pet_bio:  Optional[str] = None

class RemoveEntry(BaseModel):
    username: str


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


@app.post("/register", tags=["Auth"])
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

@app.post("/login", tags=["Auth"])
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


@app.get("/profile/{username}", tags=["Profile"])
def get_profile(username: str):
    conn = get_db()
    user = conn.execute(
        "SELECT username,pet_name,pet_type,pet_year,pet_bio,pet_image,bonus_points FROM users WHERE username=?",
        (username,)
    ).fetchone()
    conn.close()
    if not user:
        raise HTTPException(404, "User not found")
    return dict(user)

@app.put("/profile/{username}", tags=["Profile"])
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

@app.post("/profile/{username}/image", tags=["Profile"])
async def upload_profile_image(username: str, image: UploadFile = File(...)):
    ext      = image.filename.split(".")[-1]
    filename = f"profile_{username}.{ext}"
    with open(f"uploads/{filename}", "wb") as f:
        shutil.copyfileobj(image.file, f)
    conn = get_db()
    conn.execute("UPDATE users SET pet_image=? WHERE username=?",
                 (f"/uploads/{filename}", username))
    conn.commit()
    conn.close()
    return {"status": "uploaded", "image_url": f"/uploads/{filename}"}


@app.post("/upload", tags=["Posts"])
async def upload_post(
    username: str        = Form(...),
    caption:  str        = Form(""),
    location: str        = Form(""),
    image:    UploadFile = File(...)
):
    ext      = image.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    with open(f"uploads/{filename}", "wb") as f:
        shutil.copyfileobj(image.file, f)
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO posts (username, caption, location, image_url, theme) VALUES (?,?,?,?,?)",
        (username, caption, location, f"/uploads/{filename}", "Bravest Pet")
    )
    post_id = cursor.lastrowid
    conn.commit()

    completed_missions = []
    bonus_total = 0
    for mtype in ["post_today", "theme_post"]:
        title, bonus = check_and_complete_mission(username, mtype, conn)
        if title:
            completed_missions.append(title)
            bonus_total += bonus

    conn.close()
    return {
        "status": "uploaded",
        "post_id": post_id,
        "missions_completed": completed_missions,
        "bonus_points": bonus_total
    }

@app.get("/posts", tags=["Posts"])
def get_posts(username: Optional[str] = None, limit: int = 50, offset: int = 0):
    conn = get_db()
    if username:
        rows = conn.execute(
            """SELECT p.*, u.pet_image
               FROM posts p
               LEFT JOIN users u ON p.username = u.username
               WHERE p.username=?
               ORDER BY p.created_at DESC LIMIT ? OFFSET ?""",
            (username, limit, offset)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT p.*, u.pet_image
               FROM posts p
               LEFT JOIN users u ON p.username = u.username
               ORDER BY p.created_at DESC LIMIT ? OFFSET ?""",
            (limit, offset)
        ).fetchall()
    conn.close()
    return {"posts": [dict(r) for r in rows]}

@app.post("/like/{post_id}", tags=["Posts"])
def like_post(post_id: int, body: LikeBody):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO likes (post_id, username) VALUES (?,?)",
            (post_id, body.username)
        )
        conn.execute("UPDATE posts SET likes = likes + 1 WHERE id=?", (post_id,))
        viral = calculate_viral_score(post_id, conn)
        conn.execute("UPDATE posts SET viral_score=? WHERE id=?", (viral, post_id))
        conn.commit()

        likes = conn.execute(
            "SELECT likes FROM posts WHERE id=?", (post_id,)
        ).fetchone()[0]

        post_owner = conn.execute(
            "SELECT username, theme FROM posts WHERE id=?", (post_id,)
        ).fetchone()

        completed_missions = []
        bonus_total = 0

        for mtype in ["likes_given", "theme_likes"]:
            title, bonus = check_and_complete_mission(body.username, mtype, conn)
            if title:
                completed_missions.append(title)
                bonus_total += bonus

        if post_owner:
            for mtype in ["hourly_likes", "likes_received"]:
                title, bonus = check_and_complete_mission(post_owner["username"], mtype, conn)
                if title:
                    completed_missions.append(title)
                    bonus_total += bonus

        conn.close()
        return {
            "status": "liked",
            "likes": likes,
            "viral_score": viral,
            "missions_completed": completed_missions,
            "bonus_points": bonus_total
        }
    except sqlite3.IntegrityError:
        conn.execute("DELETE FROM likes WHERE post_id=? AND username=?",
                     (post_id, body.username))
        conn.execute("UPDATE posts SET likes = likes - 1 WHERE id=?", (post_id,))
        viral = calculate_viral_score(post_id, conn)
        conn.execute("UPDATE posts SET viral_score=? WHERE id=?", (viral, post_id))
        conn.commit()
        likes = conn.execute(
            "SELECT likes FROM posts WHERE id=?", (post_id,)
        ).fetchone()[0]
        conn.close()
        return {"status": "unliked", "likes": likes, "viral_score": viral}

@app.post("/comment/{post_id}", tags=["Posts"])
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

    post_owner = conn.execute(
        "SELECT username FROM posts WHERE id=?", (post_id,)
    ).fetchone()

    completed_missions = []
    bonus_total = 0

    title, bonus = check_and_complete_mission(body.username, "comments_given", conn)
    if title:
        completed_missions.append(title)
        bonus_total += bonus

    if post_owner:
        title, bonus = check_and_complete_mission(post_owner["username"], "comments_received", conn)
        if title:
            completed_missions.append(title)
            bonus_total += bonus

    conn.close()
    return {
        "status": "commented",
        "comments": [dict(c) for c in comments],
        "missions_completed": completed_missions,
        "bonus_points": bonus_total
    }

@app.delete("/post/{post_id}", tags=["Posts"])
def delete_post(post_id: int, body: LikeBody):
    conn = get_db()
    post = conn.execute(
        "SELECT username FROM posts WHERE id=?", (post_id,)
    ).fetchone()
    if not post:
        raise HTTPException(404, "Post not found")
    if post["username"] != body.username:
        raise HTTPException(403, "Not your post")
    conn.execute("DELETE FROM posts WHERE id=?", (post_id,))
    conn.execute("DELETE FROM likes WHERE post_id=?", (post_id,))
    conn.execute("DELETE FROM comments WHERE post_id=?", (post_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

@app.get("/comments/{post_id}", tags=["Posts"])
def get_comments(post_id: int):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM comments WHERE post_id=? ORDER BY created_at ASC",
        (post_id,)
    ).fetchall()
    conn.close()
    return {"comments": [dict(r) for r in rows]}

@app.get("/liked/{username}", tags=["Posts"])
def get_liked_posts(username: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT post_id FROM likes WHERE username=?", (username,)
    ).fetchall()
    conn.close()
    return {"liked_post_ids": [r["post_id"] for r in rows]}

@app.get("/missions", tags=["Missions"])
def get_missions():
    conn = get_db()
    today = today_str()
    missions = conn.execute(
        "SELECT * FROM missions WHERE date=?", (today,)
    ).fetchall()
    conn.close()
    return {"missions": [dict(m) for m in missions]}

@app.get("/missions/{username}", tags=["Missions"])
def get_user_missions(username: str):
    conn = get_db()
    today = today_str()
    missions = conn.execute(
        "SELECT * FROM missions WHERE date=?", (today,)
    ).fetchall()
    result = []
    for m in missions:
        completed = conn.execute(
            "SELECT id FROM mission_completions WHERE mission_id=? AND username=?",
            (m["id"], username)
        ).fetchone()
        result.append({**dict(m), "completed": completed is not None})
    conn.close()
    return {"missions": result}


@app.get("/api/leaderboard", tags=["Leaderboard"])
def get_api_leaderboard(limit: int = Query(default=20, ge=1, le=200)):
    def _():
        conn = get_db()
        rows = conn.execute("""
            SELECT u.username, u.pet_name, u.pet_type, u.pet_image,
                   best.likes as best_likes,
                   best.viral_score as top_viral,
                   best.image_url as best_post_image,
                   COALESCE(u.bonus_points, 0) as bonus_points
            FROM users u
            JOIN posts best ON best.id = (
                SELECT id FROM posts
                WHERE username = u.username
                ORDER BY likes DESC
                LIMIT 1
            )
            ORDER BY (best.viral_score + COALESCE(u.bonus_points, 0)) DESC,
                     best.likes DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        medals = ["🥇","🥈","🥉"]
        return {
            "total_entries": len(rows),
            "leaderboard": [
                {
                    "rank":            i + 1,
                    "medal":           medals[i] if i < 3 else None,
                    "username":        r["username"],
                    "pet_name":        r["pet_name"] or r["username"],
                    "pet_type":        r["pet_type"] or "",
                    "pet_image":       r["pet_image"] or "",
                    "best_post_image": r["best_post_image"] or "",
                    "total_likes":     r["best_likes"] or 0,
                    "viral_score":     round(r["top_viral"] or 0, 2),
                    "bonus_points":    r["bonus_points"],
                    "total_score":     round((r["top_viral"] or 0) + r["bonus_points"], 2),
                    "badge":           "🥇 Gold" if i == 0 else "🥈 Silver" if i == 1 else "🥉 Bronze" if i == 2 else ""
                }
                for i, r in enumerate(rows)
            ]
        }
    return track("leaderboard", _)

@app.get("/leaderboard/data", tags=["Leaderboard"], summary="Get top 10 leaderboard")
def get_leaderboard_data(limit: int = Query(default=10, ge=1, le=200)):
    def _():
        conn = get_db()
        rows = conn.execute("""
            SELECT u.username, u.pet_name, u.pet_type,
                   best.likes as best_likes,
                   best.viral_score as top_viral,
                   COALESCE(u.bonus_points, 0) as bonus_points
            FROM users u
            JOIN posts best ON best.id = (
                SELECT id FROM posts
                WHERE username = u.username
                ORDER BY likes DESC
                LIMIT 1
            )
            ORDER BY (best.viral_score + COALESCE(u.bonus_points, 0)) DESC,
                     best.likes DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        medals = ["🥇","🥈","🥉"]
        return {
            "total_entries": len(rows),
            "leaderboard": [
                {
                    "rank":         i + 1,
                    "medal":        medals[i] if i < 3 else f"#{i+1}",
                    "username":     r["username"],
                    "pet_name":     r["pet_name"] or r["username"],
                    "pet_type":     r["pet_type"] or "",
                    "total_likes":  r["best_likes"] or 0,
                    "viral_score":  round(r["top_viral"] or 0, 2),
                    "bonus_points": r["bonus_points"],
                    "total_score":  round((r["top_viral"] or 0) + r["bonus_points"], 2),
                }
                for i, r in enumerate(rows)
            ]
        }
    return track("leaderboard", _)

@app.delete("/remove", tags=["Leaderboard"], summary="Remove user and all posts")
def remove_entry(body: RemoveEntry):
    def _():
        conn = get_db()
        conn.execute("DELETE FROM posts    WHERE username=?", (body.username,))
        conn.execute("DELETE FROM users    WHERE username=?", (body.username,))
        conn.execute("DELETE FROM likes    WHERE username=?", (body.username,))
        conn.execute("DELETE FROM comments WHERE username=?", (body.username,))
        conn.commit()
        conn.close()
        return {"status": "removed", "username": body.username}
    return track("remove", _)

@app.get("/info", tags=["Statistics"], summary="Get statistics")
def get_info():
    def _():
        conn = get_db()
        rows = conn.execute("SELECT likes, viral_score FROM posts").fetchall()
        conn.close()
        if not rows:
            raise HTTPException(404, "No posts found")
        scores = sorted(r["likes"] for r in rows)
        virals = sorted(r["viral_score"] for r in rows)
        n = len(scores)
        def pct(arr, p):
            idx = p / 100 * (n - 1)
            lo, hi = int(idx), min(int(idx)+1, n-1)
            return round(arr[lo] + (idx - lo) * (arr[hi] - arr[lo]), 2)
        return {
            "total_posts": n,
            "statistics": {
                "mean":      round(statistics.mean(scores), 2),
                "median":    round(statistics.median(scores), 2),
                "min":       min(scores),
                "max":       max(scores),
                "q1":        pct(scores, 25),
                "q3":        pct(scores, 75),
                "iqr":       round(pct(scores, 75) - pct(scores, 25), 2),
                "avg_viral": round(statistics.mean(virals), 2),
                "max_viral": max(virals),
            }
        }
    return track("info", _)

@app.get("/performance", tags=["Statistics"], summary="Endpoint execution times")
def get_performance():
    def _():
        out = {}
        for ep, times in endpoint_times.items():
            if times:
                out[ep] = {
                    "calls":  len(times),
                    "avg_ms": round(statistics.mean(times), 3),
                    "min_ms": round(min(times), 3),
                    "max_ms": round(max(times), 3)
                }
            else:
                out[ep] = {"calls": 0, "avg_ms": None, "min_ms": None, "max_ms": None}
        return {"endpoint_performance": out}
    return track("performance", _)

@app.get("/history", tags=["Statistics"], summary="Score submission history with timestamps")
def get_history(
    username: Optional[str] = None,
    start:    Optional[str] = None,
    end:      Optional[str] = None,
    limit:    int = Query(default=50, ge=1, le=500)
):
    conn = get_db()
    query = """
        SELECT l.username, l.post_id, l.created_at,
               p.viral_score, p.likes, p.caption
        FROM likes l
        JOIN posts p ON l.post_id = p.id
        WHERE 1=1
    """
    params = []

    if username:
        query += " AND l.username = ?"
        params.append(username)
    if start:
        query += " AND DATE(l.created_at) >= ?"
        params.append(start)
    if end:
        query += " AND DATE(l.created_at) <= ?"
        params.append(end)

    query += " ORDER BY l.created_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return {
        "total": len(rows),
        "filters": {
            "username": username,
            "start":    start,
            "end":      end
        },
        "history": [
            {
                "username":    r["username"],
                "post_id":     r["post_id"],
                "timestamp":   r["created_at"],
                "likes":       r["likes"],
                "viral_score": r["viral_score"],
                "caption":     r["caption"] or ""
            }
            for r in rows
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)