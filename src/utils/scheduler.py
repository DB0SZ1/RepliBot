"""
Scheduler Utility
Human-like activity scheduling with randomization
"""

import random
import time
from datetime import datetime, timedelta
from typing import Callable, Optional, List, Dict
from zoneinfo import ZoneInfo
import json
from pathlib import Path
import threading

CONFIG_PATH = Path(__file__).parent.parent.parent / "config"


class Scheduler:
    """
    Human-like scheduling for bot actions.
    
    Features:
    - Random intervals (not exactly every hour)
    - Active hours enforcement (WAT timezone)
    - Weekend behavior adjustment
    - Natural gaps simulation
    """
    
    def __init__(self, timezone: str = "Africa/Lagos"):
        """
        Initialize scheduler.
        
        Args:
            timezone: Timezone for active hours (default WAT)
        """
        self.tz = ZoneInfo(timezone)
        self._stop_flag = threading.Event()
        self._last_action_time: Optional[datetime] = None
        
        # Load config
        config_file = CONFIG_PATH / "bot_config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.behavior = config.get("behavior", {})
        else:
            self.behavior = {}
        
        self.active_hours = self.behavior.get("active_hours", [6, 23])
        self.avoid_hours = self.behavior.get("avoid_hours", [0, 5])
    
    def get_current_time(self) -> datetime:
        """Get current time in configured timezone."""
        return datetime.now(self.tz)
    
    def is_active_hour(self) -> bool:
        """
        Check if current time is within active hours.
        
        Returns:
            True if bot should be active
        """
        now = self.get_current_time()
        hour = now.hour
        
        # Check avoid hours first
        if len(self.avoid_hours) >= 2:
            start_avoid, end_avoid = self.avoid_hours[0], self.avoid_hours[1]
            if start_avoid <= hour <= end_avoid:
                return False
        
        # Check active hours
        if len(self.active_hours) >= 2:
            start_active, end_active = self.active_hours[0], self.active_hours[1]
            return start_active <= hour <= end_active
        
        return True
    
    def is_weekend(self) -> bool:
        """Check if it's weekend."""
        now = self.get_current_time()
        return now.weekday() >= 5  # Saturday=5, Sunday=6
    
    def get_random_interval(
        self,
        min_minutes: int = 45,
        max_minutes: int = 90
    ) -> int:
        """
        Get random interval between actions.
        
        Args:
            min_minutes: Minimum wait time
            max_minutes: Maximum wait time
            
        Returns:
            Wait time in seconds
        """
        # Weekend = longer intervals
        if self.is_weekend():
            min_minutes = int(min_minutes * 1.5)
            max_minutes = int(max_minutes * 1.5)
        
        minutes = random.randint(min_minutes, max_minutes)
        # Add some seconds for more randomness
        seconds = random.randint(0, 59)
        
        return (minutes * 60) + seconds
    
    def get_response_delay(self) -> int:
        """
        Get human-like response delay (don't reply instantly).
        
        Returns:
            Delay in seconds
        """
        # 2-15 minutes, weighted towards shorter delays
        weights = [3, 3, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        minutes = random.choices(range(2, 16), weights=weights)[0]
        seconds = random.randint(0, 59)
        
        return (minutes * 60) + seconds
    
    def get_next_active_time(self) -> datetime:
        """
        Get next time when bot should be active.
        
        Returns:
            Datetime of next active period
        """
        now = self.get_current_time()
        
        if self.is_active_hour():
            return now
        
        # Find next active hour
        start_hour = self.active_hours[0] if self.active_hours else 6
        
        # If current hour is after end of active period, go to next day
        if now.hour >= self.active_hours[1] if len(self.active_hours) > 1 else 23:
            next_day = now + timedelta(days=1)
            return next_day.replace(
                hour=start_hour,
                minute=random.randint(0, 30),
                second=0,
                microsecond=0
            )
        
        # If before active period, wait until start
        return now.replace(
            hour=start_hour,
            minute=random.randint(0, 30),
            second=0,
            microsecond=0
        )
    
    def distribute_actions(self, total_actions: int = 17) -> List[datetime]:
        """
        Distribute actions throughout the active hours.
        
        Args:
            total_actions: Number of actions to distribute
            
        Returns:
            List of scheduled times
        """
        now = self.get_current_time()
        start_hour = self.active_hours[0] if self.active_hours else 6
        end_hour = self.active_hours[1] if len(self.active_hours) > 1 else 23
        
        # Today's window
        start_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_time = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        
        if now > start_time:
            start_time = now
        
        # Calculate total minutes available
        total_minutes = int((end_time - start_time).total_seconds() / 60)
        
        if total_minutes <= 0:
            return []
        
        # Distribute with randomness
        schedule = []
        avg_interval = total_minutes / total_actions
        
        current_time = start_time
        for i in range(total_actions):
            # Random offset from average
            offset = random.randint(int(-avg_interval * 0.3), int(avg_interval * 0.3))
            interval = max(10, int(avg_interval + offset))  # Min 10 minutes
            
            action_time = current_time + timedelta(minutes=interval)
            if action_time < end_time:
                schedule.append(action_time)
                current_time = action_time
        
        return schedule
    
    def wait_until(self, target_time: datetime) -> bool:
        """
        Wait until target time (can be interrupted).
        
        Args:
            target_time: Time to wait until
            
        Returns:
            True if completed, False if interrupted
        """
        while True:
            if self._stop_flag.is_set():
                return False
            
            now = self.get_current_time()
            if now >= target_time:
                return True
            
            # Sleep in small intervals to allow interruption
            remaining = (target_time - now).total_seconds()
            sleep_time = min(remaining, 30)  # Max 30 second sleep
            time.sleep(sleep_time)
    
    def sleep_random(
        self,
        min_seconds: int = 60,
        max_seconds: int = 300
    ) -> bool:
        """
        Sleep for a random duration.
        
        Args:
            min_seconds: Minimum sleep time
            max_seconds: Maximum sleep time
            
        Returns:
            True if completed, False if interrupted
        """
        sleep_time = random.randint(min_seconds, max_seconds)
        end_time = self.get_current_time() + timedelta(seconds=sleep_time)
        return self.wait_until(end_time)
    
    def stop(self) -> None:
        """Signal scheduler to stop."""
        self._stop_flag.set()
    
    def reset(self) -> None:
        """Reset stop flag."""
        self._stop_flag.clear()
    
    def run_loop(
        self,
        action_fn: Callable,
        min_interval: int = 45,
        max_interval: int = 90
    ) -> None:
        """
        Run action in loop with scheduling.
        
        Args:
            action_fn: Function to call each iteration
            min_interval: Min minutes between actions
            max_interval: Max minutes between actions
        """
        self.reset()
        
        while not self._stop_flag.is_set():
            # Wait for active hours
            if not self.is_active_hour():
                next_active = self.get_next_active_time()
                print(f"Outside active hours. Next active: {next_active.strftime('%H:%M')}")
                if not self.wait_until(next_active):
                    break
            
            # Execute action
            try:
                action_fn()
            except Exception as e:
                print(f"Action error: {e}")
            
            self._last_action_time = self.get_current_time()
            
            # Wait for next action
            interval = self.get_random_interval(min_interval, max_interval)
            print(f"Next action in {interval // 60} minutes...")
            
            end_time = self.get_current_time() + timedelta(seconds=interval)
            if not self.wait_until(end_time):
                break
    
    def get_time_until_next(self) -> Dict:
        """Get formatted time until next action window."""
        now = self.get_current_time()
        
        if self.is_active_hour():
            return {
                "active": True,
                "message": "Active now",
                "next_time": now
            }
        
        next_time = self.get_next_active_time()
        delta = next_time - now
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        
        return {
            "active": False,
            "message": f"Next active in {hours}h {minutes}m",
            "next_time": next_time
        }


# Test
if __name__ == "__main__":
    scheduler = Scheduler()
    
    print(f"Current time (WAT): {scheduler.get_current_time()}")
    print(f"Is active hour: {scheduler.is_active_hour()}")
    print(f"Is weekend: {scheduler.is_weekend()}")
    print(f"Random interval: {scheduler.get_random_interval()} seconds")
    print(f"Response delay: {scheduler.get_response_delay()} seconds")
    print(f"\nNext active: {scheduler.get_time_until_next()}")
    
    print("\nSample schedule for 17 actions:")
    schedule = scheduler.distribute_actions(17)
    for i, t in enumerate(schedule, 1):
        print(f"  {i:2}. {t.strftime('%H:%M:%S')}")
