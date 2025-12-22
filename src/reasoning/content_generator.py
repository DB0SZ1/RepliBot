"""
Content Generator
Generates posts, replies, and quotes in your raw, no-filter voice.
"""

import random
import re
from typing import Dict, Optional, List
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent.parent / "data"


class ContentGenerator:
    """
    Generates content matching the bot's personality.
    
    Features:
    - Raw, no-filter voice
    - Code/tech terminology
    - ALL CAPS for emphasis
    - Sarcastic dark humor
    - Short punchy sentences
    """
    
    def __init__(self, openrouter_client=None, personality_engine=None):
        """
        Initialize generator.
        
        Args:
            openrouter_client: AI client for generation
            personality_engine: Personality engine
        """
        self.ai_client = openrouter_client
        self.personality = personality_engine
    
    def generate_reply(
        self,
        tweet: Dict,
        style_hint: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a reply to a tweet.
        
        Args:
            tweet: Tweet to reply to
            style_hint: Optional style hint (sarcastic, supportive, etc)
            
        Returns:
            Generated reply text
        """
        if not self.ai_client:
            return self._generate_fallback_reply(tweet)
        
        # Get personality and learned style
        personality = {}
        learned_style = {}
        
        if self.personality:
            personality = self.personality.get_personality()
            # Get learned style from personality engine
            learned_style = {
                "directness_score": personality.get("directness", 8),
                "uses_code_terms": personality.get("communication", {}).get("uses_code_terms", True),
                "code_terms_found": personality.get("learned_code_terms", []),
                "dominant_tone": personality.get("learned_tone", "analytical")
            }
        
        reply = self.ai_client.generate_reply(
            tweet=tweet,
            personality=personality,
            learned_style=learned_style
        )
        
        if reply:
            reply = self._post_process(reply, style_hint)
        
        return reply
    
    def generate_post(
        self,
        topic: Optional[str] = None,
        style: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate an original post.
        
        Args:
            topic: Topic to post about
            style: shitpost, ragebait, or valuable
            
        Returns:
            Generated post text
        """
        if not self.ai_client:
            return self._generate_fallback_post(topic)
        
        # Determine content type if not specified
        if not style and self.personality:
            probs = self.personality.get_content_type_probability()
            r = random.random()
            if r < probs.get("shitpost", 0.35):
                style = "shitpost"
            elif r < probs.get("shitpost", 0.35) + probs.get("ragebait", 0.15):
                style = "ragebait"
            else:
                style = "valuable"
        
        personality = {}
        if self.personality:
            personality = self.personality.get_personality()
        
        # Build prompt
        prompt = self._build_post_prompt(topic, style, personality)
        
        system_prompt = None
        if self.personality:
            system_prompt = self.personality.get_system_prompt()
        
        post = self.ai_client.generate(
            prompt=prompt,
            task="content_generation",
            system_prompt=system_prompt
        )
        
        if post:
            post = self._post_process(post, style)
        
        return post
    
    def generate_quote(
        self,
        tweet: Dict,
        angle: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a quote tweet.
        
        Args:
            tweet: Tweet to quote
            angle: How to frame the quote (agree, disagree, add context, etc)
            
        Returns:
            Generated quote text
        """
        if not self.ai_client:
            return self._generate_fallback_quote(tweet)
        
        personality = {}
        if self.personality:
            personality = self.personality.get_personality()
        
        prompt = f"""Generate a quote tweet for this post. Your voice is raw, no-filter, based.

TWEET BEING QUOTED:
"{tweet.get('text', '')}"
Author: @{tweet.get('author_username', 'unknown')}

YOUR APPROACH: {angle or "Add your unique perspective - agree, disagree, or expand"}

RULES:
- MAX 250 characters (leave room for quoted tweet)
- Be DIRECT - no fluff
- Add VALUE with your perspective
- Use code/tech analogies if relevant
- Can be sarcastic or supportive based on the content
- Sound like a real person with opinions

Generate ONLY the quote text:"""

        system_prompt = None
        if self.personality:
            system_prompt = self.personality.get_system_prompt()
        
        quote = self.ai_client.generate(
            prompt=prompt,
            task="content_generation", 
            system_prompt=system_prompt
        )
        
        if quote:
            quote = self._post_process(quote, "quote")
            # Ensure shorter for quotes
            if len(quote) > 250:
                quote = quote[:247] + "..."
        
        return quote
    
    def _build_post_prompt(
        self,
        topic: Optional[str],
        style: str,
        personality: Dict
    ) -> str:
        """Build prompt for post generation."""
        
        style_guides = {
            "shitpost": """
CREATE A SHITPOST:
- Funny, relatable, chaotic energy
- Can be self-deprecating
- Tech/code humor preferred
- Absurdist observations welcome
- The kind of tweet that makes people go "lmao same"
""",
            "ragebait": """
CREATE A HOT TAKE:
- Controversial opinion (but defensible)
- Something people will argue about
- Challenge common wisdom
- Start with "Unpopular opinion:" or "Hot take:" or just dive in
- Be provocative but not offensive
""",
            "valuable": """
CREATE A VALUABLE POST:
- Share genuine insight or tip
- Based on real experience
- Something people can learn from
- Can be wrapped in humor/sarcasm
- The kind of tweet people screenshot
"""
        }
        
        style_guide = style_guides.get(style, style_guides["valuable"])
        
        topic_line = f"TOPIC: {topic}" if topic else "TOPIC: Choose something relevant to tech/dev life"
        
        code_terms = personality.get("learned_code_terms", ["debug", "refactor", "deploy", "production"])
        
        prompt = f"""{style_guide}

{topic_line}

YOUR VOICE:
- Raw, no-filter, unapologetically based
- Direct to the point of brutality
- Uses code terms naturally: {', '.join(code_terms[:5])}
- ALL CAPS for emphasis when needed
- Short punchy sentences

RULES:
- MAX 280 characters
- No hashtags
- No emojis (unless absolutely necessary for the joke)
- Sound like a REAL person, not a bot

Generate ONLY the tweet text:"""

        return prompt
    
    def _generate_fallback_reply(self, tweet: Dict) -> str:
        """Generate a simple reply without AI."""
        text = tweet.get("text", "").lower()
        
        # Simple pattern matching for fallback replies
        if "?" in tweet.get("text", ""):
            replies = [
                "Honestly? It depends on the context.",
                "The real answer is: it depends.",
                "Short answer: yes. Long answer: it's complicated."
            ]
        elif any(word in text for word in ["hate", "annoying", "frustrating"]):
            replies = [
                "Facts. No notes.",
                "Say it louder.",
                "The accuracy here is painful."
            ]
        elif any(word in text for word in ["love", "great", "amazing"]):
            replies = [
                "Valid take actually.",
                "Can't argue with that.",
                "Rare W on the timeline."
            ]
        else:
            replies = [
                "This is the content I'm here for.",
                "Real talk right here.",
                "Saving this one."
            ]
        
        return random.choice(replies)
    
    def _generate_fallback_post(self, topic: Optional[str]) -> str:
        """Generate a simple post without AI."""
        posts = [
            "The best code is the code you don't have to write.",
            "Debugging is just being a detective in a mystery you wrote yourself.",
            "Production is just staging that people use.",
            "The real tech debt was the features we shipped along the way.",
            "If it works, don't touch it. If it doesn't work, also don't touch it. Just rewrite it."
        ]
        return random.choice(posts)
    
    def _generate_fallback_quote(self, tweet: Dict) -> str:
        """Generate a simple quote without AI."""
        quotes = [
            "This right here.",
            "More people need to see this.",
            "Saving this for future reference.",
            "The accuracy is concerning.",
            "Rare timeline W."
        ]
        return random.choice(quotes)
    
    def _post_process(self, text: str, style: Optional[str] = None) -> str:
        """
        Post-process generated text.
        
        Args:
            text: Generated text
            style: Content style
            
        Returns:
            Cleaned text
        """
        # Remove quotes if AI wrapped the response
        text = text.strip().strip('"').strip("'")
        
        # Remove any "Sure, here's..." preamble
        preambles = [
            "Here's", "Sure,", "Here is", "I'll", "Let me",
            "Okay,", "Alright,", "So,", "Well,"
        ]
        for p in preambles:
            if text.lower().startswith(p.lower()):
                # Find end of preamble
                colon = text.find(":")
                newline = text.find("\n")
                if colon > 0 and colon < 50:
                    text = text[colon + 1:].strip()
                elif newline > 0 and newline < 50:
                    text = text[newline + 1:].strip()
        
        # Remove hashtags (we don't use them)
        text = re.sub(r'#\w+', '', text).strip()
        
        # Limit length
        if len(text) > 280:
            text = text[:277] + "..."
        
        # Occasionally add CAPS for emphasis (if style calls for it)
        if style in ["ragebait", "shitpost"] and random.random() < 0.2:
            words = text.split()
            if len(words) > 3:
                # Capitalize a random word for emphasis
                idx = random.randint(1, len(words) - 2)
                if len(words[idx]) > 3:
                    words[idx] = words[idx].upper()
                text = " ".join(words)
        
        return text
    
    def inject_typo(self, text: str, probability: float = 0.02) -> str:
        """
        Occasionally inject typos for authenticity.
        
        Args:
            text: Original text
            probability: Chance of typo per word
            
        Returns:
            Text with possible typos
        """
        if random.random() > probability * len(text.split()):
            return text
        
        words = text.split()
        if len(words) < 3:
            return text
        
        # Pick a random word to typo
        idx = random.randint(1, len(words) - 1)
        word = words[idx]
        
        if len(word) < 4:
            return text
        
        # Simple typo: swap two adjacent letters
        pos = random.randint(1, len(word) - 2)
        typo_word = word[:pos] + word[pos+1] + word[pos] + word[pos+2:]
        words[idx] = typo_word
        
        return " ".join(words)


# Test
if __name__ == "__main__":
    generator = ContentGenerator()
    
    # Test fallback replies
    mock_tweet = {
        "text": "Why is debugging so frustrating sometimes?",
        "author_username": "dev_user"
    }
    
    print("Fallback reply:", generator._generate_fallback_reply(mock_tweet))
    print("Fallback post:", generator._generate_fallback_post(None))
    print("Fallback quote:", generator._generate_fallback_quote(mock_tweet))
    
    # Test typo injection
    text = "This is a perfectly normal sentence without any errors."
    print("\nOriginal:", text)
    for _ in range(5):
        typo = generator.inject_typo(text, probability=0.5)
        if typo != text:
            print("With typo:", typo)
            break
