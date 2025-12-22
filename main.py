#!/usr/bin/env python3
"""
X Reply Bot - Main Bot
======================
Active engagement bot that posts, replies, and quotes.

This script:
1. Scans timeline and mentions
2. AI decides best action
3. Generates content in your voice
4. Posts within rate limits
5. Learns from engagement results

Run with: python main.py
Dry run:  python main.py --dry-run
Stop:     Ctrl+C
"""

import sys
import time
import signal
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import get_logger
from src.utils.scheduler import Scheduler
from src.utils.keep_alive import start_keep_alive, stop_keep_alive
from src.core.x_client import XClient
from src.core.openrouter_client import OpenRouterClient
from src.core.rate_limiter import RateLimiter
from src.learning.personality_engine import PersonalityEngine
from src.learning.traction_predictor import TractionPredictor
from src.learning.style_analyzer import StyleAnalyzer
from src.reasoning.decision_maker import DecisionMaker
from src.reasoning.content_generator import ContentGenerator
from src.reasoning.safety_checker import SafetyChecker
from src.actions.poster import Poster
from src.actions.replier import Replier
from src.actions.quoter import Quoter


class XReplyBot:
    """
    Main X Reply Bot.
    
    Orchestrates all components for active engagement:
    - Timeline scanning
    - AI decision making
    - Content generation
    - Action execution
    - Engagement learning
    """
    
    def __init__(self, dry_run: bool = False, verbose: bool = True, x_client=None, openrouter_client=None, rate_limiter=None):
        """
        Initialize the bot.
        
        Args:
            dry_run: If True, don't actually post
            verbose: Show detailed output
            x_client: Injected XClient
            openrouter_client: Injected OpenRouterClient
            rate_limiter: Injected RateLimiter
        """
        self.dry_run = dry_run
        self.verbose = verbose
        self.running = False
        
        self.x_client = x_client
        self.ai_client = openrouter_client
        self.limiter = rate_limiter
        
        self.log = get_logger()
        if verbose:
            self.log.banner()
        
        if dry_run:
            self.log.warning("DRY RUN MODE - No actual posts will be made")
        
        if verbose:
            self.log.header("Bot Initialization")
        
        # Load env
        load_dotenv()
        
        # Initialize all components
        self._init_components()
        
        # Stats
        self.stats = {
            "started": datetime.now(),
            "actions_taken": 0,
            "posts": 0,
            "replies": 0,
            "quotes": 0,
            "skips": 0,
            "errors": 0
        }
    
    def _init_components(self) -> None:
        """Initialize all bot components."""
        # Core clients
        if not self.x_client:
            try:
                self.x_client = XClient()
                self.log.success(f"X Client: @{self.x_client.me.username}")
            except Exception as e:
                self.log.error(f"X Client failed: {e}")
                raise RuntimeError("Cannot run without X Client")
        
        if not self.ai_client:
            try:
                self.ai_client = OpenRouterClient()
                self.log.success("OpenRouter Client initialized")
            except Exception as e:
                self.log.warning(f"OpenRouter failed: {e}")
                self.log.info("Will use fallback content generation")
                self.ai_client = None
        
        # Rate limiting
        if not self.limiter:
            self.limiter = RateLimiter()
            self.log.success("Rate Limiter initialized")
        
        # Learning components
        self.personality = PersonalityEngine()
        self.log.success("Personality Engine loaded")
        
        self.predictor = TractionPredictor(openrouter_client=self.ai_client)
        self.log.success("Traction Predictor loaded")
        
        # Reasoning
        self.decision_maker = DecisionMaker(
            openrouter_client=self.ai_client,
            rate_limiter=self.limiter,
            traction_predictor=self.predictor,
            personality_engine=self.personality
        )
        self.log.success("Decision Maker initialized")
        
        self.content_gen = ContentGenerator(
            openrouter_client=self.ai_client,
            personality_engine=self.personality
        )
        self.log.success("Content Generator initialized")
        
        self.safety = SafetyChecker(rate_limiter=self.limiter)
        self.log.success("Safety Checker initialized")
        
        # Actions
        self.poster = Poster(
            x_client=self.x_client,
            content_generator=self.content_gen,
            safety_checker=self.safety,
            rate_limiter=self.limiter
        )
        
        self.replier = Replier(
            x_client=self.x_client,
            content_generator=self.content_gen,
            safety_checker=self.safety,
            rate_limiter=self.limiter
        )
        
        self.quoter = Quoter(
            x_client=self.x_client,
            content_generator=self.content_gen,
            safety_checker=self.safety,
            rate_limiter=self.limiter
        )
        
        self.log.success("Action handlers initialized")
        
        # Scheduler
        self.scheduler = Scheduler()
        self.log.success("Scheduler initialized")
    
    def display_status(self) -> None:
        """Display current bot status."""
        print("\n" + self.limiter.display_status())
        
        runtime = datetime.now() - self.stats["started"]
        
        print("\n╔════════════════════════════════════════╗")
        print("║         SESSION STATS                  ║")
        print("╠════════════════════════════════════════╣")
        print(f"║ Runtime: {str(runtime).split('.')[0]:<28} ║")
        print(f"║ Actions: {self.stats['actions_taken']:<29} ║")
        print(f"║   Posts:   {self.stats['posts']:<27} ║")
        print(f"║   Replies: {self.stats['replies']:<27} ║")
        print(f"║   Quotes:  {self.stats['quotes']:<27} ║")
        print(f"║ Skips: {self.stats['skips']:<31} ║")
        print(f"║ Errors: {self.stats['errors']:<30} ║")
        print("╚════════════════════════════════════════╝")
    
    def scan_timeline(self) -> list:
        """Scan timeline for opportunities."""
        self.log.info("Scanning timeline...")
        
        try:
            timeline = self.x_client.get_timeline(max_results=50)
            self.log.stats("Timeline tweets", len(timeline), "cyan")
            return timeline
        except Exception as e:
            self.log.error(f"Timeline scan failed: {e}")
            return []
    
    def scan_mentions(self) -> list:
        """Scan for mentions."""
        self.log.info("Checking mentions...")
        
        try:
            mentions = self.x_client.get_mentions(max_results=20)
            if mentions:
                self.log.stats("New mentions", len(mentions), "yellow")
            return mentions
        except Exception as e:
            self.log.error(f"Mentions scan failed: {e}")
            return []
    
    def execute_action(self, decision: dict) -> dict:
        """
        Execute a decided action.
        
        Args:
            decision: Decision dict from decision maker
            
        Returns:
            Result dict
        """
        action = decision.get("action")
        target = decision.get("target")
        content = decision.get("content")  # AI may pre-generate
        
        self.log.divider()
        self.log.info(self.decision_maker.format_decision(decision))
        
        if action == "skip":
            self.stats["skips"] += 1
            return {"success": True, "action": "skip", "reason": decision.get("reason")}
        
        if action == "post":
            result = self.poster.post(
                content=content,
                dry_run=self.dry_run
            )
            if result.get("success"):
                self.stats["posts"] += 1
                self.stats["actions_taken"] += 1
                self.log.action("post", result.get("content", ""))
        
        elif action == "reply":
            if not target:
                return {"success": False, "error": "No target for reply"}
            
            result = self.replier.reply(
                target_tweet=target,
                content=content,
                dry_run=self.dry_run
            )
            if result.get("success"):
                self.stats["replies"] += 1
                self.stats["actions_taken"] += 1
                self.log.action("reply", result.get("content", ""))
        
        elif action == "quote":
            if not target:
                return {"success": False, "error": "No target for quote"}
            
            result = self.quoter.quote(
                target_tweet=target,
                content=content,
                dry_run=self.dry_run
            )
            if result.get("success"):
                self.stats["quotes"] += 1
                self.stats["actions_taken"] += 1
                self.log.action("quote", result.get("content", ""))
        
        else:
            result = {"success": False, "error": f"Unknown action: {action}"}
        
        if not result.get("success"):
            self.stats["errors"] += 1
            self.log.error(f"Action failed: {result.get('error')}")
        
        return result
    
    def run_cycle(self) -> dict:
        """
        Run one bot cycle.
        
        Returns:
            Cycle result dict
        """
        self.log.header("Action Cycle")
        
        # Check if we can act
        usage = self.limiter.get_usage()
        if not usage["can_act"]:
            self.log.warning("Daily limit reached!")
            return {"success": False, "reason": "limit_reached"}
        
        # Check timing
        if not self.scheduler.is_active_hour():
            next_active = self.scheduler.get_next_active_time()
            self.log.info(f"Outside active hours. Next: {next_active.strftime('%H:%M')}")
            return {"success": False, "reason": "inactive_hours"}
        
        # Scan
        timeline = self.scan_timeline()
        mentions = self.scan_mentions()
        
        if not timeline and not mentions:
            self.log.warning("No content to engage with")
            return {"success": False, "reason": "no_content"}
        
        # Decide with AI
        if self.ai_client:
            decision = self.decision_maker.decide_with_ai(
                timeline=timeline,
                mentions=mentions
            )
        else:
            decision = self.decision_maker.decide(
                timeline=timeline,
                mentions=mentions
            )
        
        # Execute
        result = self.execute_action(decision)
        
        # Show current status
        if self.verbose:
            self.display_status()
        
        return result
    
    def run_single(self) -> None:
        """Run a single action cycle."""
        self.log.header("Single Action Mode")
        result = self.run_cycle()
        print(f"\nResult: {result}")
    
    def run_continuous(self) -> None:
        """Run continuous bot loop."""
        self.running = True
        
        self.log.header("Starting Continuous Mode")
        print("Press Ctrl+C to stop\n")
        
        # Display personality
        print(self.personality.describe())
        
        while self.running:
            try:
                # Run a cycle
                result = self.run_cycle()
                
                if result.get("reason") == "limit_reached":
                    # Wait until tomorrow
                    next_time = self.limiter.get_next_available_time()
                    if next_time:
                        self.log.info(f"Waiting until {next_time.strftime('%Y-%m-%d %H:%M')}")
                        while datetime.now() < next_time and self.running:
                            time.sleep(60)
                    continue
                
                if result.get("reason") == "inactive_hours":
                    # Wait until active
                    next_active = self.scheduler.get_next_active_time()
                    self.log.info(f"Waiting until {next_active.strftime('%H:%M')}")
                    self.scheduler.wait_until(next_active)
                    continue
                
                # Wait for next action - FREE TIER: 1 read per 15 min
                if result.get("success") and result.get("action") != "skip":
                    # Successful action - wait 15-20 min (API limit)
                    interval = self.scheduler.get_random_interval(15, 20)
                    self.log.info(f"Next cycle in {interval} minutes (free tier limit)...")
                    interval *= 60  # Convert to seconds
                else:
                    # Skip or error - still must wait 15 min due to read limits
                    interval = self.scheduler.get_random_interval(15, 18)
                    self.log.info(f"Next check in {interval} minutes...")
                    interval *= 60
                
                # Sleep in chunks for interrupt handling
                end_time = datetime.now() + timedelta(seconds=interval)
                while datetime.now() < end_time and self.running:
                    time.sleep(30)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.log.error(f"Cycle error: {e}")
                self.stats["errors"] += 1
                time.sleep(60)
        
        self.log.header("Bot Stopped")
        self.display_status()
    
    def stop(self) -> None:
        """Stop the bot."""
        self.running = False
        self.scheduler.stop()
        self.log.info("Stopping bot...")


class Supervisor:
    """
    Bot Supervisor.
    Manages switching between Learning Mode and Active Mode.
    """
    
    def __init__(self, dry_run: bool = False, verbose: bool = True):
        self.dry_run = dry_run
        self.verbose = verbose
        self.running = False
        
        self.log = get_logger()
        self.log.banner()
        self.log.header("Supervisor Initialization")
        
        # Load env
        load_dotenv()
        
        # State
        self.DATA_PATH = Path(__file__).parent / "data"
        self.DATA_PATH.mkdir(exist_ok=True)
        self.state_file = self.DATA_PATH / "bot_state.json"
        self.config_file = Path(__file__).parent / "config" / "bot_config.json"
        
        self.state = self._load_state()
        self.config = self._load_config()
        
        # Shared Components
        self.x_client = None
        self.ai_client = None
        self.limiter = None
        self._init_shared_components()
        
        # Sub-systems
        # We delay instantiation until needed or init them here
        from learn_mode import LearningMode
        self.learner = LearningMode(
            x_client=self.x_client, 
            openrouter_client=self.ai_client,
            verbose=verbose
        )
        
        self.bot = XReplyBot(
            dry_run=dry_run, 
            verbose=verbose, 
            x_client=self.x_client,
            openrouter_client=self.ai_client,
            rate_limiter=self.limiter
        )
        
    def _load_state(self) -> dict:
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default state
        return {
            "first_run": datetime.now().isoformat(),
            "mode": "learning",
            "last_active": None
        }

    def _save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def _load_config(self) -> dict:
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}

    def _init_shared_components(self):
        try:
            self.x_client = XClient()
            self.log.success(f"X Client: @{self.x_client.me.username}")
        except Exception as e:
            self.log.error(f"X Client failed: {e}")
            
        try:
            self.ai_client = OpenRouterClient()
            self.log.success("OpenRouter Client initialized")
        except:
            self.ai_client = None
            
        self.limiter = RateLimiter()

    def get_days_elapsed(self) -> float:
        start_date = datetime.fromisoformat(self.state["first_run"])
        return (datetime.now() - start_date).total_seconds() / 86400

    def run(self):
        self.running = True
        self.log.header("Supervisor Started")
        
        learning_days = self.config.get("behavior", {}).get("learning_period_days", 14)
        
        print("Press Ctrl+C to stop\n")
        
        while self.running:
            try:
                days = self.get_days_elapsed()
                
                # Determine Mode
                if days < learning_days:
                    mode = "learning"
                    remaining = learning_days - days
                    status = f"LEARNING MODE (Day {int(days)+1}/{learning_days}) - {remaining:.1f} days left"
                else:
                    mode = "active"
                    status = f"ACTIVE MODE (Day {int(days)+1})"
                
                # State transition log
                if self.state["mode"] != mode:
                    self.log.info(f"Switching mode: {self.state['mode']} -> {mode}")
                    self.state["mode"] = mode
                    self._save_state()
                
                # Run Cycle
                if mode == "learning":
                    print(f"\r[Supervisor] {status}...", end="")
                    self.learner.step()
                    # Learning mode is slow (15 min intervals), so we sleep less here to check often
                    # but learner.step() checks its own timers.
                    time.sleep(60) 
                    
                else:
                    # Active Mode
                    print(f"\r[Supervisor] {status}...", end="")
                    result = self.bot.run_cycle()
                    
                    # Handle bot's required waits
                    if result.get("reason") == "limit_reached":
                        time.sleep(60)
                    elif result.get("reason") == "inactive_hours":
                         # Bot scheduler handles this logic usually, but here we just wait
                         time.sleep(300)
                    else:
                        # Success or skip
                        time.sleep(60)

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.log.error(f"Supervisor error: {e}")
                time.sleep(60)
        
        self.log.header("Supervisor Stopped")

    def stop(self):
        self.running = False


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="X Reply Bot - Supervisor Mode")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Run without actually posting")
    parser.add_argument("--quiet", "-q", action="store_true", help="Reduce output verbosity")
    args = parser.parse_args()
    
    keep_alive = start_keep_alive()
    
    supervisor = Supervisor(dry_run=args.dry_run, verbose=not args.quiet)
    
    def signal_handler(sig, frame):
        print("\n")
        supervisor.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    supervisor.run()


if __name__ == "__main__":
    main()
