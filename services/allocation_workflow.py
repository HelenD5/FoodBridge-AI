
from services.database import get_connection


def approve_allocation(allocation_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        cursor.execute("""
            SELECT allocation_id, food_id, allocated_quantity,
                   allocation_status
            FROM allocations
            WHERE allocation_id = %s
            FOR UPDATE
        """, (allocation_id,))

        allocation = cursor.fetchone()

        if not allocation:
            raise Exception("Allocation not found.")

        if allocation["allocation_status"] != "Recommended":
            raise Exception("Only recommended allocations can be approved.")

        cursor.execute("""
            SELECT food_id, quantity, status
            FROM food_listings
            WHERE food_id = %s
            FOR UPDATE
        """, (allocation["food_id"],))

        food = cursor.fetchone()

        if not food:
            raise Exception("Food donation not found.")

        if food["status"] not in ("Available", "Reserved"):
            raise Exception("Food is no longer available.")

        allocated_quantity = int(allocation["allocated_quantity"])
        available_quantity = int(food["quantity"])

        if allocated_quantity > available_quantity:
            raise Exception(
                f"Insufficient stock. Available: {available_quantity}"
            )

        remaining_quantity = available_quantity - allocated_quantity

        new_food_status = (
            "Reserved" if remaining_quantity == 0 else "Available"
        )

        cursor.execute("""
            UPDATE food_listings
            SET quantity = %s,
                status = %s
            WHERE food_id = %s
        """, (
            remaining_quantity,
            new_food_status,
            food["food_id"]
        ))

        cursor.execute("""
            UPDATE allocations
            SET allocation_status = 'Approved'
            WHERE allocation_id = %s
        """, (allocation_id,))

        conn.commit()

        return True, "Allocation approved successfully!"

    except Exception as e:
        conn.rollback()
        return False, str(e)

    finally:
        cursor.close()
        conn.close()


def reject_allocation(allocation_id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE allocations
            SET allocation_status = 'Rejected'
            WHERE allocation_id = %s
              AND allocation_status = 'Recommended'
        """, (allocation_id,))

        conn.commit()

        if cursor.rowcount == 0:
            return False, "Allocation cannot be rejected."

        return True, "Allocation rejected."

    except Exception as e:
        conn.rollback()
        return False, str(e)

    finally:
        cursor.close()
        conn.close()


def mark_picked_up(allocation_id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE allocations
            SET allocation_status = 'Picked Up'
            WHERE allocation_id = %s
              AND allocation_status = 'Approved'
        """, (allocation_id,))

        conn.commit()

        if cursor.rowcount == 0:
            return False, "Only approved allocations can be picked up."

        return True, "Food marked as picked up!"

    except Exception as e:
        conn.rollback()
        return False, str(e)

    finally:
        cursor.close()
        conn.close()


def mark_delivered(allocation_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        cursor.execute("""
            SELECT allocation_id, food_id, allocation_status
            FROM allocations
            WHERE allocation_id = %s
            FOR UPDATE
        """, (allocation_id,))

        allocation = cursor.fetchone()

        if not allocation:
            raise Exception("Allocation not found.")

        if allocation["allocation_status"] != "Picked Up":
            raise Exception("Mark as picked up before delivery.")

        cursor.execute("""
            UPDATE allocations
            SET allocation_status = 'Delivered'
            WHERE allocation_id = %s
        """, (allocation_id,))

        cursor.execute("""
            SELECT quantity
            FROM food_listings
            WHERE food_id = %s
            FOR UPDATE
        """, (allocation["food_id"],))

        food = cursor.fetchone()

        if food and int(food["quantity"]) == 0:
            cursor.execute("""
                UPDATE food_listings
                SET status = 'Distributed'
                WHERE food_id = %s
            """, (allocation["food_id"],))

        conn.commit()

        return True, "Delivery completed successfully!"

    except Exception as e:
        conn.rollback()
        return False, str(e)

    finally:
        cursor.close()
        conn.close()
