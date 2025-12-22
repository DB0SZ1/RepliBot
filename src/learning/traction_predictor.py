"""
Traction Predictor
Predicts engagement potential for tweets.
Continuously improves based on actual results.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import math

DATA_PATH = Path(__file__).parent.parent.parent / "data"


class TractionPredictor:
    """
    Predicts viral potential of tweets.
    
    Uses:
    - Author metrics (followers, engagement rate)
    - Content analysis (topic, sentiment, media)
    - Timing factors
    - Historical patterns
    
    Learns from actual engagement outcomes.
    """
    
    def __init__(self, openrouter_client=None):
        """
        Initialize predictor.
        
        Args:
            openrouter_client: AI client for advanced predictions
        """
        self.ai_client = openrouter_client
        
        DATA_PATH.mkdir(parents=True, exist_ok=True)
        self.metrics_file = DATA_PATH / "engagement_metrics.json"
        self.metrics = self._load_metrics()
        
        # Prediction weights (learned over time)
        self.weights = self.metrics.get("learned_weights", {
            "author_followers": 0.20,
            "author_engagement_rate": 0.25,
            "topic_relevance": 0.20,
            "time_optimality": 0.15,
            "media_bonus": 0.10,
            "conversation_potential": 0.10
        })
    
    def _load_metrics(self) -> Dict:
        """Load engagement metrics."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        
        return {
            "predictions": [],
            "outcomes": [],
            "accuracy_history": [],
            "learned_weights": {},
            "viral_topics": [],
            "best_hours": [9, 10, 11, 18, 19, 20],
            "avg_engagement_rate": 0.05,
            "metadata": {
                "created": datetime.now().isoformat(),
                "last_update": None,
                "total_predictions": 0,
                "correct_predictions": 0
            }
        }
    
    def _save_metrics(self) -> None:
        """Save metrics to disk."""
        self.metrics["metadata"]["last_update"] = datetime.now().isoformat()
        self.metrics["learned_weights"] = self.weights
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2, default=str)
    
    def calculate_author_score(self, tweet: Dict) -> float:
        """
        Score based on author's influence.
        
        Args:
            tweet: Tweet dict with author info
            
        Returns:
            Score 0-100
        """
        followers = tweet.get("author_followers", 0)
        
        # Log scale for followers (diminishing returns)
        if followers <= 0:
            return 10
        
        # Score: 100 followers = 20, 1k = 40, 10k = 60, 100k = 80, 1M = 100
        score = min(100, 20 * math.log10(max(followers, 1)))
        
        return score
    
    def calculate_engagement_rate(self, tweet: Dict) -> float:
        """
        Calculate current engagement rate.
        
        Args:
            tweet: Tweet with metrics
            
        Returns:
            Engagement rate 0-1
        """
        metrics = tweet.get("metrics", {})
        followers = tweet.get("author_followers", 1)
        
        likes = metrics.get("like_count", 0)
        retweets = metrics.get("retweet_count", 0)
        replies = metrics.get("reply_count", 0)
        
        total_engagement = likes + (retweets * 2) + (replies * 3)
        
        if followers <= 0:
            return 0
        
        return min(1, total_engagement / followers)
    
    def calculate_time_score(self, tweet: Dict) -> float:
        """
        Score based on posting time.
        
        Args:
            tweet: Tweet with created_at
            
        Returns:
            Score 0-100
        """
        created_at = tweet.get("created_at")
        if not created_at:
            return 50  # Default
        
        try:
            if isinstance(created_at, str):
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                dt = created_at
            
            hour = dt.hour
            
            # Check if in best hours
            best_hours = self.metrics.get("best_hours", [9, 10, 11, 18, 19, 20])
            
            if hour in best_hours:
                return 100
            
            # Score based on distance from best hours
            min_distance = min(abs(hour - h) for h in best_hours)
            return max(0, 100 - (min_distance * 15))
            
        except Exception:
            return 50
    
    def calculate_topic_score(self, tweet: Dict) -> float:
        """
        Score based on topic relevance.
        
        Args:
            tweet: Tweet dict
            
        Returns:
            Score 0-100
        """
        text = tweet.get("text", "").lower()
        viral_topics = self.metrics.get("viral_topics", [
            "tech", "crypto", "startup", "programming", "ai",
            "drama", "hot take", "unpopular opinion"
        ])
        
        score = 30  # Base score
        
        for topic in viral_topics:
            if topic.lower() in text:
                score += 15
        
        return min(100, score)
    
    def calculate_media_bonus(self, tweet: Dict) -> float:
        """
        Bonus for media content.
        
        Args:
            tweet: Tweet dict
            
        Returns:
            Score 0-100
        """
        # Check for media indicators in text
        text = tweet.get("text", "").lower()
        
        score = 0
        
        # Images/videos typically boost engagement
        if "pic.twitter" in text or "https://t.co" in text:
            score = 50
        
        # Code blocks boost for tech audience
        if "```" in text or any(ext in text for ext in ['.py', '.js', '.ts', '.go']):
            score += 30
        
        return min(100, score)
    
    def calculate_conversation_score(self, tweet: Dict) -> float:
        """
        Score for conversation/reply potential.
        
        Args:
            tweet: Tweet dict
            
        Returns:
            Score 0-100
        """
        text = tweet.get("text", "")
        
        score = 30  # Base
        
        # Questions encourage replies
        if "?" in text:
            score += 30
        
        # Hot takes / controversial
        hot_phrases = ["unpopular opinion", "hot take", "fight me", "change my mind",
                      "actually", "controversial", "no one talks about"]
        if any(phrase in text.lower() for phrase in hot_phrases):
            score += 40
        
        # Direct statements (confidence)
        if text.isupper() or sum(1 for c in text if c.isupper()) / max(len(text), 1) > 0.3:
            score += 20
        
        return min(100, score)
    
    def predict_traction(self, tweet: Dict) -> Dict:
        """
        Predict traction score for a tweet.
        
        Args:
            tweet: Tweet dict
            
        Returns:
            Prediction dict with score and breakdown
        """
        # Calculate component scores
        author_score = self.calculate_author_score(tweet)
        engagement_score = self.calculate_engagement_rate(tweet) * 100
        time_score = self.calculate_time_score(tweet)
        topic_score = self.calculate_topic_score(tweet)
        media_score = self.calculate_media_bonus(tweet)
        conversation_score = self.calculate_conversation_score(tweet)
        
        # Weighted combination
        traction_score = (
            author_score * self.weights["author_followers"] +
            engagement_score * self.weights["author_engagement_rate"] +
            topic_score * self.weights["topic_relevance"] +
            time_score * self.weights["time_optimality"] +
            media_score * self.weights["media_bonus"] +
            conversation_score * self.weights["conversation_potential"]
        )
        
        # Determine potential level
        if traction_score >= 80:
            potential = "viral"
        elif traction_score >= 60:
            potential = "high"
        elif traction_score >= 40:
            potential = "medium"
        else:
            potential = "low"
        
        prediction = {
            "traction_score": round(traction_score, 2),
            "viral_potential": potential,
            "should_engage": traction_score >= 40,
            "breakdown": {
                "author": round(author_score, 1),
                "engagement": round(engagement_score, 1),
                "timing": round(time_score, 1),
                "topic": round(topic_score, 1),
                "media": round(media_score, 1),
                "conversation": round(conversation_score, 1)
            },
            "tweet_id": tweet.get("id"),
            "predicted_at": datetime.now().isoformat()
        }
        
        # Store prediction for later evaluation
        self.metrics["predictions"].append({
            "tweet_id": tweet.get("id"),
            "score": traction_score,
            "predicted_at": prediction["predicted_at"]
        })
        
        # Keep last 500 predictions
        if len(self.metrics["predictions"]) > 500:
            self.metrics["predictions"] = self.metrics["predictions"][-500:]
        
        self.metrics["metadata"]["total_predictions"] += 1
        self._save_metrics()
        
        return prediction
    
    def predict_with_ai(self, tweet: Dict, learned_patterns: Dict) -> Optional[Dict]:
        """
        Use AI for advanced prediction.
        
        Args:
            tweet: Tweet dict
            learned_patterns: Learned engagement patterns
            
        Returns:
            AI prediction or None
        """
        if not self.ai_client:
            return None
        
        return self.ai_client.predict_engagement(tweet, learned_patterns)
    
    def record_outcome(
        self,
        tweet_id: str,
        actual_likes: int,
        actual_retweets: int,
        actual_replies: int
    ) -> None:
        """
        Record actual outcome for learning.
        
        Args:
            tweet_id: Tweet ID
            actual_likes: Actual like count
            actual_retweets: Actual retweet count
            actual_replies: Actual reply count
        """
        # Find prediction
        prediction = None
        for p in self.metrics["predictions"]:
            if p.get("tweet_id") == tweet_id:
                prediction = p
                break
        
        if not prediction:
            return
        
        # Calculate actual score
        actual_engagement = actual_likes + (actual_retweets * 2) + (actual_replies * 3)
        
        # Store outcome
        outcome = {
            "tweet_id": tweet_id,
            "predicted_score": prediction["score"],
            "actual_engagement": actual_engagement,
            "actual_likes": actual_likes,
            "actual_retweets": actual_retweets,
            "actual_replies": actual_replies,
            "recorded_at": datetime.now().isoformat()
        }
        
        self.metrics["outcomes"].append(outcome)
        
        # Keep last 500 outcomes
        if len(self.metrics["outcomes"]) > 500:
            self.metrics["outcomes"] = self.metrics["outcomes"][-500:]
        
        # Check if prediction was correct
        predicted_high = prediction["score"] >= 40
        actual_high = actual_engagement >= 10
        
        if predicted_high == actual_high:
            self.metrics["metadata"]["correct_predictions"] += 1
        
        # Learn from outcome
        self._learn_from_outcome(prediction, outcome)
        
        self._save_metrics()
    
    def _learn_from_outcome(self, prediction: Dict, outcome: Dict) -> None:
        """Adjust weights based on outcome."""
        predicted = prediction["score"]
        actual = outcome["actual_engagement"]
        
        # Simple weight adjustment
        error = abs(predicted - min(100, actual * 2))  # Scale actual to 0-100
        
        # If error is high, adjust weights slightly
        if error > 30:
            # This is a simplified learning - real ML would be more sophisticated
            adjustment = 0.01
            
            # Adjust based on which component was likely off
            if outcome["actual_replies"] > outcome["actual_likes"]:
                # Conversation was more important
                self.weights["conversation_potential"] = min(0.3, 
                    self.weights["conversation_potential"] + adjustment)
                self.weights["author_followers"] = max(0.1,
                    self.weights["author_followers"] - adjustment)
    
    def get_best_opportunities(
        self,
        tweets: List[Dict],
        top_n: int = 5
    ) -> List[Tuple[Dict, Dict]]:
        """
        Find best engagement opportunities from tweet list.
        
        Args:
            tweets: List of tweet dicts
            top_n: Number of top opportunities
            
        Returns:
            List of (tweet, prediction) tuples
        """
        predictions = []
        
        for tweet in tweets:
            pred = self.predict_traction(tweet)
            predictions.append((tweet, pred))
        
        # Sort by score
        predictions.sort(key=lambda x: x[1]["traction_score"], reverse=True)
        
        return predictions[:top_n]
    
    def get_accuracy(self) -> float:
        """Get prediction accuracy."""
        total = self.metrics["metadata"]["total_predictions"]
        correct = self.metrics["metadata"]["correct_predictions"]
        
        if total == 0:
            return 0.0
        
        return correct / total
    
    def get_stats(self) -> Dict:
        """Get predictor statistics."""
        return {
            "total_predictions": self.metrics["metadata"]["total_predictions"],
            "correct_predictions": self.metrics["metadata"]["correct_predictions"],
            "accuracy": f"{self.get_accuracy() * 100:.1f}%",
            "outcomes_recorded": len(self.metrics["outcomes"]),
            "weights": self.weights,
            "best_hours": self.metrics["best_hours"],
            "viral_topics": self.metrics.get("viral_topics", [])
        }


# Test
if __name__ == "__main__":
    predictor = TractionPredictor()
    
    # Test prediction
    sample_tweet = {
        "id": "test123",
        "text": "Unpopular opinion: Most 'senior' developers can't debug without Stack Overflow. Fight me.",
        "author_followers": 5000,
        "author_username": "test_user",
        "metrics": {"like_count": 15, "retweet_count": 3, "reply_count": 8},
        "created_at": datetime.now().isoformat()
    }
    
    prediction = predictor.predict_traction(sample_tweet)
    print("Prediction:")
    print(json.dumps(prediction, indent=2))
    
    print("\nStats:")
    print(json.dumps(predictor.get_stats(), indent=2))
