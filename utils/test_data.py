# utils/test_data.py - Test verileri

from __future__ import annotations

import calendar
import sqlite3
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import bcrypt

from database.db import init_db

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "database" / "company.db"

DEMO_EMPLOYEES: List[Dict[str, object]] = [
    {
        "first_name": "Admin",
        "last_name": "User",
        "email": "admin@company.com",
        "department": "Management",
        "position": "System Admin",
        "hourly_rate": 600.0,
        "is_admin": 1,
        "password": "admin123",
    },
    {
        "first_name": "Hakan",
        "last_name": "Yilmaz",
        "email": "hr@company.com",
        "department": "Human Resources",
        "position": "HR Manager",
        "hourly_rate": 450.0,
        "is_admin": 1,
        "password": "hr1234",
    },
    {
        "first_name": "Ali",
        "last_name": "Kaya",
        "email": "ali.kaya@company.com",
        "department": "IT",
        "position": "Software Developer",
        "hourly_rate": 280.0,
        "is_admin": 0,
        "password": "ali1234",
    },
    {
        "first_name": "Ayse",
        "last_name": "Demir",
        "email": "ayse.demir@company.com",
        "department": "Accounting",
        "position": "Accountant",
        "hourly_rate": 260.0,
        "is_admin": 0,
        "password": "ayse1234",
    },
    {
        "first_name": "Mehmet",
        "last_name": "Kara",
        "email": "mehmet.kara@company.com",
        "department": "Sales",
        "position": "Sales Specialist",
        "hourly_rate": 240.0,
        "is_admin": 0,
        "password": "mehmet1234",
    },
    {
        "first_name": "Zeynep",
        "last_name": "Celik",
        "email": "zeynep.celik@company.com",
        "department": "Marketing",
        "position": "Marketing Specialist",
        "hourly_rate": 230.0,
        "is_admin": 0,
        "password": "zeynep1234",
    },
    {
        "first_name": "Can",
        "last_name": "Arslan",
        "email": "can.arslan@company.com",
        "department": "Operations",
        "position": "Operations Assistant",
        "hourly_rate": 210.0,
        "is_admin": 0,
        "password": "can1234",
    },
    {
        "first_name": "Deniz",
        "last_name": "Yildiz",
        "email": "deniz.yildiz@company.com",
        "department": "IT",
        "position": "QA Engineer",
        "hourly_rate": 255.0,
        "is_admin": 0,
        "password": "deniz1234",
    },
    {
        "first_name": "Ece",
        "last_name": "Kurt",
        "email": "ece.kurt@company.com",
        "department": "Support",
        "position": "Support Specialist",
        "hourly_rate": 220.0,
        "is_admin": 0,
        "password": "ece1234",
    },
    {
        "first_name": "Mert",
        "last_name": "Ozturk",
        "email": "mert.ozturk@company.com",
        "department": "Logistics",
        "position": "Logistics Coordinator",
        "hourly_rate": 235.0,
        "is_admin": 0,
        "password": "mert1234",
    },
]


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _previous_month(year: int, month: int) -> Tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _recent_months(count: int = 2) -> List[Tuple[int, int]]:
    today = date.today()
    year, month = today.year, today.month
    months: List[Tuple[int, int]] = []

    for _ in range(count):
        months.append((year, month))
        year, month = _previous_month(year, month)

    months.reverse()
    return months


def _month_weekdays(year: int, month: int) -> List[date]:
    last_day = calendar.monthrange(year, month)[1]
    days: List[date] = []

    for day in range(1, last_day + 1):
        current = date(year, month, day)
        if current.weekday() < 5:
            days.append(current)

    return days


def _attendance_pattern(employee_index: int, day_index: int, work_date: date) -> Tuple[str, float, float]:
    selector = (employee_index * 11 + day_index * 7 + work_date.day) % 20

    if selector == 0:
        return "leave", 0.0, 0.0
    if selector in {1, 2}:
        return "absent", 0.0, 0.0

    overtime = 0.0
    if selector % 9 == 0:
        overtime = 2.0
    elif selector % 5 == 0:
        overtime = 1.0

    return "present", 8.0, overtime


def _ensure_demo_employees(conn: sqlite3.Connection) -> int:
    existing_emails = {
        row["email"]
        for row in conn.execute("SELECT email FROM employees").fetchall()
    }

    inserted = 0
    for employee in DEMO_EMPLOYEES:
        email = str(employee["email"]).strip().lower()
        if email in existing_emails:
            continue

        conn.execute(
            """
            INSERT INTO employees (
                first_name, last_name, email, department, position,
                hourly_rate, active, is_admin, password_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                employee["first_name"],
                employee["last_name"],
                email,
                employee["department"],
                employee["position"],
                float(employee["hourly_rate"]),
                1,
                int(employee["is_admin"]),
                _hash_password(str(employee["password"])),
            ),
        )
        inserted += 1

    return inserted


def _get_employee_id_map(conn: sqlite3.Connection) -> Dict[str, int]:
    rows = conn.execute("SELECT employee_id, email FROM employees").fetchall()
    return {str(row["email"]).strip().lower(): int(row["employee_id"]) for row in rows}


def _ensure_demo_attendance(conn: sqlite3.Connection) -> int:
    employee_id_map = _get_employee_id_map(conn)
    seeded_months = _recent_months(2)

    existing_pairs = {
        (int(row["employee_id"]), str(row["work_date"]))
        for row in conn.execute("SELECT employee_id, work_date FROM attendance").fetchall()
    }

    inserted = 0

    for employee_index, employee in enumerate(DEMO_EMPLOYEES):
        email = str(employee["email"]).strip().lower()
        employee_id = employee_id_map.get(email)
        if employee_id is None:
            continue

        for year, month in seeded_months:
            weekdays = _month_weekdays(year, month)

            for day_index, work_date in enumerate(weekdays):
                status, work_hours, overtime_hours = _attendance_pattern(
                    employee_index=employee_index,
                    day_index=day_index,
                    work_date=work_date,
                )

                key = (employee_id, work_date.isoformat())
                if key in existing_pairs:
                    continue

                conn.execute(
                    """
                    INSERT INTO attendance (
                        employee_id, work_date, status, work_hours, overtime_hours
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        employee_id,
                        work_date.isoformat(),
                        status,
                        float(work_hours),
                        float(overtime_hours),
                    ),
                )
                inserted += 1

    return inserted


def seed_demo_data() -> Dict[str, int]:
    """
    Seed demo employees and attendance data into company.db.

    Returns:
        dict with inserted counts:
        {
            "employees": int,
            "attendance": int
        }
    """
    init_db()

    conn = _connect()
    try:
        employees_inserted = _ensure_demo_employees(conn)
        attendance_inserted = _ensure_demo_attendance(conn)
        conn.commit()
        return {
            "employees": employees_inserted,
            "attendance": attendance_inserted,
        }
    finally:
        conn.close()


def print_demo_credentials() -> None:
    for employee in DEMO_EMPLOYEES:
        print(f'{employee["email"]} / {employee["password"]}')


if __name__ == "__main__":
    result = seed_demo_data()
    print(
        f'Demo data seeded: {result["employees"]} employees, '
        f'{result["attendance"]} attendance records.'
    )
    print("\nCredentials:")
    print_demo_credentials()