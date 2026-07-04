from backend.database.connection import db_session


def initialize_database() -> None:
    with db_session() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                hashed_password TEXT NOT NULL,
                theme TEXT NOT NULL DEFAULT 'system',
                preferred_gemini_model TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_login_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS revoked_tokens (
                token TEXT PRIMARY KEY,
                revoked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                original_filename TEXT,
                stored_filename TEXT,
                cleaned_filename TEXT,
                content_hash TEXT,
                file_type TEXT,
                file_size_bytes INTEGER NOT NULL DEFAULT 0,
                row_count INTEGER NOT NULL DEFAULT 0,
                column_count INTEGER NOT NULL DEFAULT 0,
                missing_value_count INTEGER NOT NULL DEFAULT 0,
                data_quality_score INTEGER,
                cleaning_report TEXT,
                status TEXT NOT NULL DEFAULT 'uploaded',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS dataset_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS dataset_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                analysis_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(dataset_id, user_id),
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                dataset_id INTEGER,
                title TEXT NOT NULL,
                filename TEXT,
                file_size_bytes INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS ai_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                dataset_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                dataset_id INTEGER,
                model_name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS activity_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )

        existing_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(datasets)").fetchall()
        }
        migrations = {
            "original_filename": "ALTER TABLE datasets ADD COLUMN original_filename TEXT",
            "stored_filename": "ALTER TABLE datasets ADD COLUMN stored_filename TEXT",
            "cleaned_filename": "ALTER TABLE datasets ADD COLUMN cleaned_filename TEXT",
            "file_type": "ALTER TABLE datasets ADD COLUMN file_type TEXT",
            "content_hash": "ALTER TABLE datasets ADD COLUMN content_hash TEXT",
            "file_size_bytes": "ALTER TABLE datasets ADD COLUMN file_size_bytes INTEGER NOT NULL DEFAULT 0",
            "row_count": "ALTER TABLE datasets ADD COLUMN row_count INTEGER NOT NULL DEFAULT 0",
            "column_count": "ALTER TABLE datasets ADD COLUMN column_count INTEGER NOT NULL DEFAULT 0",
            "missing_value_count": "ALTER TABLE datasets ADD COLUMN missing_value_count INTEGER NOT NULL DEFAULT 0",
            "data_quality_score": "ALTER TABLE datasets ADD COLUMN data_quality_score INTEGER",
            "cleaning_report": "ALTER TABLE datasets ADD COLUMN cleaning_report TEXT",
            "updated_at": "ALTER TABLE datasets ADD COLUMN updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        }
        for column, statement in migrations.items():
            if column not in existing_columns:
                connection.execute(statement)
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_datasets_user_content_hash ON datasets(user_id, content_hash)"
        )

        report_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(reports)").fetchall()
        }
        report_migrations = {
            "dataset_id": "ALTER TABLE reports ADD COLUMN dataset_id INTEGER",
            "filename": "ALTER TABLE reports ADD COLUMN filename TEXT",
            "file_size_bytes": "ALTER TABLE reports ADD COLUMN file_size_bytes INTEGER NOT NULL DEFAULT 0",
        }
        for column, statement in report_migrations.items():
            if column not in report_columns:
                connection.execute(statement)

        user_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }
        user_migrations = {
            "theme": "ALTER TABLE users ADD COLUMN theme TEXT NOT NULL DEFAULT 'system'",
            "preferred_gemini_model": "ALTER TABLE users ADD COLUMN preferred_gemini_model TEXT",
        }
        for column, statement in user_migrations.items():
            if column not in user_columns:
                connection.execute(statement)
