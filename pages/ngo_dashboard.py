
import streamlit as st
import pandas as pd

from services.database import fetch_all
from services.allocation_workflow import (
    approve_allocation,
    reject_allocation,
    mark_picked_up,
    mark_delivered
)


def show_ngo_dashboard():

    st.header("🏢 NGO Allocation Dashboard")

    st.write(
        "Review AI food allocation recommendations, "
        "approve food, track pickups and confirm deliveries."
    )

    ngos = fetch_all("""
        SELECT ngo_id, ngo_name, location, people_served
        FROM ngos
        ORDER BY ngo_name
    """)

    if not ngos:
        st.warning("No NGOs registered yet.")
        return

    ngo_names = [ngo["ngo_name"] for ngo in ngos]

    selected_name = st.selectbox("Select NGO", ngo_names)

    selected_ngo = next(
        ngo for ngo in ngos
        if ngo["ngo_name"] == selected_name
    )

    ngo_id = selected_ngo["ngo_id"]

    st.markdown("---")

    col1, col2 = st.columns(2)

    col1.metric(
        "👥 Beneficiaries",
        selected_ngo["people_served"]
    )

    col2.write(f"📍 {selected_ngo['location']}")

    allocations = fetch_all("""
        SELECT
            a.allocation_id,
            a.food_id,
            a.allocated_quantity,
            a.predicted_demand,
            a.priority_score,
            a.allocation_status,
            f.food_name,
            f.food_category,
            f.expiry_time,
            d.organization_name AS donor_name
        FROM allocations a
        JOIN food_listings f
            ON a.food_id = f.food_id
        JOIN donors d
            ON f.donor_id = d.donor_id
        WHERE a.ngo_id = %s
        ORDER BY a.allocation_id DESC
    """, (ngo_id,))

    if not allocations:
        st.info("No allocations available for this NGO.")
        return

    df = pd.DataFrame(allocations)

    # Metrics
    total = int(df["allocated_quantity"].sum())

    recommended = int(
        df.loc[
            df["allocation_status"] == "Recommended",
            "allocated_quantity"
        ].sum()
    )

    approved = int(
        df.loc[
            df["allocation_status"] == "Approved",
            "allocated_quantity"
        ].sum()
    )

    picked_up = int(
        df.loc[
            df["allocation_status"] == "Picked Up",
            "allocated_quantity"
        ].sum()
    )

    delivered = int(
        df.loc[
            df["allocation_status"] == "Delivered",
            "allocated_quantity"
        ].sum()
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Portions", total)
    c2.metric("Awaiting Approval", recommended)
    c3.metric("Picked Up", picked_up)
    c4.metric("Delivered", delivered)

    st.markdown("---")

    # NGO actions
    st.subheader("📬 Action Required")

    pending = df[
        df["allocation_status"] == "Recommended"
    ]

    if pending.empty:
        st.success("No pending recommendations.")
    else:

        for _, row in pending.iterrows():

            with st.expander(
                f"🍱 {row['food_name']} — "
                f"{row['allocated_quantity']} portions"
            ):

                st.write("**Donor:**", row["donor_name"])
                st.write("**Category:**", row["food_category"])
                st.write("**Quantity:**", row["allocated_quantity"])
                st.write("**Priority score:**", row["priority_score"])
                st.write("**Predicted demand:**", row["predicted_demand"])
                st.write("**Expiry:**", row["expiry_time"])

                col1, col2 = st.columns(2)

                if col1.button(
                    "✅ Approve",
                    key=f"approve_{row['allocation_id']}"
                ):

                    success, message = approve_allocation(
                        int(row["allocation_id"])
                    )

                    if success:
                        st.success(message)
                    else:
                        st.error(message)

                    st.rerun()

                if col2.button(
                    "❌ Reject",
                    key=f"reject_{row['allocation_id']}"
                ):

                    success, message = reject_allocation(
                        int(row["allocation_id"])
                    )

                    if success:
                        st.success(message)
                    else:
                        st.error(message)

                    st.rerun()

    st.markdown("---")

    # Pickup management
    st.subheader("🚚 Pickup Management")

    approved_rows = df[
        df["allocation_status"] == "Approved"
    ]

    if approved_rows.empty:

        st.info("No approved allocations waiting for pickup.")

    else:

        for _, row in approved_rows.iterrows():

            col1, col2 = st.columns([3, 1])

            col1.write(
                f"**{row['food_name']}** — "
                f"{row['allocated_quantity']} portions"
            )

            if col2.button(
                "Mark Picked Up",
                key=f"pickup_{row['allocation_id']}"
            ):

                success, message = mark_picked_up(
                    int(row["allocation_id"])
                )

                if success:
                    st.success(message)
                else:
                    st.error(message)

                st.rerun()

    st.markdown("---")

    # Delivery management
    st.subheader("📦 Delivery Confirmation")

    pickup_rows = df[
        df["allocation_status"] == "Picked Up"
    ]

    if pickup_rows.empty:

        st.info("No pickups awaiting delivery confirmation.")

    else:

        for _, row in pickup_rows.iterrows():

            col1, col2 = st.columns([3, 1])

            col1.write(
                f"**{row['food_name']}** — "
                f"{row['allocated_quantity']} portions"
            )

            if col2.button(
                "Confirm Delivered",
                key=f"delivered_{row['allocation_id']}"
            ):

                success, message = mark_delivered(
                    int(row["allocation_id"])
                )

                if success:
                    st.success(message)
                else:
                    st.error(message)

                st.rerun()

    st.markdown("---")

    # History
    st.subheader("📋 Complete Allocation History")

    display_df = df.rename(columns={
        "food_name": "Food",
        "food_category": "Category",
        "donor_name": "Donor",
        "allocated_quantity": "Portions",
        "allocation_status": "Status",
        "priority_score": "Priority Score",
        "predicted_demand": "Predicted Demand"
    })

    st.dataframe(
        display_df[
            [
                "Food",
                "Category",
                "Donor",
                "Portions",
                "Status",
                "Priority Score",
                "Predicted Demand"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

    st.subheader("📊 Distribution Summary")

    st.bar_chart(
        df.groupby("food_name")["allocated_quantity"].sum()
    )

    st.subheader("Allocation Status")

    st.bar_chart(df["allocation_status"].value_counts())
