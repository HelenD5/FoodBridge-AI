import streamlit as st
from datetime import date, time, datetime
from services.database import execute_query


def show_donor_portal():

    st.title("🍱 Food Donor Portal")
    st.write("Donate surplus food and help NGOs reduce food waste.")

    st.markdown("---")

    with st.form("donation_form"):

        st.subheader("🏢 Donor Information")

        organization = st.text_input("Organization Name")
        location = st.text_input("Organization Location")

        st.subheader("🍛 Food Information")

        food_name = st.text_input("Food Name")

        category = st.selectbox(
            "Food Category",
            ["Rice", "Vegetables", "Fruits", "Bread", "Meals", "Other"]
        )

        quantity = st.number_input(
            "Quantity (portions)",
            min_value=1,
            value=50
        )

        prepared_date = st.date_input(
            "Prepared Date",
            value=date.today()
        )

        prepared_time = st.time_input(
            "Prepared Time",
            value=time(12, 0)
        )

        expiry_date = st.date_input(
            "Expiry Date",
            value=date.today()
        )

        expiry_time = st.time_input(
            "Expiry Time",
            value=time(18, 0)
        )

        pickup_location = st.text_input("Pickup Address")

        submitted = st.form_submit_button(
            "🚀 Submit Food Donation",
            use_container_width=True
        )

        if submitted:

            if not organization or not food_name or not pickup_location:
                st.warning("Please fill all required fields.")

            else:

                prepared_at = datetime.combine(
                    prepared_date, prepared_time
                )

                expires_at = datetime.combine(
                    expiry_date, expiry_time
                )

                if expires_at <= prepared_at:

                    st.error("Expiry must be after preparation time.")

                else:

                    try:

                        user_id = execute_query(
                            "INSERT INTO users (name, role) VALUES (%s, %s)",
                            (organization, "donor")
                        )

                        donor_id = execute_query(
                            """INSERT INTO donors
                            (user_id, organization_name, location)
                            VALUES (%s, %s, %s)""",
                            (user_id, organization, location)
                        )

                        execute_query(
                            """INSERT INTO food_listings
                            (donor_id, food_name, food_category, quantity,
                            prepared_at, expiry_time, pickup_location)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                            (
                                donor_id,
                                food_name,
                                category,
                                quantity,
                                prepared_at,
                                expires_at,
                                pickup_location
                            )
                        )

                        st.success("Donation successfully registered! 🎉")
                        st.balloons()

                    except Exception as e:

                        st.error(f"Database Error: {e}")

    st.markdown("---")
    st.subheader("📦 Existing Food Donations")

    try:

        from services.database import fetch_all

        donations = fetch_all(
            """SELECT food_name, food_category, quantity,
            expiry_time, pickup_location, status
            FROM food_listings
            ORDER BY food_id DESC"""
        )

        if donations:
            st.dataframe(donations, use_container_width=True)
        else:
            st.info("No donations registered yet.")

    except Exception as e:
        st.error(f"Could not load donations: {e}")
