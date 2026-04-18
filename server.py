"""
PawRank - Pet Leaderboard Server
FastAPI REST API | Hackathon Submission
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
import statistics
import time

app = FastAPI(
    title="PawRank API",
    description="A competitive pet leaderboard for IU students — supporting stray animal adoption.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (CSS, JS) ─────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Data store ─────────────────────────────────────────────────────────────
leaderboard: list[dict] = []
endpoint_times: dict[str, list[float]] = {
    "add": [], "remove": [], "leaderboard": [], "info": [], "performance": []
}

SEED = [
    {"username": "jiwoo_kim",    "pet_name": "Bori",   "pet_type": "Dog",     "score": 83},
    {"username": "soomin_lee",   "pet_name": "Nabi",   "pet_type": "Cat",     "score": 74},
    {"username": "dohyun_park",  "pet_name": "Mango",  "pet_type": "Hamster", "score": 61},
    {"username": "arin_choi",    "pet_name": "Kong",   "pet_type": "Rabbit",  "score": 55},
    {"username": "minjun_jung",  "pet_name": "Lucy",   "pet_type": "Dog",     "score": 38},
    {"username": "seoyeon_yoon", "pet_name": "Choco",  "pet_type": "Dog",     "score": 29},
]
_next_id = 1
for s in SEED:
    leaderboard.append({**s, "id": _next_id, "rank": _next_id, "theme": "Bravest Pet"})
    _next_id += 1


# ── Helpers ────────────────────────────────────────────────────────────────
def recalculate_ranks():
    leaderboard.sort(key=lambda x: x["score"], reverse=True)
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1

def track(endpoint: str, fn):
    t0 = time.perf_counter()
    result = fn()
    endpoint_times[endpoint].append((time.perf_counter() - t0) * 1000)
    return result


# ── Models ─────────────────────────────────────────────────────────────────
class AddEntry(BaseModel):
    username: str
    pet_name: str
    pet_type: str
    score: float
    theme: Optional[str] = "Bravest Pet"

class RemoveEntry(BaseModel):
    username: str


# ── Routes ─────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False, response_class=HTMLResponse)
def root():
    return FileResponse("static/index.html")


@app.post("/add", tags=["Leaderboard"], summary="Add or update an entry")
def add_entry(entry: AddEntry):
    global _next_id
    def _():
        global _next_id
        existing = next((e for e in leaderboard if e["username"] == entry.username), None)
        if existing:
            existing.update({"score": entry.score, "pet_name": entry.pet_name,
                             "pet_type": entry.pet_type, "theme": entry.theme})
            recalculate_ranks()
            return {"status": "updated", "entry": existing}
        new = {"id": _next_id, "username": entry.username, "pet_name": entry.pet_name,
               "pet_type": entry.pet_type, "score": entry.score, "theme": entry.theme, "rank": 0}
        _next_id += 1
        leaderboard.append(new)
        recalculate_ranks()
        return {"status": "added", "entry": new}
    return track("add", _)


@app.delete("/remove", tags=["Leaderboard"], summary="Remove an entry by username")
def remove_entry(body: RemoveEntry):
    def _():
        e = next((x for x in leaderboard if x["username"] == body.username), None)
        if not e:
            raise HTTPException(404, f"User '{body.username}' not found")
        leaderboard.remove(e)
        recalculate_ranks()
        return {"status": "removed", "removed": e}
    return track("remove", _)


@app.get("/leaderboard", tags=["Leaderboard"], summary="Get top 10 entries")
def get_leaderboard(limit: int = Query(default=10, ge=1, le=100)):
    def _():
        top = leaderboard[:limit]
        medals = ["🥇", "🥈", "🥉"]
        return {
            "theme": "Bravest Pet",
            "month": "April 2025",
            "total_entries": len(leaderboard),
            "leaderboard": [
                {"rank": e["rank"],
                 "medal": medals[e["rank"]-1] if e["rank"] <= 3 else f"#{e['rank']}",
                 "pet_name": e["pet_name"], "pet_type": e["pet_type"],
                 "owner": e["username"], "score": e["score"]}
                for e in top
            ]
        }
    return track("leaderboard", _)


@app.get("/info", tags=["Statistics"], summary="Get statistics for all entries")
def get_info():
    def _():
        if not leaderboard:
            raise HTTPException(404, "No entries found")
        scores = sorted(e["score"] for e in leaderboard)
        n = len(scores)
        def pct(p):
            idx = p / 100 * (n - 1)
            lo, hi = int(idx), min(int(idx)+1, n-1)
            return round(scores[lo] + (idx - lo) * (scores[hi] - scores[lo]), 2)
        dist = {}
        for e in leaderboard:
            dist[e["pet_type"]] = dist.get(e["pet_type"], 0) + 1
        return {
            "total_entries": n,
            "statistics": {
                "mean":   round(statistics.mean(scores), 2),
                "median": round(statistics.median(scores), 2),
                "min":    min(scores), "max": max(scores),
                "range":  round(max(scores) - min(scores), 2),
                "q1": pct(25), "q3": pct(75),
                "iqr": round(pct(75) - pct(25), 2),
            },
            "pet_type_distribution": dist,
            "top_pet": next(e["pet_name"] for e in leaderboard if e["rank"] == 1),
        }
    return track("info", _)


@app.get("/performance", tags=["Statistics"], summary="Average endpoint execution time (ms)")
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)