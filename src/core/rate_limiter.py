"""
Rate Limiter for X API Free Tier
Enforces ALL free tier limits - both read and write.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import threading
import time


DATA_PATH = Path(__file__).parent.parent.parent / "data"


class RateLimiter:
    """
    Tracks and enforces X API rate limits for FREE tier.
    
    FREE TIER LIMITS (from X API docs):
    
    WRITE LIMITS (per 24 hours):
    - POST /2/tweets: 17/day per user AND per app
    
    READ LIMITS (per 15 minutes):
    - GET /2/tweets: 1/15min
    - GET /2/tweets/:id: 1/15min
    - GET /2/users/:id/mentions: 1/15min
    - GET /2/users/:id/timelines/reverse_chronological: 1/15min
    - GET /2/users/:id/tweets: 1/15min
    - GET /2/tweets/search/recent: 1/15min
    - GET /2/users/by/username/:username: 3/15min
    
    READ LIMITS (per 24 hours):
    - GET /2/users/me: 25/day
    - GET /2/users/:id: 1/day
    """
    
    # Write limits (per 24 hours)
    DAILY_POST_LIMIT = 17
    
    # Read limits (per 15 minutes)
    READ_LIMITS_15MIN = {
        "get_tweets": 1,
        "get_tweet": 1,
        "get_mentions": 1,
        "get_timeline": 1,
        "get_user_tweets": 1,
        "search_tweets": 1,
        "get_user_by_username": 3,
    }
    
    # Read limits (per 24 hours)
    READ_LIMITS_24H = {
        "get_me": 25,
        "get_user": 1,
    }
    
    def __init__(self, data_path: Optional[Path] = None):
        """Initialize rate limiter."""
        self.data_path = data_path or DATA_PATH
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.log_file = self.data_path / "rate_limits.json"
        self._lock = threading.Lock()
        self._load_log()
    
    def _load_log(self) -> None:
        """Load rate limit log from disk."""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    self.log = json.load(f)
            except json.JSONDecodeError:
                self.log = self._empty_log()
        else:
            self.log = self._empty_log()
        
        self._cleanup_old_entries()
    
    def _empty_log(self) -> Dict:
        """Create empty log structure."""
        return {
            "posts": [],  # Write actions
            "reads": {},  # Read actions by type
            "metadata": {
                "created": datetime.now().isoformat(),
                "last_update": None
            }
        }
    
    def _save_log(self) -> None:
        """Save log to disk."""
        self.log["metadata"]["last_update"] = datetime.now().isoformat()
        with open(self.log_file, 'w') as f:
            json.dump(self.log, f, indent=2, default=str)
    
    def _cleanup_old_entries(self) -> None:
        """Remove entries older than 25 hours."""
        cutoff = datetime.now() - timedelta(hours=25)
        
        # Clean posts
        self.log["posts"] = [
            p for p in self.log["posts"]
            if datetime.fromisoformat(p["timestamp"]) > cutoff
        ]
        
        # Clean reads
        for action_type in list(self.log.get("reads", {}).keys()):
            self.log["reads"][action_type] = [
                r for r in self.log["reads"][action_type]
                if datetime.fromisoformat(r) > cutoff
            ]
            # Remove empty lists
            if not self.log["reads"][action_type]:
                del self.log["reads"][action_type]
        
        self._save_log()
    
    # ==================== WRITE LIMITS ====================
    
    def _get_today_posts(self) -> list:
        """Get posts from last 24 hours."""
        cutoff = datetime.now() - timedelta(hours=24)
        return [
            p for p in self.log["posts"]
            if datetime.fromisoformat(p["timestamp"]) > cutoff
        ]
    
    def can_post(self) -> bool:
        """Check if we can post (17/day limit)."""
        return len(self._get_today_posts()) < self.DAILY_POST_LIMIT
    
    def record_post(
        self,
        action_type: str = "post",
        tweet_id: Optional[str] = None,
        target_id: Optional[str] = None,
        content: Optional[str] = None,
        success: bool = True
    ) -> bool:
        """Record a write action (post/reply/quote)."""
        with self._lock:
            self.log["posts"].append({
                "timestamp": datetime.now().isoformat(),
                "type": action_type,
                "tweet_id": tweet_id,
                "target_id": target_id,
                "content": content[:100] if content else None,
                "success": success
            })
            self._save_log()
            return True
    
    def get_posts_remaining(self) -> int:
        """Get remaining posts for today."""
        return max(0, self.DAILY_POST_LIMIT - len(self._get_today_posts()))
    
    def get_next_post_time(self) -> Optional[datetime]:
        """Get when next post will be available."""
        if self.can_post():
            return None  # Can post now
        
        # Find oldest post and when it expires
        posts = self._get_today_posts()
        if not posts:
            return None
        
        oldest = min(datetime.fromisoformat(p["timestamp"]) for p in posts)
        return oldest + timedelta(hours=24)
    
    # ==================== READ LIMITS ====================
    
    def _get_reads_15min(self, action_type: str) -> list:
        """Get reads of type from last 15 minutes."""
        cutoff = datetime.now() - timedelta(minutes=15)
        reads = self.log.get("reads", {}).get(action_type, [])
        return [r for r in reads if datetime.fromisoformat(r) > cutoff]
    
    def _get_reads_24h(self, action_type: str) -> list:
        """Get reads of type from last 24 hours."""
        cutoff = datetime.now() - timedelta(hours=24)
        reads = self.log.get("reads", {}).get(action_type, [])
        return [r for r in reads if datetime.fromisoformat(r) > cutoff]
    
    def can_read(self, action_type: str) -> bool:
        """
        Check if a read action is allowed.
        
        Args:
            action_type: Type of read action
            
        Returns:
            True if action is allowed
        """
        # Check 15-minute limits
        if action_type in self.READ_LIMITS_15MIN:
            limit = self.READ_LIMITS_15MIN[action_type]
            count = len(self._get_reads_15min(action_type))
            return count < limit
        
        # Check 24-hour limits
        if action_type in self.READ_LIMITS_24H:
            limit = self.READ_LIMITS_24H[action_type]
            count = len(self._get_reads_24h(action_type))
            return count < limit
        
        # Unknown action type - allow but warn
        return True
    
    def record_read(self, action_type: str) -> None:
        """Record a read action."""
        with self._lock:
            if "reads" not in self.log:
                self.log["reads"] = {}
            if action_type not in self.log["reads"]:
                self.log["reads"][action_type] = []
            
            self.log["reads"][action_type].append(datetime.now().isoformat())
            self._save_log()
    
    def get_read_wait_time(self, action_type: str) -> int:
        """
        Get seconds to wait before action is allowed.
        
        Args:
            action_type: Type of read action
            
        Returns:
            Seconds to wait (0 if allowed now)
        """
        if self.can_read(action_type):
            return 0
        
        # Find oldest entry for this action
        if action_type in self.READ_LIMITS_15MIN:
            reads = self._get_reads_15min(action_type)
            if not reads:
                return 0
            oldest = min(datetime.fromisoformat(r) for r in reads)
            next_available = oldest + timedelta(minutes=15)
        elif action_type in self.READ_LIMITS_24H:
            reads = self._get_reads_24h(action_type)
            if not reads:
                return 0
            oldest = min(datetime.fromisoformat(r) for r in reads)
            next_available = oldest + timedelta(hours=24)
        else:
            return 0
        
        wait = (next_available - datetime.now()).total_seconds()
        return max(0, int(wait))
    
    def wait_for_read(self, action_type: str, max_wait: int = 900) -> bool:
        """
        Wait until read action is allowed.
        
        Args:
            action_type: Type of read action
            max_wait: Maximum seconds to wait
            
        Returns:
            True if action is now allowed
        """
        wait_time = self.get_read_wait_time(action_type)
        
        if wait_time == 0:
            return True
        
        if wait_time > max_wait:
            print(f"[RATE LIMIT] {action_type}: Would need to wait {wait_time}s (max {max_wait}s)")
            return False
        
        print(f"[RATE LIMIT] {action_type}: Waiting {wait_time}s...")
        time.sleep(wait_time)
        return True
    
    # ==================== COMBINED STATUS ====================
    
    def get_usage(self) -> Dict:
        """Get current usage stats."""
        posts = self._get_today_posts()
        
        read_status = {}
        for action_type, limit in self.READ_LIMITS_15MIN.items():
            count = len(self._get_reads_15min(action_type))
            wait = self.get_read_wait_time(action_type)
            read_status[action_type] = {
                "used": count,
                "limit": limit,
                "remaining": max(0, limit - count),
                "wait_seconds": wait,
                "period": "15min"
            }
        
        for action_type, limit in self.READ_LIMITS_24H.items():
            count = len(self._get_reads_24h(action_type))
            wait = self.get_read_wait_time(action_type)
            read_status[action_type] = {
                "used": count,
                "limit": limit,
                "remaining": max(0, limit - count),
                "wait_seconds": wait,
                "period": "24h"
            }
        
        return {
            "posts": {
                "used": len(posts),
                "limit": self.DAILY_POST_LIMIT,
                "remaining": self.get_posts_remaining(),
                "can_post": self.can_post()
            },
            "reads": read_status,
            "can_act": self.can_post()
        }
    
    def display_status(self) -> str:
        """Get formatted status string for display."""
        usage = self.get_usage()
        posts = usage["posts"]
        
        lines = [
            "╔════════════════════════════════════════════════════╗",
            "║           X API FREE TIER - RATE LIMITS            ║",
            "╠════════════════════════════════════════════════════╣",
            f"║ POSTS (24h): {posts['used']:2}/{posts['limit']}  │  Remaining: {posts['remaining']:2}              ║",
            "╠────────────────────────────────────────────────────╣",
            "║ READS (per 15min):                                 ║",
        ]
        
        for action, data in usage["reads"].items():
            if data["period"] == "15min":
                wait = f"wait {data['wait_seconds']}s" if data['wait_seconds'] > 0 else "ready"
                lines.append(f"║   {action:20} {data['used']}/{data['limit']}  ({wait:12}) ║")
        
        lines.append("╠────────────────────────────────────────────────────╣")
        lines.append("║ READS (per 24h):                                   ║")
        
        for action, data in usage["reads"].items():
            if data["period"] == "24h":
                lines.append(f"║   {action:20} {data['used']}/{data['limit']}  remaining: {data['remaining']:2}     ║")
        
        lines.append("╠────────────────────────────────────────────────────╣")
        
        if posts["can_post"]:
            lines.append("║ Status: ✓ READY TO POST                           ║")
        else:
            next_time = self.get_next_post_time()
            if next_time:
                lines.append(f"║ Status: ✗ POST LIMIT HIT                          ║")
                lines.append(f"║ Next post: {next_time.strftime('%Y-%m-%d %H:%M')}                       ║")
        
        lines.append("╚════════════════════════════════════════════════════╝")
        
        return "\n".join(lines)
    
    # ==================== LEGACY COMPATIBILITY ====================
    
    def can_act(self, action_type: str = "post") -> bool:
        """Legacy method - check if action is allowed."""
        if action_type in ["post", "reply", "quote"]:
            return self.can_post()
        return self.can_read(action_type)
    
    def record_action(
        self,
        action_type: str,
        tweet_id: Optional[str] = None,
        target_id: Optional[str] = None,
        content: Optional[str] = None,
        success: bool = True
    ) -> bool:
        """Legacy method - record an action."""
        return self.record_post(action_type, tweet_id, target_id, content, success)
    
    def get_recent_actions(self, limit: int = 10) -> list:
        """Get most recent write actions."""
        return sorted(
            self.log["posts"],
            key=lambda x: x["timestamp"],
            reverse=True
        )[:limit]
    
    def get_next_available_time(self) -> Optional[datetime]:
        """Get when next post will be available."""
        return self.get_next_post_time()


# Test
if __name__ == "__main__":
    limiter = RateLimiter()
    print(limiter.display_status())
    
    print("\nTesting read limits:")
    for action in ["get_timeline", "get_mentions", "search_tweets", "get_me"]:
        print(f"  {action}: can_read={limiter.can_read(action)}, wait={limiter.get_read_wait_time(action)}s")
