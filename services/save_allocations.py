import pandas as pd
from services.database import execute_query, fetch_one


def save_allocations(df):

    if df is None or df.empty:
        return 0, 0

    saved_count = 0
    skipped_count = 0

    for _, row in df.iterrows():

        food_id = int(row["Food ID"])
        ngo_id = int(row["NGO ID"])
        quantity = int(row["Recommended Portions"])

        # Basic validation
        if quantity <= 0:
            skipped_count += 1
            continue

        # Prevent duplicate allocation records
        existing = fetch_one("""
            SELECT allocation_id
            FROM allocations
            WHERE food_id = %s
              AND ngo_id = %s
        """, (food_id, ngo_id))

        if existing:
            skipped_count += 1
            continue

        # Save recommendation
        execute_query("""
            INSERT INTO allocations
            (
                food_id,
                ngo_id,
                allocated_quantity,
                predicted_demand,
                priority_score,
                allocation_status
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            food_id,
            ngo_id,
            quantity,
            int(row["Shortage"]),
            float(row["Priority Score"]),
            "Recommended"
        ))

        saved_count += 1

    return saved_count, skipped_count