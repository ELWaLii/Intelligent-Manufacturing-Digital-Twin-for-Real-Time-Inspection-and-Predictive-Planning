import psycopg2
import os

class PostgreSQLHelper:
    def __init__(self):
        self.db_config = {
            "dbname": os.environ.get("DB_NAME", "kave_db"),
            "user": os.environ.get("DB_USER", "admin"),
            "password": os.environ.get("DB_PASSWORD", "kave_pass"),
            # التعديل هنا: خلينا الافتراضي localhost عشان يشتغل من على جهازك
            "host": os.environ.get("DB_HOST", "localhost"), 
            "port": "5432"
        }

    def _get_connection(self):
        return psycopg2.connect(**self.db_config)

    def initialize_database(self):
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

    def insert_scenario(self, scenario_type, quarter, department, target_prod, pred_prod, overtime, incentive, workers):
        query = """
        INSERT INTO production_scenarios 
        (scenario_type, quarter, department, targeted_productivity, predicted_productivity, over_time, incentive, no_of_workers)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (scenario_type, quarter, department, float(target_prod), float(pred_prod), float(overtime), float(incentive), float(workers)))
                    conn.commit()
            return True, None
        except Exception as e:
            print(f"[PostgreSQL] Insert Error: {e}")
            return False, str(e)