"""
Style Analyzer
Learns communication patterns from collected posts.
Uses AI to analyze and quantify style elements.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import re
from collections import Counter

DATA_PATH = Path(__file__).parent.parent.parent / "data"


class StyleAnalyzer:
    """
    Analyzes communication style from collected posts.
    
    Learns:
    - Sentence structure
    - Emoji usage
    - Slang/pidgin patterns  
    - Humor types
    - Code terminology usage
    - Directness level
    """
    
    def __init__(self, openrouter_client=None):
        """
        Initialize analyzer.
        
        Args:
            openrouter_client: OpenRouter client for AI analysis
        """
        self.ai_client = openrouter_client
        
        DATA_PATH.mkdir(parents=True, exist_ok=True)
        self.history_file = DATA_PATH / "learning_history.json"
        self.history = self._load_history()
    
    def _load_history(self) -> Dict:
        """Load learning history."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        
        return {
            "sessions": [],
            "aggregated_style": {},
            "code_terms": [],
            "common_phrases": [],
            "metadata": {
                "created": datetime.now().isoformat(),
                "last_analysis": None,
                "total_posts_analyzed": 0
            }
        }
    
    def _save_history(self) -> None:
        """Save learning history."""
        self.history["metadata"]["last_analysis"] = datetime.now().isoformat()
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
    
    def analyze_basic_metrics(self, posts: List[str]) -> Dict:
        """
        Analyze basic text metrics without AI.
        
        Args:
            posts: List of post texts
            
        Returns:
            Basic metrics dict
        """
        if not posts:
            return {}
        
        metrics = {
            "total_posts": len(posts),
            "avg_length": 0,
            "avg_word_count": 0,
            "uses_caps": False,
            "caps_frequency": 0.0,
            "emoji_frequency": 0.0,
            "question_frequency": 0.0,
            "exclamation_frequency": 0.0,
            "hashtag_frequency": 0.0,
            "mention_frequency": 0.0
        }
        
        total_length = 0
        total_words = 0
        caps_posts = 0
        emoji_posts = 0
        question_posts = 0
        exclamation_posts = 0
        hashtag_posts = 0
        mention_posts = 0
        
        emoji_pattern = re.compile(
            "["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        
        for post in posts:
            total_length += len(post)
            total_words += len(post.split())
            
            # Check for ALL CAPS sections
            caps_words = sum(1 for word in post.split() if word.isupper() and len(word) > 2)
            if caps_words >= 2:
                caps_posts += 1
            
            # Emoji check
            if emoji_pattern.search(post):
                emoji_posts += 1
            
            # Punctuation
            if '?' in post:
                question_posts += 1
            if '!' in post:
                exclamation_posts += 1
            
            # Social features
            if '#' in post:
                hashtag_posts += 1
            if '@' in post:
                mention_posts += 1
        
        metrics["avg_length"] = total_length / len(posts)
        metrics["avg_word_count"] = total_words / len(posts)
        metrics["uses_caps"] = caps_posts / len(posts) > 0.1
        metrics["caps_frequency"] = caps_posts / len(posts)
        metrics["emoji_frequency"] = emoji_posts / len(posts)
        metrics["question_frequency"] = question_posts / len(posts)
        metrics["exclamation_frequency"] = exclamation_posts / len(posts)
        metrics["hashtag_frequency"] = hashtag_posts / len(posts)
        metrics["mention_frequency"] = mention_posts / len(posts)
        
        return metrics
    
    def extract_code_terms(self, posts: List[str]) -> List[str]:
        """
        Extract programming/tech terms from posts.
        
        Args:
            posts: List of post texts
            
        Returns:
            List of code terms found
        """
        # Common programming terms
        code_terms = [
            'function', 'variable', 'array', 'object', 'class', 'method',
            'api', 'endpoint', 'database', 'query', 'server', 'client',
            'frontend', 'backend', 'stack', 'debug', 'deploy', 'git',
            'repo', 'commit', 'push', 'pull', 'merge', 'branch',
            'loop', 'iteration', 'recursive', 'algorithm', 'optimize',
            'refactor', 'legacy', 'technical debt', 'abstraction',
            'interface', 'implementation', 'async', 'sync', 'callback',
            'promise', 'await', 'thread', 'process', 'memory', 'cpu',
            'cache', 'latency', 'throughput', 'scalable', 'microservice',
            'monolith', 'container', 'docker', 'kubernetes', 'ci/cd',
            'pipeline', 'test', 'unit test', 'integration', 'staging',
            'production', 'dev', 'ops', 'devops', 'agile', 'sprint',
            'bug', 'issue', 'ticket', 'pr', 'code review', 'lgtm',
            'null', 'undefined', 'error', 'exception', 'throw', 'catch',
            'if/else', 'switch', 'return', 'boolean', 'string', 'int',
            'float', 'json', 'xml', 'http', 'rest', 'graphql', 'sql',
            'nosql', 'redis', 'postgres', 'mongo', 'firebase', 'aws',
            'cloud', 'serverless', 'lambda', 'ec2', 's3', 'cdn',
            'sdk', 'framework', 'library', 'package', 'dependency',
            'npm', 'pip', 'brew', 'yarn', 'webpack', 'babel', 'typescript'
        ]
        
        found_terms = Counter()
        all_text = ' '.join(posts).lower()
        
        for term in code_terms:
            count = all_text.count(term.lower())
            if count > 0:
                found_terms[term] = count
        
        # Return top terms
        return [term for term, _ in found_terms.most_common(20)]
    
    def analyze_with_ai(self, posts: List[str]) -> Optional[Dict]:
        """
        Use AI to analyze communication style.
        
        Args:
            posts: List of post texts
            
        Returns:
            AI analysis dict or None
        """
        if not self.ai_client:
            print("[!] No AI client for deep analysis")
            return None
        
        if len(posts) < 5:
            print("[!] Need at least 5 posts for AI analysis")
            return None
        
        # Sample posts for analysis
        sample = posts[:30] if len(posts) > 30 else posts
        
        return self.ai_client.analyze_style(sample)
    
    def analyze_posts(self, posts: List[str], account: str = "unknown") -> Dict:
        """
        Full analysis of posts from an account.
        
        Args:
            posts: List of post texts
            account: Account name for logging
            
        Returns:
            Complete analysis dict
        """
        print(f"[*] Analyzing {len(posts)} posts from @{account}...")
        
        # Basic metrics
        basic = self.analyze_basic_metrics(posts)
        
        # Extract code terms
        code_terms = self.extract_code_terms(posts)
        
        # AI analysis
        ai_analysis = self.analyze_with_ai(posts)
        
        # Combine results
        analysis = {
            "account": account,
            "timestamp": datetime.now().isoformat(),
            "posts_analyzed": len(posts),
            "basic_metrics": basic,
            "code_terms_found": code_terms,
            "uses_code_terms": len(code_terms) > 3,
            "ai_analysis": ai_analysis or {}
        }
        
        # Merge AI analysis into top level for easy access
        if ai_analysis:
            for key in ['directness_score', 'formality_score', 'dominant_tone', 
                        'humor_type', 'sentence_style']:
                if key in ai_analysis:
                    analysis[key] = ai_analysis[key]
        
        # Store in history
        self.history["sessions"].append({
            "account": account,
            "timestamp": analysis["timestamp"],
            "summary": {
                "posts": len(posts),
                "directness": analysis.get("directness_score", 5),
                "uses_code_terms": analysis["uses_code_terms"]
            }
        })
        
        # Keep last 100 sessions
        if len(self.history["sessions"]) > 100:
            self.history["sessions"] = self.history["sessions"][-100:]
        
        self.history["metadata"]["total_posts_analyzed"] += len(posts)
        
        # Update aggregated style
        self._update_aggregated_style(analysis)
        
        self._save_history()
        
        print(f"[+] Analysis complete for @{account}")
        return analysis
    
    def _update_aggregated_style(self, analysis: Dict) -> None:
        """Update aggregated style from new analysis."""
        agg = self.history.get("aggregated_style", {})
        
        # Weight new analysis (more recent = more weight)
        weight = 0.3  # 30% weight for new analysis
        
        # Update numeric metrics
        for key in ['directness_score', 'formality_score']:
            if key in analysis:
                old_val = agg.get(key, 5)
                new_val = analysis[key]
                agg[key] = (old_val * (1 - weight)) + (new_val * weight)
        
        # Update code terms
        existing_terms = set(agg.get("code_terms", []))
        new_terms = set(analysis.get("code_terms_found", []))
        agg["code_terms"] = list(existing_terms | new_terms)[:30]
        
        # Update boolean flags
        if "uses_code_terms" in analysis:
            agg["uses_code_terms"] = analysis["uses_code_terms"]
        
        # Update string values (take latest)
        for key in ['dominant_tone', 'humor_type', 'sentence_style']:
            if key in analysis:
                agg[key] = analysis[key]
        
        # Update basic metrics
        basic = analysis.get("basic_metrics", {})
        for key in ['caps_frequency', 'emoji_frequency', 'avg_word_count']:
            if key in basic:
                old_val = agg.get(key, basic[key])
                agg[key] = (old_val * (1 - weight)) + (basic[key] * weight)
        
        self.history["aggregated_style"] = agg
    
    def get_learned_style(self) -> Dict:
        """Get the aggregated learned style."""
        return self.history.get("aggregated_style", {})
    
    def get_stats(self) -> Dict:
        """Get learning statistics."""
        return {
            "sessions": len(self.history["sessions"]),
            "total_posts_analyzed": self.history["metadata"]["total_posts_analyzed"],
            "last_analysis": self.history["metadata"]["last_analysis"],
            "has_learned_style": bool(self.history.get("aggregated_style")),
            "code_terms_learned": len(self.history.get("aggregated_style", {}).get("code_terms", []))
        }


# Test
if __name__ == "__main__":
    analyzer = StyleAnalyzer()
    print("Style Analyzer Stats:")
    print(json.dumps(analyzer.get_stats(), indent=2))
    
    # Test with sample posts
    sample_posts = [
        "This code is literally O(n²) and they're wondering why it's slow. LMAO",
        "Refactoring this legacy monolith is like defusing a bomb blindfolded",
        "When the junior pushes to main without review 💀",
        "The abstraction layers in this codebase are INSANE. Who hurt these people?",
        "Async/await is not a magic wand. You still need to understand the event loop."
    ]
    
    basic = analyzer.analyze_basic_metrics(sample_posts)
    print("\nBasic Metrics:")
    print(json.dumps(basic, indent=2))
    
    code_terms = analyzer.extract_code_terms(sample_posts)
    print("\nCode Terms Found:")
    print(code_terms)
