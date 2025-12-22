"""
Quoter Action
Quote retweets tweets.
"""

from typing import Dict, Optional
from datetime import datetime


class Quoter:
    """Handles quote retweeting."""
    
    def __init__(
        self,
        x_client,
        content_generator=None,
        safety_checker=None,
        rate_limiter=None
    ):
        """
        Initialize quoter.
        
        Args:
            x_client: X API client
            content_generator: Content generator
            safety_checker: Safety checker
            rate_limiter: Rate limiter
        """
        self.x_client = x_client
        self.generator = content_generator
        self.safety = safety_checker
        self.limiter = rate_limiter
    
    def quote(
        self,
        target_tweet: Dict,
        content: Optional[str] = None,
        angle: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict:
        """
        Quote retweet a tweet.
        
        Args:
            target_tweet: Tweet to quote
            content: Pre-generated quote text (or generate if None)
            angle: Angle for generation (agree, disagree, etc)
            dry_run: If True, don't actually quote
            
        Returns:
            Result dict
        """
        tweet_id = target_tweet.get("id")
        author = target_tweet.get("author_username", "unknown")
        
        if not tweet_id:
            return {
                "success": False,
                "error": "No tweet ID provided",
                "action": "quote"
            }
        
        # Check rate limit
        if self.limiter and not self.limiter.can_act("quote"):
            return {
                "success": False,
                "error": "Quote limit reached for today",
                "action": "quote",
                "target_id": tweet_id
            }
        
        # Generate content if not provided
        if not content:
            if self.generator:
                content = self.generator.generate_quote(
                    tweet=target_tweet,
                    angle=angle
                )
            else:
                return {
                    "success": False,
                    "error": "No content provided and no generator available",
                    "action": "quote"
                }
        
        if not content:
            return {
                "success": False,
                "error": "Failed to generate quote content",
                "action": "quote",
                "target_id": tweet_id
            }
        
        # Safety check
        if self.safety:
            is_safe, issues = self.safety.check_content(content)
            
            if not is_safe:
                content = self.safety.clean_content(content)
                is_safe, issues = self.safety.check_content(content)
                
                if not is_safe:
                    return {
                        "success": False,
                        "error": f"Quote failed safety check: {issues}",
                        "action": "quote",
                        "target_id": tweet_id,
                        "content": content
                    }
        
        # Quote
        try:
            result = self.x_client.quote_tweet(
                tweet_id=str(tweet_id),
                text=content,
                dry_run=dry_run
            )
            
            if result:
                # Record the action
                if self.limiter and not dry_run:
                    self.limiter.record_action(
                        action_type="quote",
                        tweet_id=result.get("id"),
                        target_id=str(tweet_id),
                        content=content,
                        success=True
                    )
                
                # Record content
                if self.safety and not dry_run:
                    self.safety.record_content(content)
                
                return {
                    "success": True,
                    "action": "quote",
                    "tweet_id": result.get("id"),
                    "target_id": str(tweet_id),
                    "target_author": author,
                    "target_text": target_tweet.get("text", "")[:100],
                    "content": content,
                    "dry_run": dry_run,
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "success": False,
                "error": "Quote returned no result",
                "action": "quote",
                "target_id": tweet_id
            }
            
        except Exception as e:
            # Record failed action
            if self.limiter:
                self.limiter.record_action(
                    action_type="quote",
                    target_id=str(tweet_id),
                    content=content,
                    success=False
                )
            
            return {
                "success": False,
                "error": str(e),
                "action": "quote",
                "target_id": tweet_id,
                "content": content
            }
