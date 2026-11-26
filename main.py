
import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime, date
from functools import wraps
from abc import ABC, abstractmethod


# =========================
# CONFIGURATION
# =========================

BASE_DIR = Path(__file__).resolve().parent
DB_NAME = BASE_DIR / "orbit.db"
LOG_FILE = BASE_DIR / "orbit.log"


# =========================
# DATABASE
# =========================

def get_connection():

    db = sqlite3.connect(DB_NAME)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    return db


def initialize_database():

    with get_connection() as db:

        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            destination TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            budget REAL NOT NULL,
            status TEXT DEFAULT 'Planned',
            FOREIGN KEY(user_id) REFERENCES users(id)
            ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS destinations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            city TEXT NOT NULL,
            country TEXT NOT NULL,
            FOREIGN KEY(trip_id) REFERENCES trips(id)
            ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destination_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            activity_date TEXT NOT NULL,
            cost REAL NOT NULL,
            status TEXT DEFAULT 'Planned',
            FOREIGN KEY(destination_id) REFERENCES destinations(id)
            ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            expense_date TEXT NOT NULL,
            FOREIGN KEY(trip_id) REFERENCES trips(id)
            ON DELETE CASCADE
        );
        """)

    print("Database initialized!")


# =========================
# VALIDATORS
# =========================

def validate_email(email):

    pattern = r"^[\w.-]+@[\w.-]+\.\w+$"

    return re.match(pattern, email) is not None


def validate_date(date_text):

    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return True

    except ValueError:
        return False


def validate_amount(amount):

    try:
        return float(amount) > 0

    except (ValueError, TypeError):
        return False


# =========================
# DECORATOR
# =========================

def log_action(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        try:

            result = func(*args, **kwargs)

            with open(LOG_FILE, "a", encoding="utf-8") as file:
                file.write(
                    f"{datetime.now()} | "
                    f"{func.__name__} | SUCCESS\n"
                )

            return result

        except Exception as error:

            with open(LOG_FILE, "a", encoding="utf-8") as file:
                file.write(
                    f"{datetime.now()} | "
                    f"{func.__name__} | ERROR: {error}\n"
                )

            print("An error occurred:", error)
            return None

    return wrapper


# =========================
# USER
# =========================

class User:

    def __init__(self, user_id, username, email):

        self.user_id = user_id
        self.username = username
        self.email = email

    @staticmethod
    def get_or_create(username, email):

        if not username.strip():
            print("Username cannot be empty!")
            return None

        if not validate_email(email):
            print("Invalid email!")
            return None

        with get_connection() as db:

            user = db.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()

            if user:
                return User(
                    user["id"],
                    user["username"],
                    user["email"]
                )

            cursor = db.execute("""
                INSERT INTO users (username, email)
                VALUES (?, ?)
            """, (username, email))

            return User(
                cursor.lastrowid,
                username,
                email
            )

    def display(self):

        print(f"Username: {self.username}")
        print(f"Email: {self.email}")


# =========================
# TRIP
# =========================

class Trip:

    def __init__(
        self,
        trip_id,
        user_id,
        title,
        destination,
        start_date,
        end_date,
        budget,
        status
    ):

        self.trip_id = trip_id
        self.user_id = user_id
        self.title = title
        self.destination = destination
        self.start_date = start_date
        self.end_date = end_date
        self.budget = budget
        self.status = status

    @property
    def duration(self):

        start = date.fromisoformat(self.start_date)
        end = date.fromisoformat(self.end_date)

        return (end - start).days + 1

    def display(self):

        print("-" * 40)
        print(f"ID: {self.trip_id}")
        print(f"Trip: {self.title}")
        print(f"Destination: {self.destination}")
        print(f"Dates: {self.start_date} -> {self.end_date}")
        print(f"Duration: {self.duration} days")
        print(f"Budget: {self.budget:.2f} EGP")
        print(f"Status: {self.status}")
        print("-" * 40)


# =========================
# ACTIVITY OOP
# =========================

class Activity(ABC):

    def __init__(self, name, cost):

        self.name = name
        self.cost = cost

    @abstractmethod
    def calculate_cost(self):
        pass


class Sightseeing(Activity):

    def calculate_cost(self):
        return self.cost


class Accommodation(Activity):

    def calculate_cost(self):
        return self.cost * 1.10


class Transportation(Activity):

    def calculate_cost(self):
        return self.cost * 1.05


# =========================
# TRIP MANAGER
# =========================

class TripManager:

    @staticmethod
    @log_action
    def add_trip(user_id, title, destination,
                 start_date, end_date, budget):

        if not title.strip() or not destination.strip():
            print("Title and destination are required!")
            return False

        if not validate_date(start_date) or not validate_date(end_date):
            print("Date must be YYYY-MM-DD!")
            return False

        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        if end < start:
            print("End date cannot be before start date!")
            return False

        if not validate_amount(budget):
            print("Invalid budget!")
            return False

        with get_connection() as db:

            db.execute("""
                INSERT INTO trips
                (user_id, title, destination, start_date,
                 end_date, budget)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id, title, destination,
                start_date, end_date, float(budget)
            ))

        print("Trip added!")
        return True

    @staticmethod
    def show_trips(user_id):

        with get_connection() as db:

            rows = db.execute("""
                SELECT * FROM trips
                WHERE user_id = ?
                ORDER BY id DESC
            """, (user_id,)).fetchall()

        if not rows:
            print("No trips found!")
            return

        for row in rows:

            trip = Trip(
                row["id"],
                row["user_id"],
                row["title"],
                row["destination"],
                row["start_date"],
                row["end_date"],
                row["budget"],
                row["status"]
            )

            trip.display()

    @staticmethod
    @log_action
    def update_budget(user_id, trip_id, budget):

        if not validate_amount(budget):
            print("Invalid budget!")
            return False

        with get_connection() as db:

            cursor = db.execute("""
                UPDATE trips
                SET budget = ?
                WHERE id = ? AND user_id = ?
            """, (float(budget), trip_id, user_id))

        if cursor.rowcount:
            print("Budget updated!")
            return True

        print("Trip not found!")
        return False

    @staticmethod
    @log_action
    def update_status(user_id, trip_id, status):

        if status not in ["Planned", "Ongoing", "Completed"]:
            print("Invalid status!")
            return False

        with get_connection() as db:

            cursor = db.execute("""
                UPDATE trips
                SET status = ?
                WHERE id = ? AND user_id = ?
            """, (status, trip_id, user_id))

        if cursor.rowcount:
            print("Status updated!")
            return True

        print("Trip not found!")
        return False

    @staticmethod
    @log_action
    def delete_trip(user_id, trip_id):

        with get_connection() as db:

            cursor = db.execute("""
                DELETE FROM trips
                WHERE id = ? AND user_id = ?
            """, (trip_id, user_id))

        if cursor.rowcount:
            print("Trip deleted!")
            return True

        print("Trip not found!")
        return False


# =========================
# DESTINATION MANAGER
# =========================

class DestinationManager:

    @staticmethod
    @log_action
    def add_destination(user_id, trip_id, city, country):

        if not city.strip() or not country.strip():
            print("City and country are required!")
            return False

        with get_connection() as db:

            trip = db.execute("""
                SELECT id FROM trips
                WHERE id = ? AND user_id = ?
            """, (trip_id, user_id)).fetchone()

            if trip is None:
                print("Trip not found!")
                return False

            db.execute("""
                INSERT INTO destinations
                (trip_id, city, country)
                VALUES (?, ?, ?)
            """, (trip_id, city, country))

        print("Destination added!")
        return True

    @staticmethod
    def show_destinations(user_id, trip_id):

        with get_connection() as db:

            rows = db.execute("""
                SELECT d.*
                FROM destinations d
                JOIN trips t ON d.trip_id = t.id
                WHERE t.id = ? AND t.user_id = ?
            """, (trip_id, user_id)).fetchall()

        if not rows:
            print("No destinations found!")
            return

        for row in rows:

            print(
                f"ID: {row['id']} | "
                f"{row['city']}, {row['country']}"
            )


# =========================
# ACTIVITY MANAGER
# =========================

class ActivityManager:

    TYPES = {
        "1": Sightseeing,
        "2": Accommodation,
        "3": Transportation
    }

    @staticmethod
    @log_action
    def add_activity(user_id, destination_id, name,
                     activity_date, cost, activity_type):

        if not name.strip():
            print("Activity name is required!")
            return False

        if not validate_date(activity_date):
            print("Invalid date!")
            return False

        if not validate_amount(cost):
            print("Invalid cost!")
            return False

        activity_class = ActivityManager.TYPES.get(activity_type)

        if activity_class is None:
            print("Invalid activity type!")
            return False

        with get_connection() as db:

            destination = db.execute("""
                SELECT d.id, t.start_date, t.end_date
                FROM destinations d
                JOIN trips t ON d.trip_id = t.id
                WHERE d.id = ? AND t.user_id = ?
            """, (destination_id, user_id)).fetchone()

            if destination is None:
                print("Destination not found!")
                return False

            if not (
                destination["start_date"]
                <= activity_date
                <= destination["end_date"]
            ):
                print("Activity date must be within trip dates!")
                return False

            activity = activity_class(name, float(cost))
            final_cost = activity.calculate_cost()

            db.execute("""
                INSERT INTO activities
                (destination_id, name, activity_date, cost)
                VALUES (?, ?, ?, ?)
            """, (
                destination_id, name,
                activity_date, final_cost
            ))

        print(f"Activity added! Final cost: {final_cost:.2f}")
        return True

    @staticmethod
    def show_activities(user_id, destination_id):

        with get_connection() as db:

            rows = db.execute("""
                SELECT a.*
                FROM activities a
                JOIN destinations d ON a.destination_id = d.id
                JOIN trips t ON d.trip_id = t.id
                WHERE d.id = ? AND t.user_id = ?
            """, (destination_id, user_id)).fetchall()

        if not rows:
            print("No activities found!")
            return

        for row in rows:

            print(
                f"ID: {row['id']} | {row['name']} | "
                f"{row['activity_date']} | "
                f"{row['cost']:.2f} EGP | {row['status']}"
            )

    @staticmethod
    @log_action
    def complete_activity(user_id, activity_id):

        with get_connection() as db:

            cursor = db.execute("""
                UPDATE activities
                SET status = 'Completed'
                WHERE id = ?
                AND destination_id IN (
                    SELECT d.id
                    FROM destinations d
                    JOIN trips t ON d.trip_id = t.id
                    WHERE t.user_id = ?
                )
            """, (activity_id, user_id))

        if cursor.rowcount:
            print("Activity completed!")
            return True

        print("Activity not found!")
        return False


# =========================
# EXPENSE MANAGER
# =========================

class ExpenseManager:

    CATEGORIES = [
        "Hotel", "Food", "Transport",
        "Activities", "Shopping", "Other"
    ]

    @staticmethod
    @log_action
    def add_expense(user_id, trip_id, category,
                    amount, description):

        if category not in ExpenseManager.CATEGORIES:
            print("Invalid category!")
            return False

        if not validate_amount(amount):
            print("Invalid amount!")
            return False

        with get_connection() as db:

            trip = db.execute("""
                SELECT id FROM trips
                WHERE id = ? AND user_id = ?
            """, (trip_id, user_id)).fetchone()

            if trip is None:
                print("Trip not found!")
                return False

            db.execute("""
                INSERT INTO expenses
                (trip_id, category, amount, description, expense_date)
                VALUES (?, ?, ?, ?, ?)
            """, (
                trip_id,
                category,
                float(amount),
                description,
                date.today().isoformat()
            ))

        print("Expense recorded!")
        return True

    @staticmethod
    def show_expenses(user_id, trip_id):

        with get_connection() as db:

            rows = db.execute("""
                SELECT e.*
                FROM expenses e
                JOIN trips t ON e.trip_id = t.id
                WHERE e.trip_id = ? AND t.user_id = ?
                ORDER BY e.id DESC
            """, (trip_id, user_id)).fetchall()

        if not rows:
            print("No expenses found!")
            return

        for row in rows:

            print(
                f"ID: {row['id']} | "
                f"{row['category']} | "
                f"{row['amount']:.2f} EGP | "
                f"{row['description']} | "
                f"{row['expense_date']}"
            )


# =========================
# ANALYTICS
# =========================

class AnalyticsManager:

    @staticmethod
    def trip_report(user_id, trip_id):

        with get_connection() as db:

            trip = db.execute("""
                SELECT * FROM trips
                WHERE id = ? AND user_id = ?
            """, (trip_id, user_id)).fetchone()

            if trip is None:
                print("Trip not found!")
                return

            expenses = db.execute("""
                SELECT COALESCE(SUM(amount), 0)
                FROM expenses
                WHERE trip_id = ?
            """, (trip_id,)).fetchone()[0]

            planned = db.execute("""
                SELECT COALESCE(SUM(a.cost), 0)
                FROM activities a
                JOIN destinations d ON a.destination_id = d.id
                WHERE d.trip_id = ?
            """, (trip_id,)).fetchone()[0]

            categories = db.execute("""
                SELECT category, SUM(amount) AS total
                FROM expenses
                WHERE trip_id = ?
                GROUP BY category
                ORDER BY total DESC
            """, (trip_id,)).fetchall()

        budget = trip["budget"]
        remaining = budget - expenses

        print("\n========== TRIP REPORT ==========")
        print(f"Trip: {trip['title']}")
        print(f"Destination: {trip['destination']}")
        print(f"Budget: {budget:.2f} EGP")
        print(f"Actual Expenses: {expenses:.2f} EGP")
        print(f"Planned Activities: {planned:.2f} EGP")
        print(f"Remaining: {remaining:.2f} EGP")

        if budget:
            print(f"Budget Usage: {expenses / budget * 100:.1f}%")

        print("\nExpenses by category:")

        for row in categories:
            print(f"{row['category']}: {row['total']:.2f} EGP")

        if remaining < 0:
            print("WARNING: Budget exceeded!")
        elif remaining <= budget * 0.2:
            print("Warning: Budget is getting low!")
        else:
            print("Budget is under control!")

        print("=" * 35)

    @staticmethod
    def general_statistics(user_id):

        with get_connection() as db:

            trips = db.execute("""
                SELECT COUNT(*) FROM trips WHERE user_id = ?
            """, (user_id,)).fetchone()[0]

            completed = db.execute("""
                SELECT COUNT(*) FROM trips
                WHERE user_id = ? AND status = 'Completed'
            """, (user_id,)).fetchone()[0]

            expenses = db.execute("""
                SELECT COALESCE(SUM(e.amount), 0)
                FROM expenses e
                JOIN trips t ON e.trip_id = t.id
                WHERE t.user_id = ?
            """, (user_id,)).fetchone()[0]

        print("\n========== GENERAL STATISTICS ==========")
        print(f"Total trips: {trips}")
        print(f"Completed trips: {completed}")
        print(f"Total expenses: {expenses:.2f} EGP")

        if trips:
            print(f"Completion rate: {completed / trips * 100:.1f}%")

        print("=" * 35)


# =========================
# JSON EXPORT
# =========================

class ExportManager:

    @staticmethod
    @log_action
    def export_trip(user_id, trip_id):

        with get_connection() as db:

            trip = db.execute("""
                SELECT * FROM trips
                WHERE id = ? AND user_id = ?
            """, (trip_id, user_id)).fetchone()

            if trip is None:
                print("Trip not found!")
                return False

            result = dict(trip)
            result["destinations"] = []

            destinations = db.execute("""
                SELECT * FROM destinations WHERE trip_id = ?
            """, (trip_id,)).fetchall()

            for destination in destinations:

                destination_data = dict(destination)

                activities = db.execute("""
                    SELECT * FROM activities
                    WHERE destination_id = ?
                """, (destination["id"],)).fetchall()

                destination_data["activities"] = [
                    dict(activity) for activity in activities
                ]

                result["destinations"].append(destination_data)

            expenses = db.execute("""
                SELECT * FROM expenses WHERE trip_id = ?
            """, (trip_id,)).fetchall()

            result["expenses"] = [
                dict(expense) for expense in expenses
            ]

        filename = BASE_DIR / f"trip_{trip_id}_export.json"

        with open(filename, "w", encoding="utf-8") as file:

            json.dump(
                result,
                file,
                ensure_ascii=False,
                indent=4
            )

        print(f"Exported to: {filename.name}")
        return True


# =========================
# INPUT HELPERS
# =========================

def get_int(message):

    try:
        return int(input(message))

    except ValueError:
        print("Enter a valid integer!")
        return None


def get_float(message):

    try:
        return float(input(message))

    except ValueError:
        print("Enter a valid number!")
        return None


# =========================
# MENUS
# =========================

def trip_menu(user_id):

    while True:

        print("""
========== TRIPS ==========

1. Add trip
2. Show trips
3. Update budget
4. Update status
5. Delete trip
6. Back
""")

        choice = input("Choose: ").strip()

        if choice == "1":

            title = input("Title: ")
            destination = input("Destination: ")
            start = input("Start date YYYY-MM-DD: ")
            end = input("End date YYYY-MM-DD: ")
            budget = get_float("Budget: ")

            if budget is not None:
                TripManager.add_trip(
                    user_id, title, destination,
                    start, end, budget
                )

        elif choice == "2":
            TripManager.show_trips(user_id)

        elif choice == "3":

            trip_id = get_int("Trip ID: ")
            budget = get_float("New budget: ")

            if trip_id is not None and budget is not None:
                TripManager.update_budget(user_id, trip_id, budget)

        elif choice == "4":

            trip_id = get_int("Trip ID: ")
            status = input("Planned / Ongoing / Completed: ").strip().title()

            if trip_id is not None:
                TripManager.update_status(user_id, trip_id, status)

        elif choice == "5":

            trip_id = get_int("Trip ID: ")

            if trip_id is not None:
                TripManager.delete_trip(user_id, trip_id)

        elif choice == "6":
            break

        else:
            print("Invalid choice!")


def destination_menu(user_id):

    while True:

        print("""
========== DESTINATIONS ==========

1. Add destination
2. Show destinations
3. Back
""")

        choice = input("Choose: ").strip()

        if choice == "1":

            trip_id = get_int("Trip ID: ")

            if trip_id is None:
                continue

            city = input("City: ")
            country = input("Country: ")

            DestinationManager.add_destination(
                user_id, trip_id, city, country
            )

        elif choice == "2":

            trip_id = get_int("Trip ID: ")

            if trip_id is not None:
                DestinationManager.show_destinations(user_id, trip_id)

        elif choice == "3":
            break

        else:
            print("Invalid choice!")


def activity_menu(user_id):

    while True:

        print("""
========== ACTIVITIES ==========

1. Add activity
2. Show activities
3. Complete activity
4. Back
""")

        choice = input("Choose: ").strip()

        if choice == "1":

            destination_id = get_int("Destination ID: ")

            if destination_id is None:
                continue

            name = input("Activity name: ")
            activity_date = input("Date YYYY-MM-DD: ")
            cost = get_float("Base cost: ")

            if cost is None:
                continue

            print("""
1. Sightseeing
2. Accommodation
3. Transportation
""")

            activity_type = input("Type: ").strip()

            ActivityManager.add_activity(
                user_id, destination_id,
                name, activity_date,
                cost, activity_type
            )

        elif choice == "2":

            destination_id = get_int("Destination ID: ")

            if destination_id is not None:
                ActivityManager.show_activities(
                    user_id, destination_id
                )

        elif choice == "3":

            activity_id = get_int("Activity ID: ")

            if activity_id is not None:
                ActivityManager.complete_activity(
                    user_id, activity_id
                )

        elif choice == "4":
            break

        else:
            print("Invalid choice!")


def expense_menu(user_id):

    while True:

        print("""
========== EXPENSES ==========

1. Add expense
2. Show expenses
3. Back
""")

        choice = input("Choose: ").strip()

        if choice == "1":

            trip_id = get_int("Trip ID: ")

            if trip_id is None:
                continue

            print("Categories:", ", ".join(ExpenseManager.CATEGORIES))

            category = input("Category: ").strip().title()
            amount = get_float("Amount: ")

            if amount is None:
                continue

            description = input("Description: ")

            ExpenseManager.add_expense(
                user_id, trip_id,
                category, amount, description
            )

        elif choice == "2":

            trip_id = get_int("Trip ID: ")

            if trip_id is not None:
                ExpenseManager.show_expenses(user_id, trip_id)

        elif choice == "3":
            break

        else:
            print("Invalid choice!")


def main_menu(user):

    while True:

        print(f"""
================================
       ORBIT TRAVEL PLANNER
================================

Welcome {user.username}!

1. Trip management
2. Destination management
3. Activity planner
4. Expense management
5. Trip analytics
6. General statistics
7. Export trip to JSON
8. User information
9. Exit
""")

        choice = input("Choose: ").strip()

        if choice == "1":
            trip_menu(user.user_id)

        elif choice == "2":
            destination_menu(user.user_id)

        elif choice == "3":
            activity_menu(user.user_id)

        elif choice == "4":
            expense_menu(user.user_id)

        elif choice == "5":

            trip_id = get_int("Trip ID: ")

            if trip_id is not None:
                AnalyticsManager.trip_report(user.user_id, trip_id)

        elif choice == "6":
            AnalyticsManager.general_statistics(user.user_id)

        elif choice == "7":

            trip_id = get_int("Trip ID: ")

            if trip_id is not None:
                ExportManager.export_trip(user.user_id, trip_id)

        elif choice == "8":
            user.display()

        elif choice == "9":
            print("Goodbye!")
            break

        else:
            print("Invalid choice!")


# =========================
# RUN PROGRAM
# =========================

def run_orbit():

    initialize_database()

    print("""
================================
       WELCOME TO ORBIT
    SMART TRAVEL PLANNER
================================
""")

    username = input("Username: ").strip()
    email = input("Email: ").strip()

    user = User.get_or_create(username, email)

    if user is not None:
        main_menu(user)


if __name__ == "__main__":
    run_orbit()
