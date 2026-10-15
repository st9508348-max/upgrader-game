import json
import sqlite3
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATABASE = ROOT / "upshift.db"
HOST = "127.0.0.1"
PORT = 8000


def connection():
    database = sqlite3.connect(DATABASE)
    database.row_factory = sqlite3.Row
    return database


def initialize_database():
    with connection() as database:
        database.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS game_states (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                balance INTEGER NOT NULL,
                inventory TEXT NOT NULL,
                selected_input INTEGER,
                selected_target INTEGER,
                selected_rarity TEXT NOT NULL,
                high INTEGER NOT NULL,
                activity TEXT NOT NULL,
                successful_upgrades INTEGER NOT NULL DEFAULT 0,
                failed_upgrades INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            """
        )
        columns = {row["name"] for row in database.execute("PRAGMA table_info(game_states)")}
        if "successful_upgrades" not in columns:
            database.execute("ALTER TABLE game_states ADD COLUMN successful_upgrades INTEGER NOT NULL DEFAULT 0")
        if "failed_upgrades" not in columns:
            database.execute("ALTER TABLE game_states ADD COLUMN failed_upgrades INTEGER NOT NULL DEFAULT 0")


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def default_state():
    return {
        "balance": 2500,
        "inventory": [],
        "selectedInput": None,
        "selectedTarget": None,
        "selectedRarity": "RARE",
        "high": 0,
        "activity": [],
        "successfulUpgrades": 0,
        "failedUpgrades": 0,
    }


def user_payload(user, state):
    return {"id": user["id"], "name": user["name"], "state": state}


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 1_000_000:
            raise ValueError("Request body is too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def find_user(self, user_id):
        with connection() as database:
            return database.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    def save_state(self, user_id, state):
        now = timestamp()
        with connection() as database:
            database.execute(
                """
                INSERT INTO game_states
                    (user_id, balance, inventory, selected_input, selected_target,
                    selected_rarity, high, activity, successful_upgrades, failed_upgrades, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    balance = excluded.balance,
                    inventory = excluded.inventory,
                    selected_input = excluded.selected_input,
                    selected_target = excluded.selected_target,
                    selected_rarity = excluded.selected_rarity,
                    high = excluded.high,
                    activity = excluded.activity,
                    successful_upgrades = excluded.successful_upgrades,
                    failed_upgrades = excluded.failed_upgrades,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    int(state.get("balance", 2500)),
                    json.dumps(state.get("inventory", [])),
                    state.get("selectedInput"),
                    state.get("selectedTarget"),
                    state.get("selectedRarity", "RARE"),
                    int(state.get("high", 0)),
                    json.dumps(state.get("activity", [])),
                    int(state.get("successfulUpgrades", 0)),
                    int(state.get("failedUpgrades", 0)),
                    now,
                ),
            )
            database.execute("UPDATE users SET last_seen_at = ? WHERE id = ?", (now, user_id))

    def read_state(self, user_id):
        with connection() as database:
            row = database.execute("SELECT * FROM game_states WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return default_state()
        return {
            "balance": row["balance"],
            "inventory": json.loads(row["inventory"]),
            "selectedInput": row["selected_input"],
            "selectedTarget": row["selected_target"],
            "selectedRarity": row["selected_rarity"],
            "high": row["high"],
            "activity": json.loads(row["activity"]),
            "successfulUpgrades": row["successful_upgrades"],
            "failedUpgrades": row["failed_upgrades"],
        }

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/")
        if path == "/api/users":
            with connection() as database:
                users = database.execute(
                    "SELECT id, name, created_at, last_seen_at FROM users ORDER BY last_seen_at DESC"
                ).fetchall()
            self.send_json({"users": [dict(user) for user in users]})
            return
        if path.startswith("/api/users/") and path.endswith("/state"):
            try:
                user_id = int(path.split("/")[3])
            except (IndexError, ValueError):
                self.send_json({"error": "Invalid user id"}, HTTPStatus.BAD_REQUEST)
                return
            user = self.find_user(user_id)
            if not user:
                self.send_json({"error": "User not found"}, HTTPStatus.NOT_FOUND)
                return
            self.send_json(user_payload(user, self.read_state(user_id)))
            return
        super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/api/users":
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self.read_json()
            name = str(payload.get("name", "")).strip()
            if not name or len(name) > 24:
                raise ValueError("Name must contain 1 to 24 characters")
        except (ValueError, json.JSONDecodeError):
            self.send_json({"error": "A valid player name is required"}, HTTPStatus.BAD_REQUEST)
            return
        now = timestamp()
        with connection() as database:
            database.execute(
                "INSERT INTO users (name, created_at, last_seen_at) VALUES (?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET last_seen_at = excluded.last_seen_at",
                (name, now, now),
            )
            user = database.execute("SELECT * FROM users WHERE name = ?", (name,)).fetchone()
        self.send_json(user_payload(user, self.read_state(user["id"])), HTTPStatus.CREATED)

    def do_PUT(self):
        path = urlparse(self.path).path.rstrip("/")
        if not path.startswith("/api/users/") or not path.endswith("/state"):
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            user_id = int(path.split("/")[3])
            state = self.read_json()
            user = self.find_user(user_id)
            if not user:
                self.send_json({"error": "User not found"}, HTTPStatus.NOT_FOUND)
                return
            self.save_state(user_id, state)
            self.send_json(user_payload(user, self.read_state(user_id)))
        except (ValueError, json.JSONDecodeError):
            self.send_json({"error": "Invalid user state"}, HTTPStatus.BAD_REQUEST)

    def do_DELETE(self):
        path = urlparse(self.path).path.rstrip("/")
        if not path.startswith("/api/users/"):
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            user_id = int(path.split("/")[3])
        except (IndexError, ValueError):
            self.send_json({"error": "Invalid user id"}, HTTPStatus.BAD_REQUEST)
            return
        with connection() as database:
            result = database.execute("DELETE FROM users WHERE id = ?", (user_id,))
        if result.rowcount == 0:
            self.send_json({"error": "User not found"}, HTTPStatus.NOT_FOUND)
            return
        self.send_json({"deleted": user_id})


if __name__ == "__main__":
    initialize_database()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"UPSHIFT server running at http://{HOST}:{PORT}/upgrader.html")
    print(f"SQLite database: {DATABASE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
    finally:
        server.server_close()
