"""
X (Twitter) API Client
Handles all X API interactions with FREE TIER rate limit awareness.

FREE TIER LIMITS (strictly enforced):
- POST tweets: 17/day 
- GET timeline: 1/15min
- GET mentions: 1/15min
- GET search: 1/15min
- GET user tweets: 1/15min
- GET user by username: 3/15min
"""

import os
import json
import tweepy
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

# Load credentials
CONFIG_PATH = Path(__file__).parent.parent.parent / "config"

# Import rate limiter
from .rate_limiter import RateLimiter


class XClient:
    """
    X API wrapper with FREE TIER rate limit awareness.
    
    All read methods check rate limits before calling API.
    """
    
    def __init__(self, credentials_path: Optional[str] = None, rate_limiter: Optional[RateLimiter] = None):
        """Initialize X client with credentials."""
        if credentials_path:
            creds_file = Path(credentials_path)
        else:
            creds_file = CONFIG_PATH / "x_credentials.json"
        
        # Try loading from file, fall back to env vars
        if creds_file.exists():
            with open(creds_file, 'r') as f:
                creds = json.load(f)
        else:
            creds = {
                "api_key": os.getenv("X_API_KEY"),
                "api_secret": os.getenv("X_API_SECRET"),
                "bearer_token": os.getenv("X_BEARER_TOKEN"),
                "access_token": os.getenv("X_ACCESS_TOKEN"),
                "access_token_secret": os.getenv("X_ACCESS_TOKEN_SECRET")
            }
        
        self._validate_credentials(creds)
        
        # Initialize tweepy clients
        self.bearer_token = creds.get("bearer_token")
        
        # Client for v2 API - DON'T auto wait, we handle it ourselves
        self.client = tweepy.Client(
            consumer_key=creds["api_key"],
            consumer_secret=creds["api_secret"],
            access_token=creds["access_token"],
            access_token_secret=creds["access_token_secret"],
            bearer_token=self.bearer_token,
            wait_on_rate_limit=False  # We handle rate limits manually
        )
        
        # Auth for v1.1 API (some features still need it)
        auth = tweepy.OAuth1UserHandler(
            creds["api_key"],
            creds["api_secret"],
            creds["access_token"],
            creds["access_token_secret"]
        )
        self.api = tweepy.API(auth, wait_on_rate_limit=False)
        
        # Rate limiter
        self.limiter = rate_limiter or RateLimiter()
        
        self._me = None
        self._me_fetched = False
    
    def _validate_credentials(self, creds: Dict) -> None:
        """Validate that all required credentials exist."""
        required = ["api_key", "api_secret", "access_token", "access_token_secret"]
        missing = [k for k in required if not creds.get(k)]
        if missing:
            raise ValueError(f"Missing X credentials: {missing}")
    
    @property
    def me(self) -> Dict:
        """Get authenticated user info (cached, uses 1/25 daily limit)."""
        if self._me is None and not self._me_fetched:
            if not self.limiter.can_read("get_me"):
                wait = self.limiter.get_read_wait_time("get_me")
                print(f"[X CLIENT] get_me rate limited. Wait: {wait}s")
                # Return placeholder
                return type('User', (), {'id': None, 'username': 'rate_limited'})()
            
            response = self.client.get_me(
                user_fields=["id", "name", "username", "description", "public_metrics"]
            )
            self._me = response.data
            self._me_fetched = True
            self.limiter.record_read("get_me")
        return self._me
    
    # ==================== WRITE ACTIONS ====================
    
    def post_tweet(self, text: str, dry_run: bool = False) -> Optional[Dict]:
        """
        Create a new tweet.
        
        Args:
            text: Tweet content (max 280 chars)
            dry_run: If True, don't actually post
            
        Returns:
            Tweet data dict or None if dry_run
        """
        if len(text) > 280:
            text = text[:277] + "..."
        
        if dry_run:
            return {"id": "dry_run", "text": text, "created_at": datetime.now().isoformat()}
        
        if not self.limiter.can_post():
            print("[X CLIENT] Post limit reached (17/day)")
            return None
        
        response = self.client.create_tweet(text=text)
        self.limiter.record_post("post", tweet_id=str(response.data["id"]), content=text)
        return {"id": response.data["id"], "text": text}
    
    def reply_to_tweet(self, tweet_id: str, text: str, dry_run: bool = False) -> Optional[Dict]:
        """
        Reply to an existing tweet.
        
        Args:
            tweet_id: ID of tweet to reply to
            text: Reply content
            dry_run: If True, don't actually reply
            
        Returns:
            Reply tweet data or None
        """
        if len(text) > 280:
            text = text[:277] + "..."
        
        if dry_run:
            return {"id": "dry_run", "text": text, "in_reply_to": tweet_id}
        
        if not self.limiter.can_post():
            print("[X CLIENT] Post limit reached (17/day)")
            return None
        
        response = self.client.create_tweet(
            text=text,
            in_reply_to_tweet_id=tweet_id
        )
        self.limiter.record_post("reply", tweet_id=str(response.data["id"]), target_id=tweet_id, content=text)
        return {"id": response.data["id"], "text": text, "in_reply_to": tweet_id}
    
    def quote_tweet(self, tweet_id: str, text: str, dry_run: bool = False) -> Optional[Dict]:
        """
        Quote retweet a tweet.
        
        Args:
            tweet_id: ID of tweet to quote
            text: Quote text
            dry_run: If True, don't actually quote
            
        Returns:
            Quote tweet data or None
        """
        if len(text) > 280:
            text = text[:277] + "..."
        
        if dry_run:
            return {"id": "dry_run", "text": text, "quoted_tweet": tweet_id}
        
        if not self.limiter.can_post():
            print("[X CLIENT] Post limit reached (17/day)")
            return None
        
        response = self.client.create_tweet(
            text=text,
            quote_tweet_id=tweet_id
        )
        self.limiter.record_post("quote", tweet_id=str(response.data["id"]), target_id=tweet_id, content=text)
        return {"id": response.data["id"], "text": text, "quoted_tweet": tweet_id}
    
    # ==================== READ ACTIONS (RATE LIMITED) ====================
    
    def get_user_id(self, username: str, wait: bool = True) -> Optional[str]:
        """
        Get user ID from username.
        
        FREE TIER: 3/15min
        """
        username = username.lstrip("@")
        
        if not self.limiter.can_read("get_user_by_username"):
            if wait:
                if not self.limiter.wait_for_read("get_user_by_username"):
                    return None
            else:
                print(f"[X CLIENT] get_user_by_username rate limited")
                return None
        
        try:
            response = self.client.get_user(username=username)
            self.limiter.record_read("get_user_by_username")
            return str(response.data.id) if response.data else None
        except tweepy.TooManyRequests:
            print(f"[X CLIENT] Rate limited on get_user for @{username}")
            return None
        except Exception as e:
            print(f"Error getting user ID for @{username}: {e}")
            return None
    
    def get_user_tweets(
        self, 
        username: str, 
        max_results: int = 10,  # Reduced default for free tier
        include_replies: bool = False,
        wait: bool = True
    ) -> List[Dict]:
        """
        Get tweets from a specific user.
        
        FREE TIER: 1/15min
        
        Args:
            username: Twitter username (without @)
            max_results: Max tweets to fetch (10 default for free tier)
            include_replies: Whether to include replies
            wait: Wait for rate limit if needed
            
        Returns:
            List of tweet dicts
        """
        # Check rate limit for username lookup
        user_id = self.get_user_id(username, wait=wait)
        if not user_id:
            return []
        
        # Check rate limit for user tweets
        if not self.limiter.can_read("get_user_tweets"):
            if wait:
                if not self.limiter.wait_for_read("get_user_tweets"):
                    return []
            else:
                print(f"[X CLIENT] get_user_tweets rate limited")
                return []
        
        exclude = [] if include_replies else ["replies"]
        
        try:
            response = self.client.get_users_tweets(
                id=user_id,
                max_results=min(max_results, 10),  # Free tier max is 10
                exclude=exclude,
                tweet_fields=["created_at", "public_metrics", "conversation_id", "text"],
                expansions=["author_id"]
            )
            self.limiter.record_read("get_user_tweets")
            
            if not response.data:
                return []
            
            tweets = []
            for tweet in response.data:
                tweets.append({
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                    "metrics": dict(tweet.public_metrics) if tweet.public_metrics else {},
                    "author_id": str(tweet.author_id),
                    "author_username": username
                })
            
            return tweets
            
        except tweepy.TooManyRequests:
            print(f"[X CLIENT] Rate limited on user tweets for @{username}")
            return []
        except Exception as e:
            print(f"Error fetching tweets for @{username}: {e}")
            return []
    
    def get_timeline(self, max_results: int = 10, wait: bool = True) -> List[Dict]:
        """
        Get home timeline tweets.
        
        FREE TIER: 1/15min
        
        Args:
            max_results: Max tweets to fetch (10 default for free tier)
            wait: Wait for rate limit if needed
            
        Returns:
            List of tweet dicts
        """
        if not self.limiter.can_read("get_timeline"):
            if wait:
                if not self.limiter.wait_for_read("get_timeline"):
                    return []
            else:
                print(f"[X CLIENT] get_timeline rate limited")
                return []
        
        try:
            response = self.client.get_home_timeline(
                max_results=min(max_results, 10),  # Free tier - small batches
                tweet_fields=["created_at", "public_metrics", "author_id", "conversation_id"],
                expansions=["author_id"],
                user_fields=["username", "public_metrics"]
            )
            self.limiter.record_read("get_timeline")
            
            if not response.data:
                return []
            
            # Build user lookup
            users = {}
            if response.includes and "users" in response.includes:
                for user in response.includes["users"]:
                    users[str(user.id)] = {
                        "username": user.username,
                        "followers": user.public_metrics.get("followers_count", 0) if user.public_metrics else 0
                    }
            
            tweets = []
            for tweet in response.data:
                author = users.get(str(tweet.author_id), {})
                tweets.append({
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                    "metrics": dict(tweet.public_metrics) if tweet.public_metrics else {},
                    "author_id": str(tweet.author_id),
                    "author_username": author.get("username"),
                    "author_followers": author.get("followers", 0)
                })
            
            return tweets
            
        except tweepy.TooManyRequests:
            print(f"[X CLIENT] Rate limited on timeline")
            return []
        except Exception as e:
            print(f"Error fetching timeline: {e}")
            return []
    
    def search_tweets(
        self, 
        query: str, 
        max_results: int = 10,
        sort_order: str = "relevancy",
        wait: bool = True
    ) -> List[Dict]:
        """
        Search for tweets.
        
        FREE TIER: 1/15min
        
        Args:
            query: Search query
            max_results: Max tweets to fetch
            sort_order: 'relevancy' or 'recency'
            wait: Wait for rate limit if needed
            
        Returns:
            List of tweet dicts
        """
        if not self.limiter.can_read("search_tweets"):
            if wait:
                if not self.limiter.wait_for_read("search_tweets"):
                    return []
            else:
                print(f"[X CLIENT] search_tweets rate limited")
                return []
        
        try:
            response = self.client.search_recent_tweets(
                query=query,
                max_results=min(max_results, 10),  # Free tier
                sort_order=sort_order,
                tweet_fields=["created_at", "public_metrics", "author_id"],
                expansions=["author_id"],
                user_fields=["username", "public_metrics"]
            )
            self.limiter.record_read("search_tweets")
            
            if not response.data:
                return []
            
            # Build user lookup
            users = {}
            if response.includes and "users" in response.includes:
                for user in response.includes["users"]:
                    users[str(user.id)] = {
                        "username": user.username,
                        "followers": user.public_metrics.get("followers_count", 0) if user.public_metrics else 0
                    }
            
            tweets = []
            for tweet in response.data:
                author = users.get(str(tweet.author_id), {})
                tweets.append({
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                    "metrics": dict(tweet.public_metrics) if tweet.public_metrics else {},
                    "author_id": str(tweet.author_id),
                    "author_username": author.get("username"),
                    "author_followers": author.get("followers", 0)
                })
            
            return tweets
            
        except tweepy.TooManyRequests:
            print(f"[X CLIENT] Rate limited on search")
            return []
        except Exception as e:
            print(f"Error searching tweets: {e}")
            return []
    
    def get_tweet(self, tweet_id: str, wait: bool = True) -> Optional[Dict]:
        """
        Get a single tweet by ID.
        
        FREE TIER: 1/15min
        """
        if not self.limiter.can_read("get_tweet"):
            if wait:
                if not self.limiter.wait_for_read("get_tweet"):
                    return None
            else:
                print(f"[X CLIENT] get_tweet rate limited")
                return None
        
        try:
            response = self.client.get_tweet(
                id=tweet_id,
                tweet_fields=["created_at", "public_metrics", "conversation_id", "author_id"],
                expansions=["author_id"],
                user_fields=["username", "public_metrics"]
            )
            self.limiter.record_read("get_tweet")
            
            if not response.data:
                return None
            
            tweet = response.data
            author = None
            if response.includes and "users" in response.includes:
                author = response.includes["users"][0]
            
            return {
                "id": str(tweet.id),
                "text": tweet.text,
                "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                "metrics": dict(tweet.public_metrics) if tweet.public_metrics else {},
                "author_id": str(tweet.author_id),
                "author_username": author.username if author else None,
                "author_followers": author.public_metrics.get("followers_count", 0) if author and author.public_metrics else 0
            }
            
        except tweepy.TooManyRequests:
            print(f"[X CLIENT] Rate limited on get_tweet")
            return None
        except Exception as e:
            print(f"Error getting tweet {tweet_id}: {e}")
            return None
    
    def get_mentions(self, max_results: int = 10, wait: bool = True) -> List[Dict]:
        """
        Get recent mentions of authenticated user.
        
        FREE TIER: 1/15min
        """
        if not self.limiter.can_read("get_mentions"):
            if wait:
                if not self.limiter.wait_for_read("get_mentions"):
                    return []
            else:
                print(f"[X CLIENT] get_mentions rate limited")
                return []
        
        try:
            user_id = self.me.id if self.me else None
            if not user_id:
                return []
            
            response = self.client.get_users_mentions(
                id=user_id,
                max_results=min(max_results, 10),  # Free tier
                tweet_fields=["created_at", "public_metrics", "author_id", "conversation_id"],
                expansions=["author_id"],
                user_fields=["username"]
            )
            self.limiter.record_read("get_mentions")
            
            if not response.data:
                return []
            
            # Build user lookup
            users = {}
            if response.includes and "users" in response.includes:
                for user in response.includes["users"]:
                    users[str(user.id)] = user.username
            
            mentions = []
            for tweet in response.data:
                mentions.append({
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                    "metrics": dict(tweet.public_metrics) if tweet.public_metrics else {},
                    "author_id": str(tweet.author_id),
                    "author_username": users.get(str(tweet.author_id))
                })
            
            return mentions
            
        except tweepy.TooManyRequests:
            print(f"[X CLIENT] Rate limited on mentions")
            return []
        except Exception as e:
            print(f"Error fetching mentions: {e}")
            return []
    
    def get_rate_status(self) -> str:
        """Get current rate limit status."""
        return self.limiter.display_status()


# Test function
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    client = XClient()
    print(f"Authenticated as: @{client.me.username if client.me else 'unknown'}")
    print("\n" + client.get_rate_status())
