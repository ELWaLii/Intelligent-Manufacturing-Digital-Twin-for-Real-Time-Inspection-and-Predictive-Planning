import pandas as pd
from db_connection import get_connection

def insert_production_from_csv(file_path):

    df = pd.read_csv(file_path)

    df = df.astype(object)
    df = df.where(pd.notnull(df), None)

    conn = get_connection()
    cur = conn.cursor()

    records = df[[
        "quarter",
        "department",
        "day",
        "team",
        "targeted_productivity",
        "smv",
        "over_time",
        "incentive",
        "idle_time",
        "idle_men",
        "no_of_style_change",
        "no_of_workers",
        "actual_productivity",
        "year",
        "month",
        "day_of_month",
        "week_of_year",
        "productivity_diff",
        "over_time_per_worker",
        "incentive_per_worker",
        "idle_impact",
        "idle_ratio"
        ]].values.tolist()

    cur.executemany("""
        INSERT INTO production_transformed
        (
            quarter,
            department,
            day,
            team,
            targeted_productivity,
            smv,
            over_time,
            incentive,
            idle_time,
            idle_men,
            no_of_style_change,
            no_of_workers,
            actual_productivity,
            year,
            month,
            day_of_month,
            week_of_year,
            productivity_diff,
            over_time_per_worker,
            incentive_per_worker,
            idle_impact,
            idle_ratio
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, records)

    conn.commit()
    print(cur.rowcount)
    cur.close()
    conn.close()

    print("✅ Data inserted successfully!")