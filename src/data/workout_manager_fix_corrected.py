#!/usr/bin/env python3
"""
Workout Manager Fix for Rogue to Garmin Bridge (Corrected Syntax)

This script diagnoses and fixes issues with workout data storage and display.
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("workout_manager_fix")

class WorkoutManagerFix:
    """
    Utility class to diagnose and fix workout data storage issues.
    """

    def __init__(self, db_path):
        """
        Initialize with database path.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def _connect(self):
        """Connect to the database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {str(e)}")
            raise

    def _disconnect(self):
        """Disconnect from the database."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def check_database_structure(self):
        """
        Check if the database has the correct structure.

        Returns:
            Dict with check results
        """
        columns = [] # Initialize columns to avoid potential UnboundLocalError
        try:
            self._connect()

            # Check tables
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type=\"table\"")
            tables = [row["name"] for row in self.cursor.fetchall()]

            required_tables = ["devices", "workouts", "workout_data", "user_profile", "configuration"]
            missing_tables = [table for table in required_tables if table not in tables]

            # Check workout_data table structure
            if "workout_data" in tables:
                self.cursor.execute("PRAGMA table_info(workout_data)")
                columns = [row["name"] for row in self.cursor.fetchall()]
                required_columns = ["id", "workout_id", "timestamp", "data"]
                missing_columns = [col for col in required_columns if col not in columns]
            else:
                missing_columns = []

            return {
                "tables": tables,
                "missing_tables": missing_tables,
                "workout_data_columns": columns if "workout_data" in tables else [],
                "missing_columns": missing_columns,
                "database_ok": len(missing_tables) == 0 and len(missing_columns) == 0
            }
        except sqlite3.Error as e:
            logger.error(f"Error checking database structure: {str(e)}")
            return {"error": str(e)}
        finally:
            self._disconnect()

    def check_workout_data(self):
        """
        Check if workout data is being stored correctly.

        Returns:
            Dict with check results
        """
        try:
            self._connect()

            # Get workouts
            self.cursor.execute("SELECT id, device_id, workout_type, start_time, end_time FROM workouts")
            workouts = [dict(row) for row in self.cursor.fetchall()]

            # Check data points for each workout
            workout_data_counts = {}
            for workout in workouts:
                workout_id = workout["id"]
                self.cursor.execute("SELECT COUNT(*) as count FROM workout_data WHERE workout_id = ?", (workout_id,))
                count = self.cursor.fetchone()["count"]
                workout_data_counts[workout_id] = count

            return {
                "workouts": workouts,
                "workout_data_counts": workout_data_counts,
                "has_workouts": len(workouts) > 0,
                "has_workout_data": any(count > 0 for count in workout_data_counts.values())
            }
        except sqlite3.Error as e:
            logger.error(f"Error checking workout data: {str(e)}")
            return {"error": str(e)}
        finally:
            self._disconnect()

    def fix_add_data_point_method(self, workout_manager_path):
        """
        Fix the add_data_point method in workout_manager.py.

        Args:
            workout_manager_path: Path to workout_manager.py

        Returns:
            True if fixed, False otherwise
        """
        try:
            # Read the file
            with open(workout_manager_path, "r") as f:
                content = f.read()

            # Check if the add_data_point method is calling db.add_workout_data
            # This check might be too simple; assumes the call is missing entirely.
            if "def add_data_point" in content and "self.db.add_workout_data" not in content:

                # Define the replacement code using raw triple quotes
                replacement_code = r"""def add_data_point(self, data):
        \"\"\
        Add a data point to the current workout.

        Args:
            data: Dictionary of workout data
        \"\"\
        if not self.active_workout_id:
            logger.warning(\"No active workout to add data point to\")
            return

        # Add timestamp if not present
        if \'timestamp\' not in data:
            data[\'timestamp\'] = int((datetime.now() - self.start_time).total_seconds())

        # Store data point in database
        try:
            self.db.add_workout_data(self.active_workout_id, data[\'timestamp\'], data)
        except Exception as e:
            logger.error(f\"Error adding workout data point to database: {str(e)}\")

        # Process data for real-time metrics""" # NOTE: This assumes the rest of the method follows

                # Replace the original method signature line
                # WARNING: This is a simple replacement and might break if the original
                # method signature line appears elsewhere or if the method body needs
                # more complex replacement logic.
                fixed_content = content.replace(
                    "def add_data_point(self, data):",
                    replacement_code,
                    1 # Replace only the first occurrence
                )

                # Write the fixed file
                with open(workout_manager_path, "w") as f:
                    f.write(fixed_content)

                return True
            else:
                logger.info("add_data_point method already contains db.add_workout_data call or not found")
                return False
        except Exception as e:
            logger.error(f"Error fixing add_data_point method: {str(e)}")
            return False

    def fix_get_workout_data_method(self, database_path):
        """
        Fix the get_workout_data method in database.py.

        Args:
            database_path: Path to database.py

        Returns:
            True if fixed, False otherwise
        """
        try:
            # Read the file
            with open(database_path, "r") as f:
                content = f.read()

            # Check if the get_workout_data method needs fixing
            if "def get_workout_data" in content:

                replacement_code = r"""def get_workout_data(self, workout_id):
        \"\"\
        Get all data points for a workout.

        Args:
            workout_id: Workout ID

        Returns:
            List of data points or empty list if not found
        \"\"\
        try:
            self._connect()

            # Verify workout exists
            self.cursor.execute(\"SELECT id FROM workouts WHERE id = ?\", (workout_id,))
            if not self.cursor.fetchone():
                logger.warning(f\"Workout {workout_id} not found\")
                return []

            # Get all data points
            self.cursor.execute(
                \"SELECT timestamp, data FROM workout_data WHERE workout_id = ? ORDER BY timestamp\",
                (workout_id,)
            )

            result = []
            for row in self.cursor.fetchall():
                try:
                    data_point = json.loads(row[\'data\'])
                    data_point[\'timestamp\'] = row[\'timestamp\']
                    result.append(data_point)
                except json.JSONDecodeError:
                    logger.error(f\"Error decoding data for workout {workout_id}, timestamp {row[\'timestamp\']}\")

            return result
        except sqlite3.Error as e:
            logger.error(f\"Error getting workout data: {str(e)}\")
            return []
        finally:
            self._disconnect()"""

                # Replace the original method signature line
                fixed_content = content.replace(
                    "def get_workout_data(self, workout_id):",
                    replacement_code,
                    1 # Replace only the first occurrence
                )

                # Write the fixed file
                with open(database_path, "w") as f:
                    f.write(fixed_content)

                return True
            else:
                logger.info("get_workout_data method not found")
                return False
        except Exception as e:
            logger.error(f"Error fixing get_workout_data method: {str(e)}")
            return False

    def fix_api_workout_details(self, app_path):
        """
        Fix the API endpoint for workout details in app.py.

        Args:
            app_path: Path to app.py

        Returns:
            True if fixed, False otherwise
        """
        try:
            # Read the file
            with open(app_path, "r") as f:
                content = f.read()

            # Check if the get_workout method needs fixing
            if "def get_workout(" in content:

                replacement_code = r"""def get_workout(workout_id):
    \"\"\"Get workout details.\"\"\"
    try:
        # Get workout details
        workout = workout_manager.get_workout(workout_id)
        if not workout:
            return jsonify({\'success\': False, \'error\': \'Workout not found\'}) # Corrected jsonify call

        # Get workout data points
        # Ensure workout_manager and its db attribute are accessible here
        # Might need adjustment based on actual app structure
        workout_data = workout_manager.db.get_workout_data(workout_id)

        # Process data for charts
        timestamps = []
        powers = []
        cadences = []
        heart_rates = []
        speeds = []
        distances = []

        for data_point in workout_data:
            timestamps.append(data_point.get(\'timestamp\', 0))
            powers.append(data_point.get(\'power\', 0))
            cadences.append(data_point.get(\'cadence\', 0)) # Assumes bike data, adjust if needed
            heart_rates.append(data_point.get(\'heart_rate\', 0))
            speeds.append(data_point.get(\'speed\', 0)) # Assumes bike data, adjust if needed
            distances.append(data_point.get(\'distance\', 0))

        # Add data series to workout
        # Ensure workout is a mutable dictionary
        if isinstance(workout, sqlite3.Row):
             workout = dict(workout)
        elif not isinstance(workout, dict):
             logger.error(f"Workout object is not a dictionary or Row: {type(workout)}")
             return jsonify({\'success\': False, \'error\': \'Internal server error: Invalid workout object type\'}) # Corrected jsonify call

        workout[\'data_series\'] = {
            \'timestamps\': timestamps,
            \'powers\': powers,
            \'cadences\': cadences,
            \'heart_rates\': heart_rates,
            \'speeds\': speeds,
            \'distances\': distances
        }

        return jsonify({\'success\': True, \'workout\': workout}) # Corrected jsonify call
    except Exception as e:
        logger.error(f\"Error getting workout details: {str(e)}\")
        return jsonify({\'success\': False, \'error\': str(e)}) # Corrected jsonify call"""

                # Replace the original method signature line
                fixed_content = content.replace(
                    "def get_workout(workout_id):",
                    replacement_code,
                    1 # Replace only the first occurrence
                )

                # Write the fixed file
                with open(app_path, "w") as f:
                    f.write(fixed_content)

                return True
            else:
                logger.info("get_workout method not found")
                return False
        except Exception as e:
            logger.error(f"Error fixing get_workout method: {str(e)}")
            return False

    def run_diagnostics(self):
        """
        Run diagnostics on the database and return results.

        Returns:
            Dict with diagnostic results
        """
        results = {
            "database_structure": self.check_database_structure(),
            "workout_data": self.check_workout_data()
        }

        return results

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python workout_manager_fix.py <path_to_db>")
        sys.exit(1)

    db_path = sys.argv[1]
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        sys.exit(1)

    fixer = WorkoutManagerFix(db_path)
    results = fixer.run_diagnostics()

    print(json.dumps(results, indent=2))

    # Determine if fixes are needed
    if not results["database_structure"]["database_ok"]:
        print("Database structure issues found. Please check the schema.")

    if not results["workout_data"]["has_workout_data"] and results["workout_data"]["has_workouts"]:
        print("Workouts exist but no workout data points are stored. This indicates an issue with data storage.")

        # Get paths to files that need fixing
        workout_manager_path = input("Enter path to workout_manager.py: ")
        database_path = input("Enter path to database.py: ")
        app_path = input("Enter path to app.py: ")

        # Apply fixes
        if os.path.exists(workout_manager_path):
            if fixer.fix_add_data_point_method(workout_manager_path):
                print("Fixed add_data_point method in workout_manager.py")
            else:
                print("No changes made to workout_manager.py")

        if os.path.exists(database_path):
            if fixer.fix_get_workout_data_method(database_path):
                print("Fixed get_workout_data method in database.py")
            else:
                print("No changes made to database.py")

        if os.path.exists(app_path):
            if fixer.fix_api_workout_details(app_path):
                print("Fixed get_workout method in app.py")
            else:
                print("No changes made to app.py")
    else:
        print("No issues found with workout data storage.")

if __name__ == "__main__":
    main()

