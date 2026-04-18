# Pawpular
Hackathon

#  Pawdium — Pet Leaderboard Platform

> IU Luddy Hacks 2026 | Dynamic Leaderboard/Ranking System

Pawdium is a social pet ranking platform where users upload photos of their pets and compete for the top spot on the leaderboard. Community likes, comments, and daily missions drive the rankings in real time.


Server runs at: http://localhost:8000  
API docs: http://localhost:8000/docs

---

## Live Demo

**Hosted URL:** https://unhurryingly-interconsonantal-vonda.ngrok-free.dev
**GitHub:** https://github.com/gk11-creator/Pawdium

---

## REST API Endpoints

### Required Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/add` | Add or update a leaderboard entry |
| `DELETE` | `/remove` | Remove a user and all their posts |
| `GET` | `/leaderboard` | Returns top 10 leaderboard (HTML page) |
| `GET` | `/info` | Returns statistics: mean, median, Q1, Q3, IQR |
| `GET` | `/performance` | Returns average endpoint execution time (ms) |

### Additional Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/register` | Register a new user |
| `POST` | `/login` | Login with username and password |
| `POST` | `/upload` | Upload a pet photo post |
| `GET` | `/posts` | Get all posts (filterable by username) |
| `POST` | `/like/{post_id}` | Like or unlike a post (toggle) |
| `GET` | `/liked/{username}` | Get all post IDs liked by a user |
| `POST` | `/comment/{post_id}` | Add a comment to a post |
| `GET` | `/comments/{post_id}` | Get all comments for a post |
| `DELETE` | `/post/{post_id}` | Delete a post (owner only) |
| `GET` | `/missions` | Get today's daily missions |
| `GET` | `/missions/{username}` | Get missions with completion status |
| `GET` | `/api/leaderboard` | Get full leaderboard as JSON |
| `GET` | `/history` | Score submission history with timestamps and filtering |
| `GET` | `/profile/{username}` | Get user profile |
| `PUT` | `/profile/{username}` | Update user profile |

---

## Ranking System

Pawdium uses a multi-factor scoring system to rank pets:

### Viral Score
Calculated on every like based on recent activity:

| Likes within 1 hour | Multiplier |
|---------------------|------------|
| 10+ likes | x1.5 |
| 20+ likes | x2.0 |
| 50+ likes | x3.0 |

### Bonus Points
Earned by completing daily missions:

| Mission | Description | Points |
|---------|-------------|--------|
| Daily Post | Upload 1 post today | +1 |
| Like Spree | Like 5 different posts today | +1 |
| Chatterbox | Leave 3 comments today | +1 |
| Viral Star | Get 5 likes within 1 hour | +5 |
| Fan Favorite | Get 10 total likes on your post | +7 |
| Conversation King | Get 5 comments on your post | +3 |
| Theme Champion | Post with this month's theme | +5 |
| Theme Supporter | Like 3 posts with this month's theme | +1 |

**Final Score = viral_score + bonus_points**

Only the best post per user (most liked) is counted toward the leaderboard.

---

## Statistics (`/info`)

Returns the following metrics for all posts:

- Mean, Median, Min, Max
- Q1, Q3, IQR
- Average & Max Viral Score

---

## 📁 Project Structure
