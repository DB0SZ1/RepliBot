"""
Post Collector
Collects and stores posts from target accounts for learning.
Runs continuously without intervention.
"""

import json
import time
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from threading import Thread, Event

CONFIG_PATH = Path(__file__).parent.parent.parent / "config"
DATA_PATH = Path(__file__).parent.parent.parent / "data"


class PostCollector:
    """
    Collects posts from target accounts for style learning.
    
    Runs continuously in background, collecting and analyzing posts.
    """
    
    def __init__(self, x_client=None, openrouter_client=None):
        """
        Initialize collector.
        
        Args:
            x_client: X API client instance
            openrouter_client: OpenRouter client for analysis
        """
        self.x_client = x_client
        self.ai_client = openrouter_client
        
        # Load configs
        self._load_config()
        
        # Data storage
        DATA_PATH.mkdir(parents=True, exist_ok=True)
        self.posts_file = DATA_PATH / "posts.json"
        self.posts = self._load_posts()
        
        # Control flags
        self._stop_event = Event()
        self._collection_thread: Optional[Thread] = None
    
    def _load_config(self) -> None:
        """Load configuration files."""
        # Target accounts
        accounts_file = CONFIG_PATH / "accounts_to_learn.json"
        if accounts_file.exists():
            with open(accounts_file, 'r') as f:
                self.targets_config = json.load(f)
        else:
            self.targets_config = {"target_accounts": [], "hashtags_to_monitor": []}
        
        # Bot config
        bot_config_file = CONFIG_PATH / "bot_config.json"
        if bot_config_file.exists():
            with open(bot_config_file, 'r') as f:
                config = json.load(f)
                self.learning_config = config.get("learning", {})
        else:
            self.learning_config = {}
    
    def _load_posts(self) -> Dict:
        """Load collected posts from disk."""
        if self.posts_file.exists():
            try:
                with open(self.posts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        
        return {
            "accounts": {},
            "hashtags": {},
            "timeline": [],
            "metadata": {
                "last_collection": None,
                "total_posts": 0,
                "started": datetime.now().isoformat(),
                "account_index": 0,
                "hashtag_index": 0
            }
        }
    
    def _save_posts(self) -> None:
        """Save collected posts to disk."""
        self.posts["metadata"]["last_collection"] = datetime.now().isoformat()
        # Ensure indices exist
        if "account_index" not in self.posts["metadata"]:
            self.posts["metadata"]["account_index"] = 0
        if "hashtag_index" not in self.posts["metadata"]:
            self.posts["metadata"]["hashtag_index"] = 0
            
        self.posts["metadata"]["total_posts"] = sum(
            len(posts) for posts in self.posts["accounts"].values()
        ) + len(self.posts["timeline"])
        
        with open(self.posts_file, 'w', encoding='utf-8') as f:
            json.dump(self.posts, f, indent=2, ensure_ascii=False, default=str)
    
    def collect_from_account(self, username: str, max_posts: int = 100) -> List[Dict]:
        """
        Collect posts from a specific account.
        
        Args:
            username: X username (without @)
            max_posts: Maximum posts to collect
            
        Returns:
            List of collected post dicts
        """
        if not self.x_client:
            print(f"[!] No X client available")
            return []
        
        username = username.lstrip("@")
        print(f"[*] Collecting posts from @{username}...")
        
        try:
            tweets = self.x_client.get_user_tweets(
                username=username,
                max_results=min(max_posts, 100)
            )
            
            if not tweets:
                print(f"[!] No tweets found for @{username}")
                return []
            
            # Store in posts dict
            if username not in self.posts["accounts"]:
                self.posts["accounts"][username] = []
            
            # Avoid duplicates
            existing_ids = {p["id"] for p in self.posts["accounts"][username]}
            new_posts = [t for t in tweets if t["id"] not in existing_ids]
            
            self.posts["accounts"][username].extend(new_posts)
            
            # Keep max posts per account
            max_per_account = self.learning_config.get("max_posts_per_account", 500)
            if len(self.posts["accounts"][username]) > max_per_account:
                # Keep most recent
                self.posts["accounts"][username] = sorted(
                    self.posts["accounts"][username],
                    key=lambda x: x.get("created_at", ""),
                    reverse=True
                )[:max_per_account]
            
            self._save_posts()
            print(f"[+] Collected {len(new_posts)} new posts from @{username}")
            
            return new_posts
            
        except Exception as e:
            print(f"[!] Error collecting from @{username}: {e}")
            return []
    
    def collect_from_hashtag(self, hashtag: str, max_posts: int = 50) -> List[Dict]:
        """
        Collect posts with a specific hashtag.
        
        Args:
            hashtag: Hashtag (with or without #)
            max_posts: Maximum posts to collect
            
        Returns:
            List of collected post dicts
        """
        if not self.x_client:
            return []
        
        hashtag = hashtag.lstrip("#")
        print(f"[*] Collecting posts with #{hashtag}...")
        
        try:
            tweets = self.x_client.search_tweets(
                query=f"#{hashtag}",
                max_results=min(max_posts, 100)
            )
            
            if not tweets:
                return []
            
            # Store
            if hashtag not in self.posts["hashtags"]:
                self.posts["hashtags"][hashtag] = []
            
            existing_ids = {p["id"] for p in self.posts["hashtags"][hashtag]}
            new_posts = [t for t in tweets if t["id"] not in existing_ids]
            
            self.posts["hashtags"][hashtag].extend(new_posts)
            self._save_posts()
            
            print(f"[+] Collected {len(new_posts)} posts with #{hashtag}")
            return new_posts
            
        except Exception as e:
            print(f"[!] Error collecting #{hashtag}: {e}")
            return []
    
    def collect_timeline(self, max_posts: int = 50) -> List[Dict]:
        """
        Collect posts from timeline.
        
        Args:
            max_posts: Maximum posts to collect
            
        Returns:
            List of collected post dicts
        """
        if not self.x_client:
            return []
        
        print(f"[*] Collecting timeline posts...")
        
        try:
            tweets = self.x_client.get_timeline(max_results=max_posts)
            
            if not tweets:
                return []
            
            existing_ids = {p["id"] for p in self.posts["timeline"]}
            new_posts = [t for t in tweets if t["id"] not in existing_ids]
            
            self.posts["timeline"].extend(new_posts)
            
            # Keep max 1000 timeline posts
            if len(self.posts["timeline"]) > 1000:
                self.posts["timeline"] = self.posts["timeline"][-1000:]
            
            self._save_posts()
            
            print(f"[+] Collected {len(new_posts)} timeline posts")
            return new_posts
            
        except Exception as e:
            print(f"[!] Error collecting timeline: {e}")
            return []
    
    def collect_next_batch(self) -> Dict:
        """
        Collect from NEXT target account and hashtags (Rotation).
        Respects strict FREE TIER limits (1 call / 15 min).
        
        Returns:
            Summary of collection results
        """
        results = {
            "accounts": {},
            "hashtags": {},
            "timeline": 0,
            "total_new": 0
        }
        
        # 1. Accounts Rotation
        target_accounts = self.targets_config.get("target_accounts", [])
        if target_accounts:
            current_idx = self.posts["metadata"].get("account_index", 0)
            if current_idx >= len(target_accounts):
                current_idx = 0
            
            target = target_accounts[current_idx]
            username = target.get("username", "").lstrip("@")
            
            if username:
                posts = self.collect_from_account(username)
                results["accounts"][username] = len(posts)
                results["total_new"] += len(posts)
            
            # Increment for next time
            self.posts["metadata"]["account_index"] = (current_idx + 1) % len(target_accounts)
            time.sleep(2) # Short pause
        
        # 2. Hashtags Rotation
        target_hashtags = self.targets_config.get("hashtags_to_monitor", [])
        if target_hashtags:
            current_idx = self.posts["metadata"].get("hashtag_index", 0)
            if current_idx >= len(target_hashtags):
                current_idx = 0
            
            hashtag = target_hashtags[current_idx]
            clean_tag = hashtag.lstrip("#")
            
            posts = self.collect_from_hashtag(clean_tag)
            results["hashtags"][clean_tag] = len(posts)
            results["total_new"] += len(posts)
            
            # Increment
            self.posts["metadata"]["hashtag_index"] = (current_idx + 1) % len(target_hashtags)
        
        # 3. Timeline (Always collect if possible, or rotate this too if strict limits needed)
        # Note: Timeline is its own endpoint limit, so we can try it every time 
        # as long as we respect its specific 15 min limit.
        timeline_posts = self.collect_timeline()
        results["timeline"] = len(timeline_posts)
        results["total_new"] += len(timeline_posts)
        
        self._save_posts()
        return results
    
    def _collection_loop(self) -> None:
        """Internal collection loop for background operation."""
        interval_minutes = self.learning_config.get("collect_interval_minutes", 30)
        
        while not self._stop_event.is_set():
            print(f"\n{'='*50}")
            print(f"[COLLECTOR] Starting collection cycle...")
            print(f"{'='*50}")
            
            try:
                results = self.collect_next_batch()
                print(f"\n[COLLECTOR] Cycle complete:")
                print(f"  - Total new posts: {results['total_new']}")
                print(f"  - Total stored: {self.posts['metadata']['total_posts']}")
            except Exception as e:
                print(f"[!] Collection error: {e}")
            
            # Wait for next cycle
            wait_seconds = interval_minutes * 60
            # Add some randomness
            wait_seconds += random.randint(-60, 60)
            
            print(f"[COLLECTOR] Next collection in {wait_seconds // 60} minutes...")
            
            # Sleep in chunks to allow stopping
            for _ in range(wait_seconds // 10):
                if self._stop_event.is_set():
                    break
                time.sleep(10)
    
    def start_continuous(self) -> None:
        """Start continuous collection in background thread."""
        if self._collection_thread and self._collection_thread.is_alive():
            print("[!] Collection already running")
            return
        
        self._stop_event.clear()
        self._collection_thread = Thread(
            target=self._collection_loop,
            daemon=True,
            name="PostCollector"
        )
        self._collection_thread.start()
        print("[+] Continuous collection started")
    
    def stop_continuous(self) -> None:
        """Stop continuous collection."""
        self._stop_event.set()
        if self._collection_thread:
            self._collection_thread.join(timeout=5)
        print("[*] Collection stopped")
    
    def get_posts_for_account(self, username: str) -> List[Dict]:
        """Get all stored posts for an account."""
        username = username.lstrip("@")
        return self.posts["accounts"].get(username, [])
    
    def get_all_post_texts(self) -> List[str]:
        """Get all post texts for analysis."""
        texts = []
        
        for account_posts in self.posts["accounts"].values():
            texts.extend([p.get("text", "") for p in account_posts])
        
        for hashtag_posts in self.posts["hashtags"].values():
            texts.extend([p.get("text", "") for p in hashtag_posts])
        
        return [t for t in texts if t]  # Filter empty
    
    def get_high_engagement_posts(self, min_likes: int = 10) -> List[Dict]:
        """Get posts with high engagement for learning."""
        high_engagement = []
        
        for account_posts in self.posts["accounts"].values():
            for post in account_posts:
                metrics = post.get("metrics", {})
                if metrics.get("like_count", 0) >= min_likes:
                    high_engagement.append(post)
        
        return sorted(
            high_engagement,
            key=lambda x: x.get("metrics", {}).get("like_count", 0),
            reverse=True
        )
    
    def get_stats(self) -> Dict:
        """Get collection statistics."""
        return {
            "total_posts": self.posts["metadata"]["total_posts"],
            "accounts_tracked": len(self.posts["accounts"]),
            "hashtags_tracked": len(self.posts["hashtags"]),
            "timeline_posts": len(self.posts["timeline"]),
            "last_collection": self.posts["metadata"]["last_collection"],
            "started": self.posts["metadata"]["started"]
        }


# Test
if __name__ == "__main__":
    collector = PostCollector()
    print("Post Collector Stats:")
    print(json.dumps(collector.get_stats(), indent=2))
