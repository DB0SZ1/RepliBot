"""
Replier Action
Replies to tweets.
"""

from typing import Dict, Optional
from datetime import datetime


class Replier:
    """Handles replying to tweets."""
    
    def __init__(
        self,
        x_client,
        content_generator=None,
        safety_checker=None,
        rate_limiter=None
    ):
        """
        Initialize replier.
        
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
    
    def reply(
        self,
        target_tweet: Dict,
        content: Optional[str] = None,
        style_hint: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict:
        """
        Reply to a tweet.
        
        Args:
            target_tweet: Tweet to reply to
            content: Pre-generated reply (or generate if None)
            style_hint: Style hint for generation
            dry_run: If True, don't actually reply
            
        Returns:
            Result dict
        """
        tweet_id = target_tweet.get("id")
        author = target_tweet.get("author_username", "unknown")
        
        if not tweet_id:
            return {
                "success": False,
                "error": "No tweet ID provided",
                "action": "reply"
            }
        
        # Check rate limit
        if self.limiter and not self.limiter.can_act("reply"):
            return {
                "success": False,
                "error": "Reply limit reached for today",
                "action": "reply",
                "target_id": tweet_id
            }
        
        # Generate content if not provided
        if not content:
            if self.generator:
                content = self.generator.generate_reply(
                    tweet=target_tweet,
                    style_hint=style_hint
                )
            else:
                return {
                    "success": False,
                    "error": "No content provided and no generator available",
                    "action": "reply"
                }
        
        if not content:
            return {
                "success": False,
                "error": "Failed to generate reply content",
                "action": "reply",
                "target_id": tweet_id
            }
        
        # Safety check
        if self.safety:
            is_safe, issues = self.safety.check_reply_safety(
                reply=content,
                target_tweet=target_tweet,
                author_username=author
            )
            
            if not is_safe:
                # Try to clean
                content = self.safety.clean_content(content)
                is_safe, issues = self.safety.check_reply_safety(
                    reply=content,
                    target_tweet=target_tweet,
                    author_username=author
                )
                
                if not is_safe:
                    return {
                        "success": False,
                        "error": f"Reply failed safety check: {issues}",
                        "action": "reply",
                        "target_id": tweet_id,
                        "content": content
                    }
        
        # Reply
        try:
            result = self.x_client.reply_to_tweet(
                tweet_id=str(tweet_id),
                text=content,
                dry_run=dry_run
            )
            
            if result:
                # Record the action
                if self.limiter and not dry_run:
                    self.limiter.record_action(
                        action_type="reply",
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
                    "action": "reply",
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
                "error": "Reply returned no result",
                "action": "reply",
                "target_id": tweet_id
            }
            
        except Exception as e:
            # Record failed action
            if self.limiter:
                self.limiter.record_action(
                    action_type="reply",
                    target_id=str(tweet_id),
                    content=content,
                    success=False
                )
            
            return {
                "success": False,
                "error": str(e),
                "action": "reply",
                "target_id": tweet_id,
                "content": content
            }
