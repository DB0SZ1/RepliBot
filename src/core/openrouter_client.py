"""
OpenRouter AI Client
Handles all AI model interactions using user's preferred FREE models:
- openai/gpt-oss-120b (primary)
- google/gemini-2.5-flash-lite-preview-09-2025 (fast)
- qwen/qwen3-next-80b-a3b-instruct (reasoning)
- openai/gpt-5-nano (quick)
- tngtech/tng-r1t-chimera:free (learning)
"""

import os
import json
import httpx
import asyncio
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from datetime import datetime
import time

CONFIG_PATH = Path(__file__).parent.parent.parent / "config"


class OpenRouterClient:
    """OpenRouter API client for AI model interactions."""
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize OpenRouter client."""
        if config_path:
            cfg_file = Path(config_path)
        else:
            cfg_file = CONFIG_PATH / "openrouter_config.json"
        
        # Try file, fall back to env
        if cfg_file.exists():
            with open(cfg_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "api_key": os.getenv("OPENROUTER_API_KEY"),
                "models": {
                    "primary": "openai/gpt-oss-120b",
                    "fast": "google/gemini-2.5-flash-lite-preview-09-2025",
                    "reasoning": "qwen/qwen3-next-80b-a3b-instruct",
                    "nano": "openai/gpt-5-nano",
                    "chimera": "tngtech/tng-r1t-chimera:free"
                },
                "settings": {
                    "temperature": 0.85,
                    "max_tokens": 500,
                    "timeout_seconds": 60
                }
            }
        
        self.api_key = self.config.get("api_key") or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key not found!")
        
        self.models = self.config.get("models", {})
        self.settings = self.config.get("settings", {})
        self.model_rotation = self.config.get("model_rotation", {})
        
        # Track rate limits per model
        self._last_request_time: Dict[str, float] = {}
        self._request_count: Dict[str, int] = {}
        
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/x-reply-bot",
            "X-Title": "X Reply Bot"
        }
    
    def _select_model(self, task: str = "primary") -> str:
        """
        Select appropriate model for task.
        
        Args:
            task: Task type - 'learning', 'content_generation', 'decision_making', 'quick_analysis'
            
        Returns:
            Model identifier
        """
        # Check rotation config first
        if task in self.model_rotation:
            for model_key in self.model_rotation[task]:
                if model_key in self.models:
                    return self.models[model_key]
        
        # Fall back to model aliases
        if task in self.models:
            return self.models[task]
        
        # Default to primary
        return self.models.get("primary", "openai/gpt-oss-120b")
    
    def _enforce_rate_limit(self, model: str) -> None:
        """Enforce rate limiting between requests."""
        min_interval = self.config.get("rate_limits", {}).get("min_interval_seconds", 1)
        last_time = self._last_request_time.get(model, 0)
        elapsed = time.time() - last_time
        
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        
        self._last_request_time[model] = time.time()
    
    def generate(
        self,
        prompt: str,
        task: str = "primary",
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate text completion.
        
        Args:
            prompt: User prompt
            task: Task type for model selection
            system_prompt: Optional system message
            temperature: Override default temperature
            max_tokens: Override default max tokens
            response_format: 'json' for JSON output
            
        Returns:
            Generated text or None on error
        """
        model = self._select_model(task)
        self._enforce_rate_limit(model)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature or self.settings.get("temperature", 0.85),
            "max_tokens": max_tokens or self.settings.get("max_tokens", 500),
            "top_p": self.settings.get("top_p", 0.95)
        }
        
        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}
        
        timeout = self.settings.get("timeout_seconds", 60)
        max_retries = self.config.get("rate_limits", {}).get("max_retries", 3)
        retry_delay = self.config.get("rate_limits", {}).get("retry_delay_seconds", 5)
        
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(
                        f"{self.BASE_URL}/chat/completions",
                        headers=self._get_headers(),
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return data["choices"][0]["message"]["content"]
                    
                    elif response.status_code == 429:
                        # Rate limited, try fallback model
                        print(f"Rate limited on {model}, trying fallback...")
                        fallback = self.models.get("fast") or self.models.get("nano")
                        if fallback and fallback != model:
                            payload["model"] = fallback
                            continue
                        time.sleep(retry_delay * (attempt + 1))
                        
                    else:
                        print(f"OpenRouter error {response.status_code}: {response.text}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                        
            except httpx.TimeoutException:
                print(f"Timeout on {model}, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    
            except Exception as e:
                print(f"OpenRouter error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        return None
    
    def generate_json(
        self,
        prompt: str,
        task: str = "primary",
        system_prompt: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Generate structured JSON response.
        
        Args:
            prompt: User prompt
            task: Task type for model selection
            system_prompt: Optional system message
            
        Returns:
            Parsed JSON dict or None
        """
        response = self.generate(
            prompt=prompt,
            task=task,
            system_prompt=system_prompt,
            response_format="json"
        )
        
        if not response:
            return None
        
        # Try to parse JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            try:
                start = response.find("{")
                end = response.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(response[start:end])
            except:
                pass
            
            print(f"Failed to parse JSON: {response[:200]}...")
            return None
    
    def analyze_style(self, posts: List[str]) -> Optional[Dict]:
        """
        Analyze communication style from posts.
        
        Args:
            posts: List of post texts to analyze
            
        Returns:
            Style analysis dict
        """
        prompt = f"""Analyze the communication style of these posts. Be specific and quantitative.

POSTS:
{chr(10).join(f'- "{p}"' for p in posts[:20])}

Return JSON:
{{
    "avg_word_count": <number>,
    "uses_caps": <true/false>,
    "caps_frequency": <0.0-1.0>,
    "emoji_frequency": <0.0-1.0>,
    "common_emojis": ["list"],
    "slang_frequency": <0.0-1.0>,
    "common_slang": ["list"],
    "sentence_style": "short|medium|long|mixed",
    "humor_type": "sarcastic|dark|wholesome|absurd|mixed",
    "uses_code_terms": <true/false>,
    "code_terms_found": ["list"],
    "directness_score": <1-10, 10=brutally direct>,
    "formality_score": <1-10, 10=very formal>,
    "dominant_tone": "aggressive|casual|professional|chaotic|analytical"
}}"""

        return self.generate_json(
            prompt=prompt,
            task="learning",
            system_prompt="You are a communication style analyst. Return only valid JSON."
        )
    
    def predict_engagement(self, tweet: Dict, learned_patterns: Dict) -> Optional[Dict]:
        """
        Predict engagement potential for a tweet.
        
        Args:
            tweet: Tweet data dict
            learned_patterns: Learned engagement patterns
            
        Returns:
            Prediction dict with score and reasoning
        """
        prompt = f"""Predict engagement potential for this tweet.

TWEET:
- Text: "{tweet.get('text', '')}"
- Author followers: {tweet.get('author_followers', 0)}
- Current metrics: {tweet.get('metrics', {})}

LEARNED PATTERNS:
- Best performing topics: {learned_patterns.get('viral_topics', [])}
- Avg engagement rate: {learned_patterns.get('avg_engagement_rate', 0.05)}
- Best hours: {learned_patterns.get('best_hours', [9, 10, 11])}

Return JSON:
{{
    "traction_score": <0-100>,
    "viral_potential": "low|medium|high|viral",
    "should_engage": <true/false>,
    "best_action": "reply|quote|skip",
    "reasoning": "brief explanation",
    "suggested_angle": "how to approach this tweet"
}}"""

        return self.generate_json(
            prompt=prompt,
            task="quick_analysis",
            system_prompt="You are an engagement predictor. Be realistic, not optimistic."
        )
    
    def generate_reply(
        self,
        tweet: Dict,
        personality: Dict,
        learned_style: Dict
    ) -> Optional[str]:
        """
        Generate a reply in the bot's voice.
        
        Args:
            tweet: Tweet to reply to
            personality: Bot personality config
            learned_style: Learned communication patterns
            
        Returns:
            Generated reply text
        """
        traits = personality.get("core_traits", [])
        comm = personality.get("communication", {})
        
        prompt = f"""Generate a reply to this tweet. Match the personality EXACTLY.

TWEET TO REPLY TO:
"{tweet.get('text', '')}"
Author: @{tweet.get('author_username', 'unknown')}

YOUR PERSONALITY:
- Style: {personality.get('style', 'raw_no_filter')}
- Core traits: {', '.join(traits[:4])}
- CAPS when serious: {comm.get('caps_when_serious', True)}
- Short sentences: {comm.get('short_sentences', True)}
- Sarcastic dark humor: {comm.get('sarcastic_dark_humor', True)}
- Uses code terms: {comm.get('uses_code_terms', True)}

LEARNED STYLE (from @KharayKrayKray):
- Directness: {learned_style.get('directness_score', 8)}/10
- Uses code terms: {learned_style.get('uses_code_terms', True)}
- Common terms: {learned_style.get('code_terms_found', [])}
- Dominant tone: {learned_style.get('dominant_tone', 'analytical')}

RULES:
- MAX 280 characters
- Be BRUTALLY direct, cut the BS
- Use code/tech terms to dissect ideas when relevant
- Short punchy sentences preferred
- Can use ALL CAPS for emphasis on key points
- Sarcastic/dark humor allowed
- NO generic replies like "great point!" or "interesting!"
- Sound like a REAL person, not a bot

Generate ONLY the reply text, nothing else:"""

        response = self.generate(
            prompt=prompt,
            task="content_generation",
            system_prompt="You are a raw, no-filter reply guy. Be authentic, direct, occasionally brutal."
        )
        
        if response:
            # Clean up
            response = response.strip().strip('"')
            if len(response) > 280:
                response = response[:277] + "..."
        
        return response
    
    def decide_action(
        self,
        timeline: List[Dict],
        personality: Dict,
        learned_patterns: Dict,
        actions_remaining: Dict,
        recent_actions: List[Dict]
    ) -> Optional[Dict]:
        """
        AI decides the next best action.
        
        Args:
            timeline: Recent timeline tweets
            personality: Bot personality
            learned_patterns: Engagement patterns
            actions_remaining: Remaining action budget
            recent_actions: Recent bot actions (to avoid repetition)
            
        Returns:
            Decision dict with action, target, content
        """
        timeline_summary = []
        for t in timeline[:10]:
            timeline_summary.append({
                "id": t.get("id"),
                "text": t.get("text", "")[:100],
                "author": t.get("author_username"),
                "likes": t.get("metrics", {}).get("like_count", 0),
                "retweets": t.get("metrics", {}).get("retweet_count", 0)
            })
        
        prompt = f"""You are {personality.get('name', 'ReplyGuyBot')}, a {personality.get('style', 'raw_no_filter')} presence on X.

REMAINING BUDGET TODAY:
- Posts: {actions_remaining.get('posts', 0)}
- Quotes: {actions_remaining.get('quotes', 0)}  
- Replies: {actions_remaining.get('replies', 0)}

TIMELINE (latest tweets):
{json.dumps(timeline_summary, indent=2)}

RECENT ACTIONS (avoid repeating):
{json.dumps([a.get('tweet_id') for a in recent_actions[-5:]])}

LEARNED PATTERNS:
- Best topics: {learned_patterns.get('viral_topics', [])}
- Avg engagement: {learned_patterns.get('avg_engagement_rate', 0.05)}

YOUR PERSONALITY:
- Brutally direct, no BS
- Uses code terms to dissect ideas
- Sarcastic dark humor
- ALL CAPS when serious

TASK: Decide the next action.

Return JSON:
{{
    "action": "reply|quote|post|skip",
    "target_tweet_id": "id if reply/quote, null if post/skip",
    "content": "generated content for the action",
    "reasoning": "why this action",
    "engagement_prediction": <0-100>,
    "confidence": <0.0-1.0>
}}

If no good opportunities, action should be "skip".
Content should match your personality - raw, direct, uses tech/code analogies."""

        return self.generate_json(
            prompt=prompt,
            task="decision_making",
            system_prompt="You are the decision engine for an X reply bot. Return valid JSON."
        )


# Test
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    client = OpenRouterClient()
    
    # Test generation
    result = client.generate(
        "Say something brutally honest in under 50 words.",
        task="content_generation"
    )
    print(f"Generated: {result}")
