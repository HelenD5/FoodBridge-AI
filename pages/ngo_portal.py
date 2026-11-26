
import streamlit as st
from services.database import execute_query, fetch_all


def show_ngo_portal():

    st.title("🏥 NGO Portal")
    st.write("Register your NGO and submit daily food requirements.")

    st.markdown("---")

    # ---------------- NGO REGISTRATION ----------------
    st.header("🏢 NGO Registration")

    with st.form("ngo_registration"):

        ngo_name = st.text_input("NGO Name")
        ngo_type = st.selectbox(
            "NGO Type",
            ["Orphanage", "Old Age Home", "Shelter", "Community Center", "Other"]
        )

        people_served = st.number_input(
            "People Served Daily", min_value=1, value=100
        )

        storage_capacity = st.number_input(
            "Food Storage Capacity (portions)",
            min_value=0,
            value=200
        )

        location = st.text_input("NGO Location")
        preferences = st.multiselect(
            "Food Preferences",
            ["Rice", "Vegetables", "Fruits", "Bread", "Meals"]
        )

        register = st.form_submit_button("Register NGO")

        if register:

            if not ngo_name or not location:
                st.warning("Please fill NGO name and location.")

            else:
                try:
                    user_id = execute_query(
                        "INSERT INTO users (name, role) VALUES (%s, %s)",
                        (ngo_name, "ngo")
                    )

                    ngo_id = execute_query(
                        """INSERT INTO ngos
                        (user_id, ngo_name, ngo_type, people_served,
                         storage_capacity, location, food_preferences)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (
                            user_id,
                            ngo_name,
                            ngo_type,
                            people_served,
                            storage_capacity,
                            location,
                            ", ".join(preferences)
                        )
                    )

                    st.success(f"NGO registered successfully! NGO ID: {ngo_id}")

                except Exception as e:
                    st.error(f"Database Error: {e}")

    st.markdown("---")

    # ---------------- DAILY DEMAND ----------------
    st.header("🍱 Submit Daily Food Demand")

    try:
        ngos = fetch_all(
            "SELECT ngo_id, ngo_name FROM ngos ORDER BY ngo_id"
        )

        if not ngos:
            st.warning("Register an NGO first.")
            return

        ngo_options = {
            f"{ngo['ngo_name']} (ID: {ngo['ngo_id']})": ngo["ngo_id"]
            for ngo in ngos
        }

        with st.form("demand_form"):

            selected_ngo = st.selectbox(
                "Select NGO",
                list(ngo_options.keys())
            )

            demand_date = st.date_input("Demand Date")

            food_category = st.selectbox(
                "Food Category",
                ["Rice", "Vegetables", "Fruits", "Bread", "Meals", "Other"]
            )

            required_quantity = st.number_input(
                "Required Food Quantity (portions)",
                min_value=1,
                value=100
            )

            current_stock = st.number_input(
                "Current Stock Available",
                min_value=0,
                value=0
            )

            donations_received = st.number_input(
                "Donations Already Received",
                min_value=0,
                value=0
            )

            people = st.number_input(
                "People to Feed",
                min_value=1,
                value=100
            )

            submit_demand = st.form_submit_button("Submit Food Demand")

            if submit_demand:

                ngo_id = ngo_options[selected_ngo]

                try:
                    execute_query(
                        """INSERT INTO ngo_demand
                        (ngo_id, demand_date, food_category,
                         required_quantity, current_stock,
                         donations_received, people_served)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (
                            ngo_id,
                            demand_date,
                            food_category,
                            required_quantity,
                            current_stock,
                            donations_received,
                            people
                        )
                    )

                    st.success("Daily food demand submitted successfully! 🎉")

                except Exception as e:
                    st.error(f"Database Error: {e}")

    except Exception as e:
        st.error(f"Could not load NGOs: {e}")

    st.markdown("---")

    # ---------------- REGISTERED NGOS ----------------
    st.header("📋 Registered NGOs")

    try:
        ngo_data = fetch_all(
            """SELECT ngo_id, ngo_name, ngo_type,
            people_served, storage_capacity, location,
            food_preferences
            FROM ngos ORDER BY ngo_id DESC"""
        )

        if ngo_data:
            st.dataframe(ngo_data, use_container_width=True)
        else:
            st.info("No NGOs registered yet.")

    except Exception as e:
        st.error(f"Error loading NGO data: {e}")

    # ---------------- DEMAND RECORDS ----------------
    st.header("📊 Submitted Demand Records")

    try:
        demand_data = fetch_all(
            """SELECT d.demand_id, n.ngo_name, d.demand_date,
            d.food_category, d.required_quantity,
            d.current_stock, d.donations_received,
            d.people_served
            FROM ngo_demand d
            JOIN ngos n ON d.ngo_id = n.ngo_id
            ORDER BY d.demand_id DESC"""
        )

        if demand_data:
            st.dataframe(demand_data, use_container_width=True)
        else:
            st.info("No demand records submitted yet.")

    except Exception as e:
        st.error(f"Error loading demand records: {e}")
