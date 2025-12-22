"""
Personality Engine
Builds and maintains the bot's personality from config and learning.
Synthesizes your raw, no-filter, based personality.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

CONFIG_PATH = Path(__file__).parent.parent.parent / "config"
DATA_PATH = Path(__file__).parent.parent.parent / "data"


class PersonalityEngine:
    """
    Manages the bot's personality.
    
    Combines:
    - Base config personality (raw, no-filter, based)
    - Learned patterns from target accounts
    - Engagement feedback adjustments
    """
    
    def __init__(self):
        """Initialize personality engine."""
        self._load_config()
        self._load_learned_style()
        self.active_personality = self._synthesize()
    
    def _load_config(self) -> None:
        """Load base personality from config."""
        config_file = CONFIG_PATH / "bot_config.json"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.base_personality = config.get("personality", {})
        else:
            # Default raw personality
            self.base_personality = {
                "name": "ReplyGuyBot",
                "style": "raw_no_filter_based",
                "myers_briggs": "ISTP/ESTP",
                "core_traits": [
                    "Direct to the point of brutality",
                    "Values authenticity over everything",
                    "Low tolerance for stupidity",
                    "Action-oriented, hates overthinking"
                ],
                "communication": {
                    "caps_when_serious": True,
                    "short_sentences": True,
                    "sarcastic_dark_humor": True,
                    "uses_code_terms": True
                },
                "shitpost_ratio": 0.35,
                "ragebait_ratio": 0.15,
                "valuable_info_ratio": 0.50
            }
    
    def _load_learned_style(self) -> None:
        """Load learned style from history."""
        history_file = DATA_PATH / "learning_history.json"
        
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
                    self.learned_style = history.get("aggregated_style", {})
            except:
                self.learned_style = {}
        else:
            self.learned_style = {}
    
    def _synthesize(self) -> Dict:
        """
        Synthesize active personality from base + learned.
        
        Returns:
            Complete personality dict
        """
        personality = dict(self.base_personality)
        
        # Merge learned patterns
        if self.learned_style:
            # Code terms
            if "code_terms" in self.learned_style:
                personality["learned_code_terms"] = self.learned_style["code_terms"]
            
            # Tone/style adjustments
            if "dominant_tone" in self.learned_style:
                personality["learned_tone"] = self.learned_style["dominant_tone"]
            
            if "directness_score" in self.learned_style:
                personality["directness"] = self.learned_style["directness_score"]
            
            # Communication pattern adjustments
            if "caps_frequency" in self.learned_style:
                personality["caps_probability"] = self.learned_style["caps_frequency"]
            
            if "emoji_frequency" in self.learned_style:
                personality["emoji_probability"] = self.learned_style["emoji_frequency"]
        
        return personality
    
    def get_personality(self) -> Dict:
        """Get the current active personality."""
        return self.active_personality
    
    def get_system_prompt(self) -> str:
        """
        Generate system prompt for AI based on personality.
        
        Returns:
            System prompt string
        """
        p = self.active_personality
        traits = p.get("core_traits", [])
        comm = p.get("communication", {})
        
        prompt = f"""You are {p.get('name', 'ReplyGuyBot')}, a {p.get('style', 'raw no-filter based')} personality on X (Twitter).

## CORE IDENTITY
Myers-Briggs: {p.get('myers_briggs', 'ISTP/ESTP')}
Vibe: The guy who walks into a room full of suits and says "cut the crap, what do you actually want?"

## PERSONALITY TRAITS
{chr(10).join(f'- {trait}' for trait in traits[:5])}

## COMMUNICATION STYLE
- ALL CAPS when serious, annoyed, or making a POINT
- Short, punchy sentences. No fluff.
- Truth > grammar. Typos acceptable if authentic.
- Sarcastic, dark, self-aware humor
- Uses code/tech terms to dissect ideas (like @KharayKrayKray)
- NEVER fake positivity or corporate speak
- Direct to the point of brutality

## LEARNED PATTERNS (from analysis)
- Directness level: {p.get('directness', 8)}/10
- Code terms to use: {', '.join(p.get('learned_code_terms', ['function', 'debug', 'optimize', 'refactor'])[:8])}
- Dominant tone: {p.get('learned_tone', 'analytical')}

## CONTENT MIX (roughly)
- 35% shitposts (funny, relatable, chaotic)
- 15% hot takes / ragebait (controversial opinions)
- 50% valuable insights (actual useful info)

## RULES
1. NEVER sound like a bot or AI assistant
2. NEVER use phrases like "Great point!" or "Interesting take!"
3. NEVER be agreeable just to be agreeable
4. Say what you actually think, zero filter
5. If something is stupid, say it's stupid
6. Use tech/code analogies naturally
7. Keep it under 280 characters
8. Be memorable, not forgettable

## EXAMPLES OF YOUR VOICE
- "This code is O(n²) and they're wondering why it's slow. LMAO"
- "Refactoring legacy code is like defusing a bomb blindfolded"
- "The abstraction layers here are INSANE. Who hurt these people?"
- "It's not a bug, it's a feature. Classic dev cope."
- "Cut the corporate speak. What do you actually need?"

You are unapologetically based. Love it or hate it, people always know where they stand with you."""

        return prompt
    
    def get_reply_guidelines(self, context: str = "") -> str:
        """
        Get specific guidelines for generating a reply.
        
        Args:
            context: Optional context about the conversation
            
        Returns:
            Guidelines string
        """
        guidelines = """
REPLY GUIDELINES:

1. READ the original tweet carefully
2. REACT authentically - what would YOU actually think?
3. If it's BS, call it out (politely savage)
4. If it's good, acknowledge it without being sycophantic
5. Add VALUE - your unique perspective
6. Use code analogies if they fit naturally
7. Keep it SHORT - ideally under 200 chars
8. No hashtags in replies
9. One @mention max (only if replying to specific person)

AVOID:
- "This is so true!"
- "Great thread!"
- "Couldn't agree more!"
- Empty validation
- Obvious statements
- Being generic

BE:
- Specific
- Opinionated  
- Memorable
- Authentic
- Direct
"""
        if context:
            guidelines += f"\nCONTEXT: {context}"
        
        return guidelines
    
    def adjust_for_engagement(self, engagement_data: Dict) -> None:
        """
        Adjust personality based on engagement feedback.
        
        Args:
            engagement_data: Dict with engagement metrics
        """
        # This would be called after analyzing what posts performed well
        
        # If sarcasm is working, increase it
        if engagement_data.get("sarcasm_performance", 0) > 0.7:
            if "humor_weight" not in self.active_personality:
                self.active_personality["humor_weight"] = 1.0
            self.active_personality["humor_weight"] = min(1.5, 
                self.active_personality["humor_weight"] * 1.1)
        
        # If CAPS posts perform well, use more
        if engagement_data.get("caps_performance", 0) > 0.6:
            self.active_personality["caps_probability"] = min(0.5,
                self.active_personality.get("caps_probability", 0.2) + 0.05)
        
        # Save adjustments
        self._save_adjustments()
    
    def _save_adjustments(self) -> None:
        """Save personality adjustments."""
        # Could save to a personality_adjustments.json for persistence
        pass
    
    def get_content_type_probability(self) -> Dict[str, float]:
        """
        Get probability distribution for content types.
        
        Returns:
            Dict with content type probabilities
        """
        return {
            "shitpost": self.active_personality.get("shitpost_ratio", 0.35),
            "ragebait": self.active_personality.get("ragebait_ratio", 0.15),
            "valuable": self.active_personality.get("valuable_info_ratio", 0.50)
        }
    
    def should_use_caps(self, content: str, sentiment: str = "neutral") -> bool:
        """
        Decide if CAPS should be used.
        
        Args:
            content: The content being generated
            sentiment: Detected sentiment
            
        Returns:
            True if should use caps
        """
        import random
        
        # Higher chance for serious/annoyed sentiment
        if sentiment in ["annoyed", "serious", "emphatic"]:
            return random.random() < 0.6
        
        # Base probability from config
        base_prob = self.active_personality.get("caps_probability", 0.2)
        return random.random() < base_prob
    
    def get_code_terms(self) -> List[str]:
        """Get list of code terms to potentially use."""
        default_terms = [
            "function", "debug", "optimize", "refactor", "legacy",
            "abstraction", "interface", "algorithm", "loop", "recursion",
            "deploy", "production", "staging", "bug", "feature",
            "O(n)", "complexity", "runtime", "memory leak", "race condition"
        ]
        
        learned = self.active_personality.get("learned_code_terms", [])
        
        # Combine and dedupe
        all_terms = list(set(default_terms + learned))
        return all_terms
    
    def describe(self) -> str:
        """Get a human-readable personality description."""
        p = self.active_personality
        
        desc = f"""
╔══════════════════════════════════════════════════╗
║           BOT PERSONALITY PROFILE                ║
╠══════════════════════════════════════════════════╣
║ Name: {p.get('name', 'Unknown'):<42} ║
║ Style: {p.get('style', 'raw_no_filter'):<41} ║
║ Myers-Briggs: {p.get('myers_briggs', 'ISTP'):<34} ║
╠══════════════════════════════════════════════════╣
║ Content Mix:                                     ║
║   Shitposts: {p.get('shitpost_ratio', 0.35)*100:>5.1f}%                            ║
║   Hot Takes: {p.get('ragebait_ratio', 0.15)*100:>5.1f}%                            ║
║   Value:     {p.get('valuable_info_ratio', 0.5)*100:>5.1f}%                            ║
╠══════════════════════════════════════════════════╣
║ Directness: {p.get('directness', 8)}/10 (brutally honest)          ║
║ Uses CAPS: {'Yes' if p.get('communication', {}).get('caps_when_serious') else 'No':<37} ║
║ Code Terms: {len(self.get_code_terms())} terms loaded                     ║
╚══════════════════════════════════════════════════╝
"""
        return desc


# Test
if __name__ == "__main__":
    engine = PersonalityEngine()
    
    print(engine.describe())
    print("\n" + "="*50)
    print("SYSTEM PROMPT:")
    print("="*50)
    print(engine.get_system_prompt()[:1500] + "...")
