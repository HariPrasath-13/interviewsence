import sqlite3
import json
import os

def get_connection(db_path):
    """Establishes connection to the SQLite database and enables foreign keys."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    # Return rows as dictionaries for easier key-value access in python
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path):
    """Initializes the database schema if it doesn't already exist."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # 1. Main sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            timestamp TEXT DEFAULT (datetime('now', 'localtime')),
            duration REAL DEFAULT 0.0,
            dominant_emotion TEXT DEFAULT 'None',
            average_confidence REAL DEFAULT 0.0,
            positive_pct REAL DEFAULT 0.0,
            negative_pct REAL DEFAULT 0.0,
            neutral_pct REAL DEFAULT 0.0,
            recommendations TEXT DEFAULT ''
        );
    """)
    
    # 2. Detailed frame entries table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            elapsed_seconds REAL DEFAULT 0.0,
            emotion TEXT,
            confidence REAL,
            probabilities_json TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
        );
    """)
    
    conn.commit()
    conn.close()

def create_session(db_path, session_id):
    """Inserts a new empty session placeholder into the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessions (session_id, timestamp) VALUES (?, datetime('now', 'localtime'))", 
        (session_id,)
    )
    conn.commit()
    conn.close()

def add_frame_data(db_path, session_id, elapsed_seconds, emotion, confidence, probabilities):
    """Stores metrics for a single raw webcam frame in the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    probs_json = json.dumps(probabilities)
    cursor.execute(
        """
        INSERT INTO session_details (session_id, elapsed_seconds, emotion, confidence, probabilities_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, elapsed_seconds, emotion, confidence, probs_json)
    )
    conn.commit()
    conn.close()

def get_session_details(db_path, session_id):
    """Retrieves all logged frame details for a specific session sorted by elapsed time."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, session_id, elapsed_seconds, emotion, confidence, probabilities_json FROM session_details WHERE session_id = ? ORDER BY elapsed_seconds ASC",
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    details = []
    for r in rows:
        details.append({
            "id": r["id"],
            "session_id": r["session_id"],
            "elapsed_seconds": r["elapsed_seconds"],
            "emotion": r["emotion"],
            "confidence": r["confidence"],
            "probabilities": json.loads(r["probabilities_json"]) if r["probabilities_json"] else {}
        })
    return details

def get_session(db_path, session_id):
    """Retrieves a single session profile by its session_id."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT session_id, timestamp, duration, dominant_emotion, average_confidence, positive_pct, negative_pct, neutral_pct, recommendations FROM sessions WHERE session_id = ?",
        (session_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def update_session_analytics(db_path, session_id, duration, dominant_emotion, average_confidence, positive_pct, negative_pct, neutral_pct, recommendations):
    """Updates structural aggregates containing overall statistics for a practice session."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE sessions
        SET duration = ?,
            dominant_emotion = ?,
            average_confidence = ?,
            positive_pct = ?,
            negative_pct = ?,
            neutral_pct = ?,
            recommendations = ?
        WHERE session_id = ?
        """,
        (duration, dominant_emotion, average_confidence, positive_pct, negative_pct, neutral_pct, recommendations, session_id)
    )
    conn.commit()
    conn.close()

def get_all_sessions(db_path):
    """Returns all sessions in the database sorted by timestamp descendingly."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT session_id, timestamp, duration, dominant_emotion, average_confidence, positive_pct, negative_pct, neutral_pct, recommendations FROM sessions ORDER BY timestamp DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_session(db_path, session_id):
    """Removes a session (and its cascaded frame logs) completely."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()
