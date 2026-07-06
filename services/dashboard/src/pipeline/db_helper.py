"""
KAVE Intelligent Manufacturing — PostgreSQL Database Helper
=============================================================
Provides connection management, table initialization, and CRUD
operations for the production_scenarios and defect_logs tables.

Environment Variables:
    DB_HOST, DB_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

Author: KAVE Engineering Team
Version: 2.0.0
"""

import os
import time
import psycopg2


class PostgreSQLHelper:
    """
    Helper class for PostgreSQL database operations.
    Handles connection management, table creation, and data insertion
    with retry logic for containerized environments.
    """

    # Maximum connection retry attempts (containers may start slowly)
    MAX_RETRIES = 5
    RETRY_DELAY = 3  # seconds between retries

    def __init__(self):
        """Initialize database configuration from environment variables."""
        self.db_config = {
            "dbname": os.environ.get("POSTGRES_DB", "kave_db"),
            "user": os.environ.get("POSTGRES_USER", "admin"),
            "password": os.environ.get("POSTGRES_PASSWORD", "kave_pass"),
            "host": os.environ.get("DB_HOST", "localhost"),
            "port": os.environ.get("DB_PORT", "5432"),
        }

    def _get_connection(self):
        """
        Create a new database connection with retry logic.
        Retries up to MAX_RETRIES times with exponential backoff,
        which is essential when running in Docker containers where
        PostgreSQL may take a few seconds to become ready.

        Returns:
            psycopg2.connection: Active database connection.

        Raises:
            psycopg2.OperationalError: If all retry attempts fail.
        """
        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                conn = psycopg2.connect(**self.db_config)
                return conn
            except psycopg2.OperationalError as e:
                last_error = e
                wait_time = self.RETRY_DELAY * attempt
                print(
                    f"[PostgreSQL] Connection attempt {attempt}/{self.MAX_RETRIES} "
                    f"failed. Retrying in {wait_time}s... Error: {e}"
                )
                time.sleep(wait_time)

        raise psycopg2.OperationalError(
            f"[PostgreSQL] All {self.MAX_RETRIES} connection attempts failed. "
            f"Last error: {last_error}"
        )

    def initialize_database(self):
        """
        Create the production_scenarios table if it does not exist.
        Called once at application startup.
        """
        query = """
        CREATE TABLE IF NOT EXISTS production_scenarios (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            scenario_type VARCHAR(50) NOT NULL,
            quarter VARCHAR(50) NOT NULL,
            department VARCHAR(50) NOT NULL,
            targeted_productivity FLOAT NOT NULL,
            predicted_productivity FLOAT NOT NULL,
            over_time FLOAT NOT NULL,
            incentive FLOAT NOT NULL,
            no_of_workers FLOAT NOT NULL
        );
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    conn.commit()
            print("[PostgreSQL] Table 'production_scenarios' is ready.")
        except Exception as e:
            print(f"[PostgreSQL] Init Error: {e}")

    def insert_scenario(
        self, scenario_type, quarter, department,
        target_prod, pred_prod, overtime, incentive, workers
    ):
        """
        Insert a simulation or optimization scenario result into PostgreSQL.

        Args:
            scenario_type: Type of scenario (e.g., 'Custom_What_If', 'Golden_Plan').
            quarter: Production quarter.
            department: Department name.
            target_prod: Targeted productivity value.
            pred_prod: Predicted productivity value.
            overtime: Overtime minutes allocated.
            incentive: Incentive budget in USD.
            workers: Number of workers allocated.

        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        query = """
        INSERT INTO production_scenarios
        (scenario_type, quarter, department, targeted_productivity,
         predicted_productivity, over_time, incentive, no_of_workers)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (
                        scenario_type, quarter, department,
                        float(target_prod), float(pred_prod),
                        float(overtime), float(incentive), float(workers)
                    ))
                    conn.commit()
            return True, None
        except Exception as e:
            print(f"[PostgreSQL] Insert Error: {e}")
            return False, str(e)
