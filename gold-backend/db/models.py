import sqlite3
import os

def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db(db_path: str):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS gold_price (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL UNIQUE,
            xau_usd   REAL,
            au9999    REAL,
            usd_cny   REAL,
            premium   REAL
        );

        CREATE TABLE IF NOT EXISTS macro_indicators (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            date         DATE NOT NULL UNIQUE,
            tips_10y     REAL,
            dxy          REAL,
            spdr_tonnes  REAL,
            cot_net_long INTEGER,
            vix          REAL
        );

        CREATE TABLE IF NOT EXISTS cb_events (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date    DATE NOT NULL,
            country       TEXT DEFAULT 'CN',
            action        TEXT,
            amount_tonnes REAL,
            impact_score  REAL,
            source_url    TEXT,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS rule_scores (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            calc_time       DATETIME NOT NULL,
            total_score     INTEGER,
            signal          TEXT,
            confidence      REAL,
            indicator_scores TEXT,
            weights_used    TEXT
        );

        CREATE TABLE IF NOT EXISTS prediction_log (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            pred_date           DATE NOT NULL,
            target_date         DATE NOT NULL,
            predicted_direction TEXT,
            predicted_change_pct REAL,
            rule_score           INTEGER,
            llm_consensus        TEXT,
            debate_transcript    TEXT,
            actual_px_change     REAL,
            is_correct           INTEGER,
            error_reason         TEXT
        );
    """)

    conn.commit()
    conn.close()
