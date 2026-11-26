import os
import joblib
import pandas as pd
import streamlit as st

from services.inventory import (
    update_expired_food,
    get_expired_food,
    get_expiring_soon,
    get_available_inventory
)

from services.database import fetch_all
from pages.donor_portal import show_donor_portal
from pages.ngo_portal import show_ngo_portal
from pages.ngo_dashboard import show_ngo_dashboard
from train_model import train


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="FoodBridge AI",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 FoodBridge AI")

st.caption(
    "AI-powered food demand prediction "
    "and surplus food allocation"
)


# ==================================================
# MODEL PATHS
# ==================================================

MODEL_PATH = "models/best_model.joblib"
METRICS_PATH = "models/model_metrics.csv"
DATA_PATH = "data/foodbridge_dataset.csv"


# ==================================================
# LOAD MACHINE LEARNING MODEL
# ==================================================

model = None

metrics = pd.DataFrame(
    columns=["Model", "MAE", "RMSE", "R2"]
)

dataset = pd.DataFrame()

try:

    if not os.path.exists(MODEL_PATH):

        with st.spinner("Training models for the first time..."):
            train()

    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)

    if os.path.exists(METRICS_PATH):
        metrics = pd.read_csv(METRICS_PATH)

    if os.path.exists(DATA_PATH):
        dataset = pd.read_csv(DATA_PATH)

except Exception as e:

    st.error(f"Model loading error: {e}")


# ==================================================
# SIDEBAR
# ==================================================

with st.sidebar:

    st.header("⚙️ Controls")

    if st.button(
        "🔄 Retrain Original Models",
        use_container_width=True
    ):

        try:

            with st.spinner("Training machine learning models..."):
                train()

            st.success("Models retrained successfully!")

            st.rerun()

        except Exception as e:

            st.error(f"Training error: {e}")

    st.markdown("---")

    st.write("**Dataset:** Simulated prototype data")

    st.write(f"**Dataset rows:** {len(dataset):,}")

    st.write("**Models compared:** 4")

    st.caption(
        "Experimental predictions require validation "
        "with real historical data."
    )


# ==================================================
# APPLICATION TABS
# ==================================================

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([

    "📊 Overview",

    "🔮 Demand Prediction",

    "🤝 Smart Allocation",

    "🧪 Model Lab",

    "🍱 Donor Portal",

    "🏥 NGO Portal",

    "🏢 NGO Dashboard"

])


# ==================================================
# TAB 1 - ADMIN OVERVIEW
# ==================================================

with tab1:

    st.header("📊 FoodBridge Admin Dashboard")

    st.caption("Live analytics powered by MySQL")

    # ------------------------------------------------
    # AUTOMATIC EXPIRY UPDATE
    # ------------------------------------------------

    try:

        update_expired_food()

    except Exception as e:

        st.warning(
            f"Automatic expiry update warning: {e}"
        )


    # ------------------------------------------------
    # DATABASE STATISTICS
    # ------------------------------------------------

    try:

        donation_stats_result = fetch_all("""
            SELECT
                COUNT(*) AS total_donations,
                COALESCE(SUM(quantity), 0) AS total_portions
            FROM food_listings
        """)

        ngo_stats_result = fetch_all("""
            SELECT COUNT(*) AS total_ngos
            FROM ngos
        """)

        allocation_stats_result = fetch_all("""
            SELECT
                COUNT(*) AS total_allocations,
                COALESCE(
                    SUM(allocated_quantity), 0
                ) AS total_allocated
            FROM allocations
            WHERE allocation_status != 'Cancelled'
        """)

        # Pending requests are optional
        try:

            pending_stats_result = fetch_all("""
                SELECT COUNT(*) AS pending
                FROM food_requests
                WHERE request_status = 'Pending'
            """)

            pending_count = (
                pending_stats_result[0]["pending"]
                if pending_stats_result
                else 0
            )

        except Exception:

            pending_count = 0


        donation_stats = (
            donation_stats_result[0]
            if donation_stats_result
            else {
                "total_donations": 0,
                "total_portions": 0
            }
        )

        ngo_stats = (
            ngo_stats_result[0]
            if ngo_stats_result
            else {
                "total_ngos": 0
            }
        )

        allocation_stats = (
            allocation_stats_result[0]
            if allocation_stats_result
            else {
                "total_allocations": 0,
                "total_allocated": 0
            }
        )


        # ------------------------------------------------
        # METRICS
        # ------------------------------------------------

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "🍱 Donations",
            donation_stats["total_donations"]
        )

        c2.metric(
            "📦 Portions Donated",
            donation_stats["total_portions"]
        )

        c3.metric(
            "🏥 Registered NGOs",
            ngo_stats["total_ngos"]
        )

        c4.metric(
            "🤝 Portions Allocated",
            allocation_stats["total_allocated"]
        )


        st.markdown("---")

        c5, c6 = st.columns(2)

        c5.metric(
            "📋 Allocation Records",
            allocation_stats["total_allocations"]
        )

        c6.metric(
            "⏳ Pending Requests",
            pending_count
        )


        # ------------------------------------------------
        # DONATION STATUS
        # ------------------------------------------------

        st.subheader("📦 Donation Status")

        status_data = fetch_all("""
            SELECT
                status,
                COUNT(*) AS count
            FROM food_listings
            GROUP BY status
        """)

        if status_data:

            status_df = pd.DataFrame(status_data)

            st.bar_chart(
                status_df.set_index("status")["count"]
            )

        else:

            st.info("No donation records available.")


        # ------------------------------------------------
        # NGO DEMAND ANALYSIS
        # ------------------------------------------------

        st.subheader("🏥 NGO Food Demand")

        demand_data = fetch_all("""
            SELECT
                n.ngo_name,
                SUM(d.required_quantity) AS required,
                SUM(
                    d.current_stock +
                    d.donations_received
                ) AS available
            FROM ngo_demand d
            JOIN ngos n
                ON d.ngo_id = n.ngo_id
            GROUP BY
                n.ngo_id,
                n.ngo_name
        """)

        if demand_data:

            demand_df = pd.DataFrame(demand_data)

            chart_df = demand_df.set_index(
                "ngo_name"
            )[["required", "available"]]

            st.bar_chart(chart_df)

            st.dataframe(
                demand_df,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "NGO demand has not been submitted yet."
            )


        # ------------------------------------------------
        # FOOD EXPIRING WITHIN 24 HOURS
        # ------------------------------------------------

        st.subheader(
            "⚠️ Food Expiring Within 24 Hours"
        )

        expiring_food = get_expiring_soon()

        if expiring_food:

            st.warning(
                f"{len(expiring_food)} food listing(s) "
                "need urgent distribution."
            )

            st.dataframe(
                pd.DataFrame(expiring_food),
                use_container_width=True,
                hide_index=True
            )

        else:

            st.success(
                "No available food is expiring "
                "within the next 24 hours."
            )


        # ------------------------------------------------
        # EXPIRED FOOD INVENTORY
        # ------------------------------------------------

        st.subheader("🚫 Expired Food Inventory")

        expired_food = get_expired_food()

        if expired_food:

            st.error(
                f"{len(expired_food)} expired food "
                "listing(s) cannot be distributed."
            )

            st.dataframe(
                pd.DataFrame(expired_food),
                use_container_width=True,
                hide_index=True
            )

        else:

            st.success("No expired food inventory.")


        # ------------------------------------------------
        # AVAILABLE FOOD INVENTORY
        # ------------------------------------------------

        st.subheader("📦 Available Food Inventory")

        available_food = get_available_inventory()

        if available_food:

            inventory_df = pd.DataFrame(
                available_food
            )

            total_available = int(
                inventory_df["quantity"].sum()
            )

            st.metric(
                "Total Available Portions",
                total_available
            )

            st.dataframe(
                inventory_df,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "No food currently available for allocation."
            )


        # ------------------------------------------------
        # RECENT DONATIONS
        # ------------------------------------------------

        st.subheader("🕒 Recent Donations")

        recent_donations = fetch_all("""
            SELECT
                food_name,
                food_category,
                quantity,
                pickup_location,
                status,
                created_at
            FROM food_listings
            ORDER BY food_id DESC
            LIMIT 10
        """)

        if recent_donations:

            st.dataframe(
                pd.DataFrame(recent_donations),
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info("No donations yet.")


    except Exception as e:

        st.error(
            f"Dashboard database error: {e}"
        )


# ==================================================
# TAB 2 - DEMAND PREDICTION
# ==================================================

with tab2:

    st.header("🧠 NGO Demand Prediction")

    st.write(
        "Predict tomorrow's food requirements "
        "using NGO information and machine learning."
    )

    from services.demand_prediction import (
        train_demand_model,
        predict_ngo_demand,
        get_shortage_status
    )


    # ------------------------------------------------
    # TRAIN DEMAND MODEL
    # ------------------------------------------------

    if st.button("🔄 Train / Retrain Demand Model"):

        try:

            with st.spinner(
                "Training machine learning models..."
            ):

                model_metrics, best_model = (
                    train_demand_model()
                )

            st.session_state.pop(
                "demand_predictions",
                None
                )

            st.success(
                f"Best model selected: {best_model}"
                )

            st.subheader("📊 Model Comparison")

            st.dataframe(
                model_metrics,
                use_container_width=True,
                hide_index=True
            )

        except Exception as e:

            st.error(
                f"Training error: {e}"
            )


    st.markdown("---")


    # ------------------------------------------------
    # PREDICT DEMAND
    # ------------------------------------------------

    if st.button(
        "🔮 Predict Tomorrow's NGO Demand"
    ):

        try:

            with st.spinner(
                "Predicting NGO demand..."
            ):

                predictions = predict_ngo_demand()

                if not predictions.empty:

                    predictions = get_shortage_status(
                        predictions
                    )

                    st.session_state[
                        "demand_predictions"
                    ] = predictions

                    st.success(
                        "Demand predictions generated successfully!"
                    )

                else:

                    st.warning(
                        "No NGO demand records found. "
                        "Register an NGO and submit demand first."
                    )

                    st.session_state.pop(
                        "demand_predictions",
                        None
                    )

        except Exception as e:

            st.error(
                f"Prediction error: {e}"
            )


    # ------------------------------------------------
    # DISPLAY PREDICTIONS
    # ------------------------------------------------

    predictions = st.session_state.get(
        "demand_predictions"
    )

    if predictions is not None and not predictions.empty:

        st.subheader(
            "📋 Predicted NGO Requirements"
        )

        display_columns = [
            "ngo_name",
            "food_category",
            "people_served",
            "required_quantity",
            "current_stock",
            "donations_received",
            "predicted_demand",
            "predicted_shortage",
            "Status"
        ]

        missing_columns = [
            column
            for column in display_columns
            if column not in predictions.columns
        ]

        if missing_columns:

            st.error(
                "Prediction output is missing columns: "
                + ", ".join(missing_columns)
            )

        else:

            st.dataframe(
                predictions[display_columns],
                use_container_width=True,
                hide_index=True
            )


            # Demand chart

            st.subheader(
                "📊 Predicted Demand by NGO"
            )

            chart = predictions.groupby(
                "ngo_name"
            )["predicted_demand"].sum()

            st.bar_chart(chart)


            # Shortage metrics

            st.subheader(
                "🚨 NGO Shortage Status"
            )

            critical_count = len(
                predictions[
                    predictions["Status"] == "Critical"
                ]
            )

            needs_food_count = len(
                predictions[
                    predictions["Status"] == "Needs Food"
                ]
            )

            sufficient_count = len(
                predictions[
                    predictions["Status"] == "Sufficient"
                ]
            )

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "🔴 Critical Shortage",
                critical_count
            )

            col2.metric(
                "🟠 Needs Food",
                needs_food_count
            )

            col3.metric(
                "🟢 Sufficient",
                sufficient_count
            )


            # Critical shortage table

            st.subheader(
                "🔴 Critical Shortage NGOs"
            )

            critical_data = predictions[
                predictions["Status"] == "Critical"
            ]

            if not critical_data.empty:

                st.dataframe(
                    critical_data[
                        [
                            "ngo_name",
                            "food_category",
                            "predicted_demand",
                            "predicted_shortage",
                            "Status"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.success(
                    "No critical shortages detected."
                )


            # NGOs needing food

            st.subheader(
                "🟠 NGOs Requiring Additional Food"
            )

            shortage_data = predictions[
                predictions["predicted_shortage"] > 0
            ]

            if not shortage_data.empty:

                st.dataframe(
                    shortage_data[
                        [
                            "ngo_name",
                            "food_category",
                            "predicted_demand",
                            "predicted_shortage",
                            "Status"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.success(
                    "No predicted food shortages."
                )


            st.info(
                "Prototype limitation: This model uses simulated "
                "training data. Predictions are experimental and "
                "require validation using real historical NGO demand."
            )


# ==================================================
# TAB 3 - SMART FOOD ALLOCATION
# ==================================================

with tab3:

    st.header("🤝 Smart Food Allocation")

    st.write(
        "Match available donations with NGO food shortages "
        "using predicted demand, beneficiary priority "
        "and food expiry urgency."
    )

    from services.allocation import generate_allocations
    from services.save_allocations import save_allocations


    # ------------------------------------------------
    # GENERATE RECOMMENDATIONS
    # ------------------------------------------------

    if st.button(
        "🔄 Generate Recommendations"
    ):

        try:

            with st.spinner(
                "Analyzing donations and NGO requirements..."
            ):

                predictions = st.session_state.get(
                    "demand_predictions"
                )

                result = generate_allocations(
                    predictions=predictions
                )

                st.session_state[
                    "allocation_result"
                ] = result


            if (
                predictions is not None
                and not predictions.empty
            ):

                st.success(
                    "AI-based allocation recommendations generated!"
                )

            else:

                st.success(
                    "Recommendations generated using "
                    "manually recorded demand."
                )

        except Exception as e:

            st.error(
                f"Allocation error: {e}"
            )

            st.session_state.pop(
                "allocation_result",
                None
            )


    # ------------------------------------------------
    # DISPLAY RECOMMENDATIONS
    # ------------------------------------------------

    result = st.session_state.get(
        "allocation_result"
    )

    if result is not None:

        if result.empty:

            st.warning(
                "No matching donations and NGO demands found. "
                "Check available donations, NGO demand records, "
                "food categories and preferences."
            )

        else:

            st.success(
                "Recommendations generated successfully!"
            )


            # Metrics

            total_portions = int(
                result["Recommended Portions"].sum()
            )

            total_ngos = result["NGO"].nunique()

            total_donations = result["Food ID"].nunique()

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "🍱 Portions Recommended",
                total_portions
            )

            c2.metric(
                "🏢 NGOs Matched",
                total_ngos
            )

            c3.metric(
                "📦 Donations Matched",
                total_donations
            )


            st.markdown("---")


            # Recommendations table

            st.subheader(
                "📋 Allocation Recommendations"
            )

            st.dataframe(
                result,
                use_container_width=True,
                hide_index=True
            )


            # Distribution chart

            st.subheader(
                "📊 Food Distribution by NGO"
            )

            distribution = result.groupby(
                "NGO"
            )["Recommended Portions"].sum()

            st.bar_chart(distribution)


            # Priority ranking

            st.subheader(
                "🏆 NGO Priority Ranking"
            )

            ranking = (
                result.groupby("NGO")["Priority Score"]
                .max()
                .sort_values(ascending=False)
                .reset_index()
            )

            ranking.columns = [
                "NGO",
                "Priority Score"
            ]

            st.dataframe(
                ranking,
                use_container_width=True,
                hide_index=True
            )


            # Explainable allocation

            st.subheader(
                "🧠 Why Was Food Allocated?"
            )

            for _, row in result.iterrows():

                with st.expander(
                    f"🍱 {row['Food']} → 🏢 {row['NGO']}"
                ):

                    st.write(
                        "**Recommended quantity:**",
                        row["Recommended Portions"],
                        "portions"
                    )

                    st.write(
                        "**AI predicted demand:**",
                        row.get(
                            "AI Predicted Demand",
                            "Not available"
                        )
                    )

                    st.write(
                        "**Current shortage:**",
                        row["Shortage"],
                        "portions"
                    )

                    st.write(
                        "**Demand source:**",
                        row.get(
                            "Demand Source",
                            "Manual Demand"
                        )
                    )

                    st.write(
                        "**Beneficiaries:**",
                        row["People Served"]
                    )

                    st.write(
                        "**Priority score:**",
                        row["Priority Score"]
                    )

                    st.write(
                        "**Expiry urgency:**",
                        row["Expiry (Hours)"],
                        "hours"
                    )

                    st.info(
                        row["Reason"]
                    )


            # Save recommendations

            st.markdown("---")

            st.subheader(
                "💾 Save Allocations"
            )

            st.warning(
                "Saving stores allocation recommendations. "
                "It does not confirm physical delivery."
            )

            if st.button(
                "💾 Save Recommendations to Database"
            ):

                try:

                    saved_count, skipped_count = (
                        save_allocations(result)
                    )

                    st.success(
                        f"New allocations saved: {saved_count}"
                    )

                    if skipped_count > 0:

                        st.warning(
                            f"Skipped {skipped_count} duplicate allocations."
                        )

                except Exception as e:

                    st.error(
                        f"Save error: {e}"
                    )


# ==================================================
# TAB 4 - MODEL LAB
# ==================================================

with tab4:

    st.header(
        "🧪 Machine Learning Model Lab"
    )

    st.write(
        "Four regression models were trained "
        "using an 80/20 train-test split."
    )

    st.write(
        "Lower MAE and RMSE are better. "
        "R² closer to 1 generally indicates better performance."
    )


    # Model comparison

    if metrics.empty:

        st.warning(
            "Model metrics are unavailable. "
            "Train the original models using the sidebar."
        )

    else:

        st.subheader(
            "📊 Model Performance Comparison"
        )

        if "MAE" in metrics.columns:

            st.dataframe(
                metrics.sort_values("MAE").round(3),
                use_container_width=True,
                hide_index=True
            )

        else:

            st.dataframe(
                metrics,
                use_container_width=True,
                hide_index=True
            )


        # Model chart

        st.subheader(
            "Model Comparison Chart"
        )

        chart_columns = [
            column
            for column in ["MAE", "RMSE"]
            if column in metrics.columns
        ]

        if (
            "Model" in metrics.columns
            and chart_columns
        ):

            st.bar_chart(
                metrics.set_index("Model")[chart_columns]
            )


    # Feature importance

    st.subheader(
        "🔍 Feature Importance"
    )

    try:

        if model is None:

            st.info(
                "Model artifact is unavailable."
            )

        elif hasattr(model, "named_steps"):

            estimator = model.named_steps.get(
                "model"
            )

            if (
                estimator is not None
                and hasattr(
                    estimator,
                    "feature_importances_"
                )
            ):

                prep = model.named_steps.get(
                    "prep"
                )

                names = (
                    prep.get_feature_names_out()
                    if prep is not None
                    else None
                )

                if names is not None:

                    importance = pd.Series(
                        estimator.feature_importances_,
                        index=names
                    ).sort_values(
                        ascending=False
                    ).head(12)

                    st.bar_chart(importance)

                else:

                    st.info(
                        "Feature names could not be extracted."
                    )

            else:

                st.info(
                    "The loaded model does not provide "
                    "tree-based feature importance."
                )

        else:

            st.info(
                "The loaded model is not a supported pipeline."
            )

    except Exception as e:

        st.info(
            f"Feature importance could not be displayed: {e}"
        )


    # Metric explanations

    st.markdown(
        "### Understanding Evaluation Metrics"
    )

    st.markdown("""
    - **MAE:** Average absolute prediction error.
    - **RMSE:** Penalizes large prediction errors more strongly.
    - **R²:** Measures how much target variation is explained by the model.
    """)


# ==================================================
# TAB 5 - DONOR PORTAL
# ==================================================

with tab5:

    show_donor_portal()


# ==================================================
# TAB 6 - NGO PORTAL
# ==================================================

with tab6:

    show_ngo_portal()


# ==================================================
# TAB 7 - NGO DASHBOARD
# ==================================================

with tab7:

    show_ngo_dashboard()