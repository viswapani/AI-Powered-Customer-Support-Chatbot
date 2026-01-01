"""MySQL database setup and helper utilities for MedEquip chatbot.

This module defines the MedEquip customer support schema in a MySQL
database and provides helper functions for executing queries and
seeding synthetic data for development and testing.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

import mysql.connector
from mysql.connector import MySQLConnection

from faker import Faker

from config import (
    DB_BACKEND,
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DB,
)

faker = Faker()


def ensure_mysql_database_exists() -> None:
    """Create the MySQL database if it does not already exist.

    Connects without specifying a database, then issues
    CREATE DATABASE IF NOT EXISTS using the configured name.
    """

    if DB_BACKEND != "mysql":
        return

    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
    )
    try:
        cur = conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
    finally:
        conn.close()


@dataclass
class Client:
    client_id: str
    name: str
    email: str
    client_type: str
    city: str
    country: str


@contextmanager
def get_connection() -> MySQLConnection:
    """Context manager yielding a MySQL connection.

    Commits on success and rolls back on error.
    """

    if DB_BACKEND != "mysql":
        raise RuntimeError(f"Expected DB_BACKEND 'mysql', got {DB_BACKEND!r}")

    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_database() -> None:
    """Create all MedEquip tables if they do not exist.

    The schema is simplified but aligned with the project specification
    and supports the 9 primary intents (orders, warranties, tickets,
    invoices, parts, etc.).
    """

    with get_connection() as conn:
        cur = conn.cursor()

        # 1. clients
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INT AUTO_INCREMENT PRIMARY KEY,
                client_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                client_type TEXT NOT NULL,
                city TEXT,
                country TEXT
            );
            """
        )

        # 2. products
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sku TEXT UNIQUE NOT NULL,
                model TEXT NOT NULL,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                power_requirements TEXT,
                specifications TEXT
            );
            """
        )

        # 3. equipment_registry
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS equipment_registry (
                id INT AUTO_INCREMENT PRIMARY KEY,
                serial_number TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                install_date TEXT,
                status TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(client_id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            """
        )

        # 4. orders
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                order_date TEXT,
                status TEXT,
                total_amount REAL,
                FOREIGN KEY (client_id) REFERENCES clients(client_id)
            );
            """
        )

        # 5. order_items
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS order_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(order_id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            """
        )

        # 6. shipments
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS shipments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                shipment_id TEXT UNIQUE NOT NULL,
                order_id TEXT NOT NULL,
                carrier TEXT,
                tracking_number TEXT,
                shipped_date TEXT,
                expected_delivery_date TEXT,
                delivery_status TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            );
            """
        )

        # 7. service_regions
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS service_regions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                region_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                country TEXT NOT NULL
            );
            """
        )

        # 8. technicians
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS technicians (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tech_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                region_code TEXT NOT NULL,
                phone TEXT,
                FOREIGN KEY (region_code) REFERENCES service_regions(region_code)
            );
            """
        )

        # 9. service_appointments
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS service_appointments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                appointment_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                serial_number TEXT,
                tech_id TEXT,
                scheduled_date TEXT,
                priority TEXT,
                status TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(client_id),
                FOREIGN KEY (serial_number) REFERENCES equipment_registry(serial_number),
                FOREIGN KEY (tech_id) REFERENCES technicians(tech_id)
            );
            """
        )

        # 10. warranties
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS warranties (
                id INT AUTO_INCREMENT PRIMARY KEY,
                warranty_id TEXT UNIQUE NOT NULL,
                serial_number TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                coverage_level TEXT,
                FOREIGN KEY (serial_number) REFERENCES equipment_registry(serial_number)
            );
            """
        )

        # 11. amc_contracts
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS amc_contracts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                amc_id TEXT UNIQUE NOT NULL,
                serial_number TEXT NOT NULL,
                tier TEXT,
                start_date TEXT,
                end_date TEXT,
                FOREIGN KEY (serial_number) REFERENCES equipment_registry(serial_number)
            );
            """
        )

        # 12. coverage_claims
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS coverage_claims (
                id INT AUTO_INCREMENT PRIMARY KEY,
                claim_id TEXT UNIQUE NOT NULL,
                serial_number TEXT NOT NULL,
                claim_date TEXT,
                status TEXT,
                description TEXT,
                FOREIGN KEY (serial_number) REFERENCES equipment_registry(serial_number)
            );
            """
        )

        # 13. support_tickets
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticket_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                serial_number TEXT,
                category TEXT,
                severity TEXT,
                status TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(client_id)
            );
            """
        )

        # 14. ticket_history
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ticket_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticket_id TEXT NOT NULL,
                event_time TEXT,
                status TEXT,
                notes TEXT,
                FOREIGN KEY (ticket_id) REFERENCES support_tickets(ticket_id)
            );
            """
        )

        # 15. invoices
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                invoice_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                order_id TEXT,
                amount REAL,
                issue_date TEXT,
                due_date TEXT,
                status TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(client_id),
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            );
            """
        )

        # 16. payments
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                payment_id TEXT UNIQUE NOT NULL,
                invoice_id TEXT NOT NULL,
                amount REAL,
                payment_date TEXT,
                method TEXT,
                status TEXT,
                FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
            );
            """
        )

        # 17. parts_catalog
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS parts_catalog (
                id INT AUTO_INCREMENT PRIMARY KEY,
                part_number TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                stock_quantity INTEGER NOT NULL DEFAULT 0,
                unit_price REAL NOT NULL DEFAULT 0.0
            );
            """
        )


def execute_query(query: str, params: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
    """Execute a read-only SQL query and return all rows as dictionaries.

    For INSERT/UPDATE/DELETE, prefer `execute_non_query`.
    """

    with get_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params or [])
        return list(cur.fetchall())


def execute_non_query(query: str, params: Optional[Sequence[Any]] = None) -> int:
    """Execute a non-SELECT query and return the number of affected rows."""

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params or [])
        return cur.rowcount


def get_client_by_credentials(email: str, client_id: str) -> Optional[Client]:
    """Look up a client by email and client_id for authentication."""

    rows = execute_query(
        "SELECT client_id, name, email, client_type, city, country FROM clients WHERE email = %s AND client_id = %s",
        (email, client_id),
    )
    if not rows:
        return None
    row = rows[0]
    return Client(
        client_id=row["client_id"],
        name=row["name"],
        email=row["email"],
        client_type=row["client_type"],
        city=row["city"],
        country=row["country"],
    )


def generate_synthetic_data(num_clients: int = 50) -> Iterable[Client]:
    """Generate synthetic client records using Faker.

    Client IDs follow the pattern ME-10001, ME-10002, ...
    """

    client_types = ["Hospital", "Clinic", "Laboratory", "Imaging Center"]

    for i in range(1, num_clients + 1):
        yield Client(
            client_id=f"ME-{10000 + i}",
            name=faker.company(),
            email=faker.company_email(),
            client_type=faker.random_element(client_types),
            city=faker.city(),
            country=faker.country(),
        )


def populate_sample_data() -> None:
    """Populate the database with synthetic baseline data.

    This includes:
    - 50 clients
    - A small catalog of products
    - Example equipment registry entries
    - Example orders, shipments, warranties, tickets, and invoices
    Sufficient to exercise the main demo use cases.
    """

    with get_connection() as conn:
        cur = conn.cursor()

        # Seed clients
        for client in generate_synthetic_data():
            cur.execute(
                """
                INSERT IGNORE INTO clients (client_id, name, email, client_type, city, country)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    client.client_id,
                    client.name,
                    client.email,
                    client.client_type,
                    client.city,
                    client.country,
                ),
            )

        # Seed a minimal product catalog aligned with the spec examples
        products = [
            ("MRI-3000", "MRI-3000", "Imaging", "MRI Scanner 3000", "High-field MRI scanner.", "220-240V, 50/60Hz", "Field strength: 3T; Bore: 70cm"),
            ("CT-4000", "CT-4000", "Imaging", "CT Scanner 4000", "Multi-slice CT scanner.", "400V, 3-phase", "Slice count: 128; GANTRY: 78cm"),
            ("PM-800", "PM-800", "Patient Monitor", "Patient Monitor PM-800", "Bedside patient monitor.", "100-240V AC", "SpO2, NIBP, ECG, TEMP"),
        ]
        for sku, model, category, name, desc, power, specs in products:
            cur.execute(
                """
                INSERT IGNORE INTO products (sku, model, category, name, description, power_requirements, specifications)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (sku, model, category, name, desc, power, specs),
            )

        # Create a couple of equipment registry entries and related records for a known demo client
        demo_client_id = "ME-10001"
        cur.execute(
            "INSERT IGNORE INTO clients (client_id, name, email, client_type, city, country) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                demo_client_id,
                "City General Hospital",
                "contact@cityhospital.com",
                "Hospital",
                "Metropolis",
                "USA",
            ),
        )

        # Fetch product IDs
        cur.execute("SELECT id, sku FROM products")
        product_rows = {row[1]: row[0] for row in cur.fetchall()}

        # Equipment registry for demo client
        equipment = [
            ("US-2022-1234", demo_client_id, product_rows.get("PM-800"), "2022-06-15", "Active"),
            ("CT-2023-4000", demo_client_id, product_rows.get("CT-4000"), "2023-01-20", "Active"),
        ]
        for serial, client_id, product_id, install_date, status in equipment:
            if product_id is None:
                continue
            cur.execute(
                """
                INSERT IGNORE INTO equipment_registry (serial_number, client_id, product_id, install_date, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (serial, client_id, product_id, install_date, status),
            )

        # Orders and shipments
        order_id = "ORD-2024-0001"
        cur.execute(
            """
            INSERT IGNORE INTO orders (order_id, client_id, order_date, status, total_amount)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (order_id, demo_client_id, "2024-03-01", "Shipped", 250000.0),
        )

        cur.execute(
            """
            INSERT IGNORE INTO shipments (shipment_id, order_id, carrier, tracking_number, shipped_date, expected_delivery_date, delivery_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                "SHP-2024-0001",
                order_id,
                "MedEquip Logistics",
                "TRK123456789",
                "2024-03-02",
                "2024-03-10",
                "In Transit",
            ),
        )

        # Warranties
        cur.execute(
            """
            INSERT IGNORE INTO warranties (warranty_id, serial_number, start_date, end_date, coverage_level)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                "WAR-2022-0001",
                "US-2022-1234",
                "2022-06-15",
                "2025-06-14",
                "Standard",
            ),
        )

        # Support ticket and history
        ticket_id = "TKT-2024-0001"
        cur.execute(
            """
            INSERT IGNORE INTO support_tickets (ticket_id, client_id, serial_number, category, severity, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                ticket_id,
                demo_client_id,
                "US-2022-1234",
                "Device Failure",
                "High",
                "Open",
                "2024-02-01",
                "2024-02-02",
            ),
        )
        history_events = [
            (ticket_id, "2024-02-01T09:15:00", "Open", "Ticket created by customer portal"),
            (ticket_id, "2024-02-01T10:00:00", "In Progress", "Technician assigned"),
            (ticket_id, "2024-02-02T14:30:00", "Open", "Awaiting spare part"),
        ]
        for t_id, ts, status, notes in history_events:
            cur.execute(
                """
                INSERT IGNORE INTO ticket_history (ticket_id, event_time, status, notes)
                VALUES (%s, %s, %s, %s)
                """,
                (t_id, ts, status, notes),
            )

        # Invoice and payment
        invoice_id = "INV-2024-3456"
        cur.execute(
            """
            INSERT IGNORE INTO invoices (invoice_id, client_id, order_id, amount, issue_date, due_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                invoice_id,
                demo_client_id,
                order_id,
                250000.0,
                "2024-03-05",
                "2024-04-05",
                "Paid",
            ),
        )
        cur.execute(
            """
            INSERT IGNORE INTO payments (payment_id, invoice_id, amount, payment_date, method, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                "PAY-2024-0001",
                invoice_id,
                250000.0,
                "2024-03-20",
                "Wire Transfer",
                "Completed",
            ),
        )

        # Parts catalog
        parts = [
            ("ECG-ELECT-001", "ECG Electrodes", "Disposable ECG electrodes", 500, 2.5),
            ("VENT-FILTER-010", "Ventilator Filter", "Bacterial/viral filter for ventilators", 120, 45.0),
        ]
        for part_number, name, desc, qty, price in parts:
            cur.execute(
                """
                INSERT IGNORE INTO parts_catalog (part_number, name, description, stock_quantity, unit_price)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (part_number, name, desc, qty, price),
            )


def initialize_database() -> None:
    """Utility to create and seed the database in a single call.

    Ensures the MySQL schema database exists, then creates tables and
    seeds sample data.
    """

    ensure_mysql_database_exists()
    create_database()
    populate_sample_data()


if __name__ == "__main__":
    print(
        f"Initializing MedEquip MySQL database '{MYSQL_DB}' "
        f"on {MYSQL_HOST}:{MYSQL_PORT}"
    )
    initialize_database()
    print("Database initialization complete.")
