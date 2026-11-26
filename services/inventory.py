from services.database import fetch_all, execute_query


def update_expired_food():

    # Automatically mark expired available/reserved food
    execute_query("""
        UPDATE food_listings
        SET status = 'Expired'
        WHERE expiry_time <= NOW()
          AND status IN ('Available', 'Reserved')
    """)


def get_expired_food():

    return fetch_all("""
        SELECT
            food_id,
            food_name,
            food_category,
            quantity,
            expiry_time,
            pickup_location
        FROM food_listings
        WHERE status = 'Expired'
        ORDER BY expiry_time DESC
    """)


def get_expiring_soon():

    return fetch_all("""
        SELECT
            food_id,
            food_name,
            food_category,
            quantity,
            expiry_time,
            pickup_location,
            TIMESTAMPDIFF(
                HOUR,
                NOW(),
                expiry_time
            ) AS hours_remaining
        FROM food_listings
        WHERE status = 'Available'
          AND expiry_time > NOW()
          AND expiry_time <= DATE_ADD(NOW(), INTERVAL 24 HOUR)
        ORDER BY expiry_time ASC
    """)


def get_available_inventory():

    return fetch_all("""
        SELECT
            food_id,
            food_name,
            food_category,
            quantity,
            expiry_time,
            pickup_location
        FROM food_listings
        WHERE status = 'Available'
          AND quantity > 0
          AND expiry_time > NOW()
        ORDER BY expiry_time ASC
    """)