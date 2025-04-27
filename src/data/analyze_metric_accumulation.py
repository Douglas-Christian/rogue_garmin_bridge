#!/usr/bin/env python3
"""
Metric Accumulation Diagnostic Tool

This tool analyzes workout data to check if metrics like distance and calories
are properly accumulating during workouts.
"""

import sqlite3
import json
import os
import sys
from datetime import datetime

# Determine the database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'rogue_garmin.db')

def analyze_metric_accumulation():
    """Analyze all workouts for metric accumulation issues."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all workouts
    cursor.execute("SELECT id, start_time, end_time, workout_type, device_id, summary FROM workouts ORDER BY id")
    workouts = cursor.fetchall()
    
    print(f"Found {len(workouts)} total workouts in database")
    
    # Stats for summary at the end
    problem_workouts = []
    empty_workouts = []
    good_workouts = []
    
    for workout in workouts:
        workout_id = workout['id']
        workout_type = workout['workout_type'] or 'unknown'
        start_time = workout['start_time']
        end_time = workout['end_time']
        device_id = workout['device_id']
        summary = None
        
        if workout['summary']:
            try:
                summary = json.loads(workout['summary'])
            except json.JSONDecodeError:
                print(f"  Error parsing summary JSON for workout {workout_id}")
        
        # Get device info
        device_info = "Unknown device"
        try:
            cursor.execute("SELECT name, device_type FROM devices WHERE id = ?", (device_id,))
            device = cursor.fetchone()
            if device:
                device_info = f"{device['name']} ({device['device_type']})"
        except Exception as e:
            print(f"  Error fetching device info: {e}")
        
        print(f"\n======== Analyzing Workout {workout_id} ({workout_type}) ========")
        print(f"  Device: {device_info} (ID: {device_id})")
        print(f"  Start: {start_time}, End: {end_time or 'Not ended'}")
        
        duration = None
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                duration = (end_dt - start_dt).total_seconds()
                print(f"  Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
            except Exception as e:
                print(f"  Error calculating duration: {e}")
        
        # Get all data points for this workout
        cursor.execute(
            "SELECT timestamp, data FROM workout_data WHERE workout_id = ? ORDER BY timestamp",
            (workout_id,)
        )
        data_points = cursor.fetchall()
        
        print(f"  Total data points: {len(data_points)}")
        
        if len(data_points) < 2:
            empty_workouts.append(workout_id)
            print(f"  Insufficient data points ({len(data_points)}) to analyze accumulation")
            
            # Check if workout ended properly
            if not end_time:
                print("  WARNING: Workout was not properly ended in the database")
            
            # Print summary if available
            if summary:
                print("  Summary data (despite no data points):")
                for key, value in summary.items():
                    print(f"    {key}: {value}")
            
            # Look for errors in workout_data table
            try:
                cursor.execute("SELECT COUNT(*) as error_count FROM workout_data WHERE workout_id = ? AND data LIKE '%error%'", (workout_id,))
                error_count = cursor.fetchone()['error_count']
                if error_count > 0:
                    print(f"  Found {error_count} data points with 'error' in them")
            except Exception as e:
                print(f"  Error checking for error data: {e}")
                
            continue
        
        # Extract metrics to analyze
        distances = []
        calories = []
        power_values = []
        heart_rate_values = []
        data_timestamps = []
        
        for point in data_points:
            try:
                timestamp = point['timestamp']
                data_timestamps.append(timestamp)
                data = json.loads(point['data'])
                if 'total_distance' in data:
                    distances.append((timestamp, data.get('total_distance')))
                if 'total_calories' in data or 'total_energy' in data:
                    calories.append((timestamp, data.get('total_calories') or data.get('total_energy')))
                if 'instantaneous_power' in data:
                    power_values.append((timestamp, data.get('instantaneous_power')))
                if 'heart_rate' in data:
                    heart_rate_values.append((timestamp, data.get('heart_rate')))
            except (json.JSONDecodeError, KeyError) as e:
                print(f"  Error parsing data point at timestamp {point['timestamp']}: {e}")
        
        # Analyze timestamps for gaps
        if len(data_timestamps) > 1:
            gaps = []
            avg_gap = 0
            max_gap = 0
            for i in range(1, len(data_timestamps)):
                gap = data_timestamps[i] - data_timestamps[i-1]
                avg_gap += gap
                max_gap = max(max_gap, gap)
                if gap > 10:  # More than 10 seconds between data points
                    gaps.append((i, gap))
            
            avg_gap /= len(data_timestamps) - 1
            print(f"  Data collection frequency: avg {avg_gap:.1f}s, max gap {max_gap}s")
            if gaps:
                print(f"  Found {len(gaps)} significant gaps (>10s) in data collection")
                for idx, gap_size in gaps[:3]:  # Show first 3 gaps
                    print(f"    Gap at point {idx}: {gap_size}s")
        
        # Check accumulation for distances
        has_distance_issues = False
        if distances:
            distances.sort(key=lambda x: x[0])  # Sort by timestamp
            dist_values = [d[1] for d in distances]
            is_accumulating = all(dist_values[i] >= dist_values[i-1] for i in range(1, len(dist_values)))
            total_increase = dist_values[-1] - dist_values[0] if dist_values else 0
            
            print(f"  Distance: {'ACCUMULATING' if is_accumulating else 'NOT ACCUMULATING'}")
            print(f"  Initial distance: {dist_values[0]}, Final distance: {dist_values[-1]}")
            print(f"  Total distance increase: {total_increase}")
            
            # Report issues
            if not is_accumulating:
                has_distance_issues = True
                decreases = [(i, dist_values[i-1], dist_values[i]) for i in range(1, len(dist_values)) if dist_values[i] < dist_values[i-1]]
                print(f"  Distance decreases detected at positions:")
                for pos, prev, curr in decreases[:5]:  # Show first 5 issues
                    print(f"    Position {pos}: {prev} → {curr} (decrease of {prev-curr})")
                if len(decreases) > 5:
                    print(f"    ... and {len(decreases)-5} more issues")
        else:
            print("  No distance data available")
        
        # Check accumulation for calories
        has_calorie_issues = False
        if calories:
            calories.sort(key=lambda x: x[0])  # Sort by timestamp
            cal_values = [c[1] for c in calories]
            is_accumulating = all(cal_values[i] >= cal_values[i-1] for i in range(1, len(cal_values)))
            total_increase = cal_values[-1] - cal_values[0] if cal_values else 0
            
            print(f"  Calories: {'ACCUMULATING' if is_accumulating else 'NOT ACCUMULATING'}")
            print(f"  Initial calories: {cal_values[0]}, Final calories: {cal_values[-1]}")
            print(f"  Total calorie increase: {total_increase}")
            
            # Report issues
            if not is_accumulating:
                has_calorie_issues = True
                decreases = [(i, cal_values[i-1], cal_values[i]) for i in range(1, len(cal_values)) if cal_values[i] < cal_values[i-1]]
                print(f"  Calorie decreases detected at positions:")
                for pos, prev, curr in decreases[:5]:  # Show first 5 issues
                    print(f"    Position {pos}: {prev} → {curr} (decrease of {prev-curr})")
                if len(decreases) > 5:
                    print(f"    ... and {len(decreases)-5} more issues")
        else:
            print("  No calorie data available")
        
        # Add to appropriate list
        if has_distance_issues or has_calorie_issues:
            problem_workouts.append(workout_id)
        else:
            good_workouts.append(workout_id)
    
    # Print summary
    print("\n======== Diagnostic Summary ========")
    print(f"Total workouts analyzed: {len(workouts)}")
    print(f"Workouts with no data points: {len(empty_workouts)} ({', '.join(map(str, empty_workouts))})")
    print(f"Workouts with accumulation issues: {len(problem_workouts)} ({', '.join(map(str, problem_workouts))})")
    print(f"Workouts with no issues: {len(good_workouts)}")
    
    conn.close()

if __name__ == "__main__":
    analyze_metric_accumulation()