"""
Poster Action
Creates original tweets.
"""

from typing import Dict, Optional
from datetime import datetime


class Poster:
    """Handles posting original tweets."""
    
    def __init__(
        self,
        x_client,
        content_generator=None,
        safety_checker=None,
        rate_limiter=None
    ):
        """
        Initialize poster.
        
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
    
    def post(
        self,
        content: Optional[str] = None,
        topic: Optional[str] = None,
        style: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict:
        """
        Create a new tweet.
        
        Args:
            content: Pre-generated content (or generate if None)
            topic: Topic for generation
            style: Style for generation
            dry_run: If True, don't actually post
            
        Returns:
            Result dict with success, tweet_id, etc
        """
        # Check rate limit
        if self.limiter and not self.limiter.can_act("post"):
            return {
                "success": False,
                "error": "Post limit reached for today",
                "action": "post"
            }
        
        # Generate content if not provided
        if not content:
            if self.generator:
                content = self.generator.generate_post(topic=topic, style=style)
            else:
                return {
                    "success": False,
                    "error": "No content provided and no generator available",
                    "action": "post"
                }
        
        if not content:
            return {
                "success": False,
                "error": "Failed to generate content",
                "action": "post"
            }
        
        # Safety check
        if self.safety:
            is_safe, issues = self.safety.check_content(content)
            if not is_safe:
                # Try to clean
                content = self.safety.clean_content(content)
                is_safe, issues = self.safety.check_content(content)
                
                if not is_safe:
                    return {
                        "success": False,
                        "error": f"Content failed safety check: {issues}",
                        "action": "post",
                        "content": content
                    }
        
        # Post
        try:
            result = self.x_client.post_tweet(content, dry_run=dry_run)
            
            if result:
                # Record the action
                if self.limiter and not dry_run:
                    self.limiter.record_action(
                        action_type="post",
                        tweet_id=result.get("id"),
                        content=content,
                        success=True
                    )
                
                # Record content for similarity checking
                if self.safety and not dry_run:
                    self.safety.record_content(content)
                
                return {
                    "success": True,
                    "action": "post",
                    "tweet_id": result.get("id"),
                    "content": content,
                    "dry_run": dry_run,
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "success": False,
                "error": "Post returned no result",
                "action": "post"
            }
            
        except Exception as e:
            # Record failed action
            if self.limiter:
                self.limiter.record_action(
                    action_type="post",
                    content=content,
                    success=False
                )
            
            return {
                "success": False,
                "error": str(e),
                "action": "post",
                "content": content
            }
