"""
Safety Checker
Anti-spam protection and X policy compliance.
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json

DATA_PATH = Path(__file__).parent.parent.parent / "data"


class SafetyChecker:
    """
    Checks content for safety and spam risks.
    
    Prevents:
    - Duplicate content
    - Spam patterns
    - Policy violations
    - Detection triggers
    """
    
    # Spam trigger words/patterns
    SPAM_PATTERNS = [
        r'\bfollow\s*(me|back)\b',
        r'\bclick\s*(here|link)\b',
        r'\bfree\s*(money|crypto|nft)\b',
        r'\bdm\s*me\s*for\b',
        r'\bgiveaway\b',
        r'\bwin\s*(a|free)\b',
        r'\blink\s*in\s*bio\b',
        r'\bclaim\s*(your|now)\b',
        r'\b(check|see)\s*pinned\b',
        r'\bfollow4follow\b',
        r'\bf4f\b',
        r'\b100%\s*(guaranteed|free)\b'
    ]
    
    # Forbidden content patterns
    FORBIDDEN_PATTERNS = [
        r'\b(hate|kill|death\s*to)\b.*\b(group|race|religion)\b',
        r'\bdoxx',
        r'\bswat',
        r'\bterrorist\b',
        r'\bbomb\s*threat\b'
    ]
    
    def __init__(self, rate_limiter=None):
        """
        Initialize checker.
        
        Args:
            rate_limiter: Rate limiter for action history
        """
        self.rate_limiter = rate_limiter
        self._recent_content: List[str] = []
        self._load_history()
    
    def _load_history(self) -> None:
        """Load recent content history."""
        history_file = DATA_PATH / "content_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    self._recent_content = data.get("recent", [])
            except:
                pass
    
    def _save_history(self) -> None:
        """Save content history."""
        DATA_PATH.mkdir(parents=True, exist_ok=True)
        history_file = DATA_PATH / "content_history.json"
        with open(history_file, 'w') as f:
            json.dump({"recent": self._recent_content[-100:]}, f)
    
    def check_content(self, content: str) -> Tuple[bool, List[str]]:
        """
        Check if content is safe to post.
        
        Args:
            content: Content to check
            
        Returns:
            Tuple of (is_safe, list of issues)
        """
        issues = []
        content_lower = content.lower()
        
        # Check for spam patterns
        for pattern in self.SPAM_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE):
                issues.append(f"Spam pattern detected: {pattern}")
        
        # Check for forbidden content
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE):
                issues.append(f"Forbidden content: {pattern}")
        
        # Check length
        if len(content) > 280:
            issues.append(f"Content too long: {len(content)} chars (max 280)")
        
        # Check for too many hashtags
        hashtag_count = content.count('#')
        if hashtag_count > 2:
            issues.append(f"Too many hashtags: {hashtag_count} (max 2)")
        
        # Check for too many mentions
        mention_count = len(re.findall(r'@\w+', content))
        if mention_count > 2:
            issues.append(f"Too many mentions: {mention_count} (max 2)")
        
        # Check for too many links
        link_count = len(re.findall(r'https?://\S+', content))
        if link_count > 1:
            issues.append(f"Too many links: {link_count} (max 1)")
        
        # Check for similarity to recent content
        similarity_issue = self._check_similarity(content)
        if similarity_issue:
            issues.append(similarity_issue)
        
        return len(issues) == 0, issues
    
    def _check_similarity(self, content: str) -> Optional[str]:
        """
        Check if content is too similar to recent posts.
        
        Args:
            content: Content to check
            
        Returns:
            Issue description or None
        """
        if not self._recent_content:
            return None
        
        content_words = set(content.lower().split())
        
        for recent in self._recent_content[-10:]:
            recent_words = set(recent.lower().split())
            
            if not content_words or not recent_words:
                continue
            
            # Jaccard similarity
            intersection = len(content_words & recent_words)
            union = len(content_words | recent_words)
            
            if union > 0:
                similarity = intersection / union
                if similarity > 0.7:
                    return f"Content too similar to recent post (similarity: {similarity:.1%})"
        
        return None
    
    def check_reply_safety(
        self,
        reply: str,
        target_tweet: Dict,
        author_username: str
    ) -> Tuple[bool, List[str]]:
        """
        Check if a reply is safe.
        
        Args:
            reply: Reply content
            target_tweet: Tweet being replied to
            author_username: Author of target tweet
            
        Returns:
            Tuple of (is_safe, list of issues)
        """
        issues = []
        
        # Basic content check
        is_safe, content_issues = self.check_content(reply)
        issues.extend(content_issues)
        
        # Check if replying to same user too much
        if self.rate_limiter:
            recent = self.rate_limiter.get_recent_actions(20)
            same_user_replies = sum(
                1 for a in recent
                if a.get("type") == "reply" and 
                author_username.lower() in str(a.get("target_id", "")).lower()
            )
            if same_user_replies >= 3:
                issues.append(f"Too many replies to @{author_username} today (max 3)")
        
        # Check for keyword spam in reply
        reply_lower = reply.lower()
        if reply_lower.count(reply_lower.split()[0] if reply_lower.split() else "") > 3:
            issues.append("Repetitive content detected")
        
        return len(issues) == 0, issues
    
    def check_timing_safety(self) -> Tuple[bool, List[str]]:
        """
        Check if timing is safe for action.
        
        Returns:
            Tuple of (is_safe, list of issues)
        """
        issues = []
        
        if self.rate_limiter:
            recent = self.rate_limiter.get_recent_actions(5)
            
            if recent:
                # Check for burst activity
                last_action = recent[0]
                last_time = datetime.fromisoformat(last_action.get("timestamp", "2000-01-01"))
                time_since = (datetime.now() - last_time).total_seconds()
                
                if time_since < 60:  # Less than 1 minute
                    issues.append("Action too soon after last (min 1 minute gap)")
                
                # Check for too many actions in last hour
                one_hour_ago = datetime.now() - timedelta(hours=1)
                recent_hour = [
                    a for a in self.rate_limiter.get_recent_actions(20)
                    if datetime.fromisoformat(a.get("timestamp", "2000-01-01")) > one_hour_ago
                ]
                
                if len(recent_hour) >= 5:
                    issues.append(f"Too many actions in last hour: {len(recent_hour)} (max 5)")
        
        return len(issues) == 0, issues
    
    def record_content(self, content: str) -> None:
        """
        Record content for similarity checking.
        
        Args:
            content: Content that was posted
        """
        self._recent_content.append(content)
        
        # Keep last 100
        if len(self._recent_content) > 100:
            self._recent_content = self._recent_content[-100:]
        
        self._save_history()
    
    def clean_content(self, content: str) -> str:
        """
        Clean content to make it safer.
        
        Args:
            content: Original content
            
        Returns:
            Cleaned content
        """
        cleaned = content
        
        # Remove extra hashtags (keep first 2)
        hashtags = re.findall(r'#\w+', cleaned)
        if len(hashtags) > 2:
            for hashtag in hashtags[2:]:
                cleaned = cleaned.replace(hashtag, '').strip()
        
        # Remove extra mentions (keep first 2)
        mentions = re.findall(r'@\w+', cleaned)
        if len(mentions) > 2:
            for mention in mentions[2:]:
                cleaned = cleaned.replace(mention, '').strip()
        
        # Remove extra links (keep first)
        links = re.findall(r'https?://\S+', cleaned)
        if len(links) > 1:
            for link in links[1:]:
                cleaned = cleaned.replace(link, '').strip()
        
        # Truncate if too long
        if len(cleaned) > 280:
            cleaned = cleaned[:277] + "..."
        
        # Clean up whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def get_safety_score(self, content: str) -> float:
        """
        Get a safety score for content.
        
        Args:
            content: Content to score
            
        Returns:
            Score 0-1 (1 = very safe)
        """
        is_safe, issues = self.check_content(content)
        
        if is_safe:
            return 1.0
        
        # Deduct points for each issue
        score = 1.0
        for issue in issues:
            if "Forbidden" in issue:
                score -= 0.5
            elif "Spam" in issue:
                score -= 0.3
            else:
                score -= 0.1
        
        return max(0, score)
    
    def summarize_issues(self, issues: List[str]) -> str:
        """Format issues for display."""
        if not issues:
            return "✓ Content is safe"
        
        return "Issues found:\n" + "\n".join(f"  ⚠️ {issue}" for issue in issues)


# Test
if __name__ == "__main__":
    checker = SafetyChecker()
    
    # Test various content
    test_cases = [
        "This is a normal tweet about coding.",
        "Follow me and I'll follow back! #f4f #follow4follow",
        "Check my link in bio for free crypto!",
        "Just deployed to production. What could go wrong? 🚀",
        "Here's a great thread on async/await! https://example.com #javascript #coding #tech #tips",
        "This take is garbage. Absolute trash fire of an opinion."
    ]
    
    for content in test_cases:
        is_safe, issues = checker.check_content(content)
        score = checker.get_safety_score(content)
        
        status = "✓ SAFE" if is_safe else "✗ UNSAFE"
        print(f"\n{status} (score: {score:.2f})")
        print(f"Content: {content[:60]}...")
        if issues:
            for issue in issues:
                print(f"  - {issue}")
