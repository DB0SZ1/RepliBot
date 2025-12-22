"""
Decision Maker
AI brain that decides what action to take next.
"""

import json
import random
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent.parent / "data"


class DecisionMaker:
    """
    Decides the next best action for the bot.
    
    Considers:
    - Available budget (posts/quotes/replies remaining)
    - Timeline opportunities
    - Engagement predictions
    - Recent actions (avoid repetition)
    - Personality fit
    """
    
    def __init__(
        self,
        openrouter_client=None,
        rate_limiter=None,
        traction_predictor=None,
        personality_engine=None
    ):
        """
        Initialize decision maker.
        
        Args:
            openrouter_client: AI client for decisions
            rate_limiter: Rate limiter for budget
            traction_predictor: Traction predictor
            personality_engine: Personality engine
        """
        self.ai_client = openrouter_client
        self.rate_limiter = rate_limiter
        self.predictor = traction_predictor
        self.personality = personality_engine
        
        DATA_PATH.mkdir(parents=True, exist_ok=True)
    
    def get_remaining_budget(self) -> Dict:
        """Get remaining action budget."""
        if self.rate_limiter:
            usage = self.rate_limiter.get_usage()
            return usage["remaining_by_type"]
        
        # Default if no rate limiter
        return {"post": 2, "quote": 1, "reply": 14}
    
    def rank_opportunities(
        self,
        tweets: List[Dict],
        top_n: int = 5
    ) -> List[Dict]:
        """
        Rank tweets by opportunity score.
        
        Args:
            tweets: List of tweet dicts
            top_n: Number of top opportunities
            
        Returns:
            Ranked list of tweets with scores
        """
        ranked = []
        
        for tweet in tweets:
            # Skip if already replied to recently
            if self._recently_engaged(tweet.get("id")):
                continue
            
            # Get traction prediction
            if self.predictor:
                prediction = self.predictor.predict_traction(tweet)
                score = prediction["traction_score"]
            else:
                # Basic scoring without predictor
                metrics = tweet.get("metrics", {})
                score = metrics.get("like_count", 0) * 2 + metrics.get("reply_count", 0) * 3
            
            ranked.append({
                "tweet": tweet,
                "score": score,
                "should_engage": score >= 30
            })
        
        # Sort by score
        ranked.sort(key=lambda x: x["score"], reverse=True)
        
        return ranked[:top_n]
    
    def _recently_engaged(self, tweet_id: str) -> bool:
        """Check if we recently engaged with this tweet."""
        if not self.rate_limiter:
            return False
        
        recent = self.rate_limiter.get_recent_actions(20)
        recent_ids = [a.get("target_id") for a in recent]
        
        return tweet_id in recent_ids
    
    def decide_action_type(self, budget: Dict) -> Optional[str]:
        """
        Decide which action type to perform.
        
        Args:
            budget: Remaining budget by type
            
        Returns:
            Action type or None
        """
        # Priority: reply > post > quote (replies are the core strategy)
        
        if budget.get("reply", 0) > 0:
            # 80% chance to reply if available
            if random.random() < 0.8:
                return "reply"
        
        if budget.get("post", 0) > 0:
            # Post if early in day or no good replies
            if random.random() < 0.3:
                return "post"
        
        if budget.get("quote", 0) > 0:
            # Quote occasionally
            if random.random() < 0.2:
                return "quote"
        
        # Fall back to whatever is available
        if budget.get("reply", 0) > 0:
            return "reply"
        if budget.get("post", 0) > 0:
            return "post"
        if budget.get("quote", 0) > 0:
            return "quote"
        
        return None  # Budget exhausted
    
    def decide(
        self,
        timeline: List[Dict],
        mentions: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Make a decision on next action.
        
        Args:
            timeline: Current timeline tweets
            mentions: Recent mentions (priority)
            
        Returns:
            Decision dict with action, target, reasoning
        """
        budget = self.get_remaining_budget()
        
        # Check if we can act at all
        if not any(v > 0 for v in budget.values()):
            return {
                "action": "skip",
                "reason": "Daily budget exhausted",
                "next_available": self.rate_limiter.get_next_available_time() if self.rate_limiter else None
            }
        
        # Priority: respond to mentions first
        if mentions and budget.get("reply", 0) > 0:
            # Find best mention to respond to
            ranked_mentions = self.rank_opportunities(mentions, top_n=3)
            if ranked_mentions and ranked_mentions[0]["should_engage"]:
                return {
                    "action": "reply",
                    "target": ranked_mentions[0]["tweet"],
                    "reason": "Responding to mention",
                    "score": ranked_mentions[0]["score"],
                    "is_mention": True
                }
        
        # Decide action type
        action_type = self.decide_action_type(budget)
        
        if action_type is None:
            return {
                "action": "skip",
                "reason": "No suitable action type available"
            }
        
        if action_type == "post":
            # Original post
            return {
                "action": "post",
                "target": None,
                "reason": "Creating original content",
                "topic_suggestions": self._get_topic_suggestions()
            }
        
        # Reply or quote - need a target
        ranked = self.rank_opportunities(timeline, top_n=5)
        
        if not ranked:
            return {
                "action": "skip",
                "reason": "No good opportunities in timeline"
            }
        
        best = ranked[0]
        
        # Check if worth engaging
        if not best["should_engage"]:
            # Lower standards if we're falling behind on actions
            if budget.get("reply", 0) > 10:  # Still have many replies left
                return {
                    "action": "skip",
                    "reason": f"Best opportunity score ({best['score']}) too low",
                    "threshold": 30
                }
        
        return {
            "action": action_type,
            "target": best["tweet"],
            "reason": f"Good opportunity (score: {best['score']:.1f})",
            "score": best["score"],
            "alternatives": [r["tweet"]["id"] for r in ranked[1:3]]
        }
    
    def decide_with_ai(
        self,
        timeline: List[Dict],
        mentions: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Use AI to make decision.
        
        Args:
            timeline: Current timeline
            mentions: Recent mentions
            
        Returns:
            AI decision dict
        """
        if not self.ai_client:
            return self.decide(timeline, mentions)
        
        budget = self.get_remaining_budget()
        
        # Get personality
        personality = {}
        learned_patterns = {}
        if self.personality:
            personality = self.personality.get_personality()
        
        if self.predictor:
            learned_patterns = {
                "viral_topics": self.predictor.metrics.get("viral_topics", []),
                "avg_engagement_rate": self.predictor.metrics.get("avg_engagement_rate", 0.05),
                "best_hours": self.predictor.metrics.get("best_hours", [9, 10, 11])
            }
        
        # Get recent actions
        recent_actions = []
        if self.rate_limiter:
            recent_actions = self.rate_limiter.get_recent_actions(5)
        
        # Combine timeline and mentions
        all_tweets = []
        if mentions:
            all_tweets.extend(mentions)
        all_tweets.extend(timeline[:15])
        
        # Call AI
        decision = self.ai_client.decide_action(
            timeline=all_tweets,
            personality=personality,
            learned_patterns=learned_patterns,
            actions_remaining=budget,
            recent_actions=recent_actions
        )
        
        if not decision:
            # Fall back to non-AI decision
            return self.decide(timeline, mentions)
        
        # Parse AI decision
        action = decision.get("action", "skip")
        target_id = decision.get("target_tweet_id")
        
        # Find target tweet
        target = None
        if target_id:
            for t in all_tweets:
                if str(t.get("id")) == str(target_id):
                    target = t
                    break
        
        return {
            "action": action,
            "target": target,
            "content": decision.get("content"),
            "reason": decision.get("reasoning", "AI decision"),
            "score": decision.get("engagement_prediction", 50),
            "confidence": decision.get("confidence", 0.5),
            "ai_generated": True
        }
    
    def _get_topic_suggestions(self) -> List[str]:
        """Get topic suggestions for original posts."""
        # Could pull from trending topics, learned patterns, etc.
        topics = [
            "tech industry hot take",
            "programming humor",
            "startup life observation",
            "code quality rant",
            "developer experience tip",
            "unpopular tech opinion"
        ]
        
        # Add learned viral topics if available
        if self.predictor:
            viral = self.predictor.metrics.get("viral_topics", [])
            topics.extend(viral[:3])
        
        return topics[:5]
    
    def should_skip(self, decision: Dict) -> bool:
        """Check if decision is a skip."""
        return decision.get("action") == "skip"
    
    def format_decision(self, decision: Dict) -> str:
        """Format decision for logging."""
        action = decision.get("action", "unknown")
        reason = decision.get("reason", "")
        
        if action == "skip":
            return f"⏭️  SKIP: {reason}"
        
        target = decision.get("target", {})
        target_text = target.get("text", "")[:50] if target else ""
        score = decision.get("score", 0)
        
        icons = {"post": "📝", "reply": "💬", "quote": "🔄"}
        icon = icons.get(action, "•")
        
        return f"{icon} {action.upper()} (score: {score:.1f}): {target_text}..."


# Test
if __name__ == "__main__":
    dm = DecisionMaker()
    
    # Test with mock timeline
    mock_timeline = [
        {
            "id": "1",
            "text": "Just deployed to production on Friday. What could go wrong?",
            "author_username": "dev_user",
            "author_followers": 5000,
            "metrics": {"like_count": 45, "retweet_count": 12, "reply_count": 23}
        },
        {
            "id": "2", 
            "text": "Another boring corporate announcement",
            "author_username": "corp_account",
            "author_followers": 100000,
            "metrics": {"like_count": 5, "retweet_count": 0, "reply_count": 1}
        }
    ]
    
    decision = dm.decide(mock_timeline)
    print("Decision:")
    print(json.dumps(decision, indent=2, default=str))
    print(f"\n{dm.format_decision(decision)}")
