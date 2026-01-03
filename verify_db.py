"""Simple verification script for MedEquip MySQL database.

Runs basic connectivity checks, auth lookup, and sample queries
across key tables. Exits with non-zero status on failure.
"""

from database import execute_query, get_client_by_credentials


def check_clients() -> None:
    print("[check_clients] Fetching up to 5 clients...")
    rows = execute_query("SELECT client_id, name, email FROM clients LIMIT 5")
    print(f"  -> Retrieved {len(rows)} client rows")
    if not rows:
        raise SystemExit("No clients found; expected seeded sample data.")


def check_auth() -> None:
    print("[check_auth] Verifying demo client credentials...")
    client = get_client_by_credentials("gregory45@snyder.net", "ME-10001")
    if client is None:
        raise SystemExit(
            "Demo client auth failed: expected ME-10001 / contact@cityhospital.com to exist."
        )
    print(f"  -> Auth OK for client_id={client.client_id}, name={client.name}")


def check_orders_and_shipments() -> None:
    print("[check_orders_and_shipments] Fetching orders and shipments...")
    orders = execute_query("SELECT order_id, client_id, status FROM orders LIMIT 5")
    print(f"  -> Retrieved {len(orders)} order rows")

    shipments = execute_query(
        "SELECT shipment_id, order_id, delivery_status FROM shipments LIMIT 5"
    )
    print(f"  -> Retrieved {len(shipments)} shipment rows")


def check_warranties_and_tickets() -> None:
    print("[check_warranties_and_tickets] Fetching warranties and tickets...")
    warranties = execute_query(
        "SELECT warranty_id, serial_number, coverage_level FROM warranties LIMIT 5"
    )
    print(f"  -> Retrieved {len(warranties)} warranty rows")

    tickets = execute_query(
        "SELECT ticket_id, client_id, status, category FROM support_tickets LIMIT 5"
    )
    print(f"  -> Retrieved {len(tickets)} support ticket rows")


def check_invoices_payments_parts() -> None:
    print("[check_invoices_payments_parts] Fetching invoices, payments, and parts...")
    invoices = execute_query(
        "SELECT invoice_id, client_id, status, amount FROM invoices LIMIT 5"
    )
    print(f"  -> Retrieved {len(invoices)} invoice rows")

    payments = execute_query(
        "SELECT payment_id, invoice_id, status, amount FROM payments LIMIT 5"
    )
    print(f"  -> Retrieved {len(payments)} payment rows")

    parts = execute_query(
        "SELECT part_number, name, stock_quantity, unit_price FROM parts_catalog LIMIT 5"
    )
    print(f"  -> Retrieved {len(parts)} part rows")


def main() -> None:
    print("=== MedEquip DB verification ===")
    check_clients()
    check_auth()
    check_orders_and_shipments()
    check_warranties_and_tickets()
    check_invoices_payments_parts()
    print("\nAll DB verification checks passed.")


if __name__ == "__main__":
    main()
