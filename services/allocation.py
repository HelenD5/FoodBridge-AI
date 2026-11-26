
import pandas as pd
from datetime import datetime
from services.database import fetch_all


def generate_allocations(predictions=None):

    # ==========================================
    # 1. FETCH AVAILABLE DONATIONS
    # ==========================================

    donations = fetch_all("""
        SELECT
            f.food_id,
            f.food_name,
            f.food_category,
            f.quantity,
            f.expiry_time,
            f.pickup_location,
            d.organization_name AS donor_name
        FROM food_listings f
        JOIN donors d
            ON f.donor_id = d.donor_id
        WHERE f.status = 'Available'
          AND f.quantity > 0
          AND f.expiry_time > NOW()
        ORDER BY f.expiry_time ASC
    """)

    # ==========================================
    # 2. FETCH LATEST NGO DEMAND
    # ==========================================

    demands = fetch_all("""
        SELECT nd.*
        FROM ngo_demand nd
        INNER JOIN (
            SELECT
                ngo_id,
                food_category,
                MAX(demand_date) AS latest_date
            FROM ngo_demand
            GROUP BY ngo_id, food_category
        ) latest
        ON nd.ngo_id = latest.ngo_id
        AND nd.food_category = latest.food_category
        AND nd.demand_date = latest.latest_date
    """)

    # ==========================================
    # 3. FETCH NGO INFORMATION
    # ==========================================

    ngos = fetch_all("""
        SELECT
            ngo_id,
            ngo_name,
            location,
            people_served,
            food_preferences,
            storage_capacity
        FROM ngos
    """)

    if not donations or not demands or not ngos:
        return pd.DataFrame()

    ngo_map = {
        ngo["ngo_id"]: ngo
        for ngo in ngos
    }

    # ==========================================
    # 4. PREPARE AI PREDICTIONS
    # ==========================================

    prediction_map = {}

    if predictions is not None and not predictions.empty:

        for _, row in predictions.iterrows():

            key = (
                int(row["ngo_id"]),
                str(row["food_category"]).strip().lower()
            )

            prediction_map[key] = {
                "predicted_demand": max(
                    0,
                    float(row["predicted_demand"])
                ),
                "predicted_shortage": max(
                    0,
                    float(row["predicted_shortage"])
                )
            }

    # ==========================================
    # 5. CALCULATE NGO SHORTAGES
    # ==========================================

    shortages = {}
    demand_info = {}

    for demand in demands:

        ngo = ngo_map.get(demand["ngo_id"])

        if ngo is None:
            continue

        category = str(
            demand["food_category"]
        ).strip().lower()

        key = (
            demand["ngo_id"],
            category
        )

        # Manual shortage calculation
        manual_shortage = max(
            0,
            float(demand["required_quantity"])
            - float(demand["current_stock"] or 0)
            - float(demand["donations_received"] or 0)
        )

        # Use AI prediction when available
        if key in prediction_map:

            predicted_shortage = prediction_map[key][
                "predicted_shortage"
            ]

            predicted_demand = prediction_map[key][
                "predicted_demand"
            ]

            shortage = predicted_shortage

            demand_source = "AI Prediction"

        else:

            shortage = manual_shortage

            predicted_demand = float(
                demand["required_quantity"]
            )

            demand_source = "Manual Demand"

        shortages[key] = max(
            0,
            float(shortage)
        )

        demand_info[key] = {
            "predicted_demand": predicted_demand,
            "demand_source": demand_source,
            "required_quantity": float(
                demand["required_quantity"]
            )
        }

    # ==========================================
    # 6. GENERATE ALLOCATION RECOMMENDATIONS
    # ==========================================

    recommendations = []

    for food in donations:

        # Available quantity of this food
        food_remaining = max(
            0,
            float(food["quantity"])
        )

        category = str(
            food["food_category"]
        ).strip().lower()

        candidates = []

        # ======================================
        # FIND ELIGIBLE NGOS
        # ======================================

        for demand in demands:

            ngo = ngo_map.get(demand["ngo_id"])

            if ngo is None:
                continue

            demand_category = str(
                demand["food_category"]
            ).strip().lower()

            # Food category must match
            if demand_category != category:
                continue

            key = (
                ngo["ngo_id"],
                category
            )

            shortage = shortages.get(
                key,
                0
            )

            # NGO must have a shortage
            if shortage <= 0:
                continue

            # ==================================
            # FOOD PREFERENCE CHECK
            # ==================================

            preferences = ngo.get(
                "food_preferences"
            ) or ""

            preferences = str(
                preferences
            ).strip().lower()

            if preferences:

                preference_list = [
                    p.strip()
                    for p in preferences.split(",")
                ]

                if (
                    category not in preference_list
                    and "all" not in preference_list
                ):
                    continue

            # ==================================
            # BENEFICIARY PRIORITY
            # ==================================

            people = max(
                1,
                int(ngo["people_served"] or 1)
            )

            beneficiary_score = min(
                people / 500,
                1
            )

            # ==================================
            # EXPIRY URGENCY
            # ==================================

            expiry = food["expiry_time"]

            if expiry:

                # Convert string to datetime if necessary
                if isinstance(expiry, str):

                    expiry = datetime.fromisoformat(
                        expiry.replace("Z", "")
                    )

                hours_left = (
                    expiry - datetime.now()
                ).total_seconds() / 3600

                # Ignore expired food
                if hours_left <= 0:
                    continue

            else:

                hours_left = 24

            # Higher urgency when expiry is closer
            urgency_score = 1 / max(
                hours_left,
                1
            )

            urgency_score = min(
                urgency_score,
                1
            )

            # ==================================
            # SHORTAGE SEVERITY
            # ==================================

            predicted_demand = demand_info[key][
                "predicted_demand"
            ]

            shortage_ratio = min(
                shortage / max(
                    predicted_demand,
                    1
                ),
                1
            )

            # ==================================
            # FINAL PRIORITY SCORE
            # ==================================

            priority_score = (
                shortage_ratio * 0.50
                + beneficiary_score * 0.20
                + urgency_score * 0.30
            )

            candidates.append({

                "ngo_id": ngo["ngo_id"],
                "ngo_name": ngo["ngo_name"],
                "location": ngo["location"],
                "people_served": people,
                "shortage": shortage,
                "predicted_demand": predicted_demand,
                "demand_source": demand_info[key][
                    "demand_source"
                ],
                "priority_score": priority_score,
                "hours_to_expiry": hours_left

            })

        # ==========================================
        # 7. SORT NGOS BY PRIORITY
        # ==========================================

        candidates.sort(
            key=lambda x: x["priority_score"],
            reverse=True
        )

        # ==========================================
        # 8. DISTRIBUTE FOOD
        # ==========================================

        for ngo in candidates:

            if food_remaining <= 0:
                break

            key = (
                ngo["ngo_id"],
                category
            )

            shortage = shortages.get(
                key,
                0
            )

            # Never allocate more than:
            # 1. Available food
            # 2. NGO's remaining shortage

            allocated = min(
                food_remaining,
                shortage
            )

            if allocated <= 0:
                continue

            # ==================================
            # EXPLAINABLE ALLOCATION
            # ==================================

            reason = (
                f"{ngo['people_served']} beneficiaries; "
                f"{shortage:.0f} portions shortage; "
                f"{ngo['demand_source']}; "
                f"food expires in "
                f"{ngo['hours_to_expiry']:.1f} hours"
            )

            recommendations.append({

                "Food ID": food["food_id"],
                "NGO ID": ngo["ngo_id"],
                "Food": food["food_name"],
                "Category": food["food_category"],
                "Donor": food["donor_name"],
                "Available Portions": food["quantity"],
                "NGO": ngo["ngo_name"],
                "NGO Location": ngo["location"],
                "People Served": ngo["people_served"],
                "Shortage": round(
                    ngo["shortage"],
                    2
                ),
                "AI Predicted Demand": round(
                    ngo["predicted_demand"],
                    2
                ),
                "Demand Source": ngo["demand_source"],
                "Recommended Portions": allocated,
                "Priority Score": round(
                    ngo["priority_score"],
                    3
                ),
                "Expiry (Hours)": round(
                    ngo["hours_to_expiry"],
                    1
                ),
                "Reason": reason

            })

            # ==================================
            # UPDATE REMAINING FOOD
            # ==================================

            food_remaining -= allocated

            # ==================================
            # UPDATE REMAINING NGO SHORTAGE
            # ==================================

            shortages[key] -= allocated

    # ==========================================
    # 9. RETURN RECOMMENDATIONS
    # ==========================================

    return pd.DataFrame(recommendations)
