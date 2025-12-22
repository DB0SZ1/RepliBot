#!/usr/bin/env python3
"""
X Reply Bot - Learning Mode
===========================
Autonomous learning that runs continuously without intervention.

This script:
1. Collects posts from target accounts (@KharayKrayKray, etc)
2. Analyzes communication styles
3. Updates traction prediction models
4. Improves personality synthesis

Run with: python learn_mode.py
Stop with: Ctrl+C

The learning NEVER stops - it continuously improves.
"""

import sys
import time
import signal
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import get_logger, Logger
from src.utils.keep_alive import start_keep_alive, stop_keep_alive
from src.core.x_client import XClient
from src.core.openrouter_client import OpenRouterClient
from src.learning.post_collector import PostCollector
from src.learning.style_analyzer import StyleAnalyzer
from src.learning.traction_predictor import TractionPredictor
from src.learning.personality_engine import PersonalityEngine


class LearningMode:
    """
    Autonomous learning system.
    
    Runs forever, continuously:
    - Collecting posts from target accounts
    - Analyzing communication styles
    - Improving predictions
    - Synthesizing personality
    """
    
    def __init__(self, x_client=None, openrouter_client=None, test_mode: bool = False, verbose: bool = True):
        """
        Initialize learning mode.
        
        Args:
            x_client: Shared XClient instance
            openrouter_client: Shared OpenRouterClient instance
            test_mode: If True, run single collection then exit
            verbose: Show detailed output
        """
        self.x_client = x_client
        self.ai_client = openrouter_client
        self.test_mode = test_mode
        self.verbose = verbose
        self.running = False
        
        self.log = get_logger()
        if verbose:
            self.log.banner()
            self.log.header("Learning Mode Initialization")
        
        # Initialize components
        self._init_components()
        
        # Stats
        self.stats = {
            "started": datetime.now(),
            "collections": 0,
            "analyses": 0,
            "posts_collected": 0,
            "posts_analyzed": 0
        }

        # Timer state
        self.last_collect = datetime.min
        self.last_analyze = datetime.min
        self.last_predict = datetime.min
        self.last_synth = datetime.min

    def _init_components(self) -> None:
        """Initialize all components."""
        # Load env
        load_dotenv()
        
        # X Client (for collecting posts)
        if not self.x_client:
            try:
                self.x_client = XClient()
                self.log.success(f"X Client initialized")
            except Exception as e:
                self.log.warning(f"X Client failed: {e}")
                self.log.info("Learning will work with cached data only")
                self.x_client = None
        
        # OpenRouter Client (for AI analysis)
        if not self.ai_client:
            try:
                self.ai_client = OpenRouterClient()
                self.log.success("OpenRouter Client initialized")
            except Exception as e:
                self.log.warning(f"OpenRouter failed: {e}")
                self.log.info("Learning will use heuristic analysis only")
                self.ai_client = None
        
        # Learning components
        self.collector = PostCollector(
            x_client=self.x_client,
            openrouter_client=self.ai_client
        )
        self.log.success("Post Collector initialized")
        
        self.analyzer = StyleAnalyzer(openrouter_client=self.ai_client)
        self.log.success("Style Analyzer initialized")
        
        self.predictor = TractionPredictor(openrouter_client=self.ai_client)
        self.log.success("Traction Predictor initialized")
        
        self.personality = PersonalityEngine()
        self.log.success("Personality Engine initialized")
    
    def _display_stats(self) -> None:
        """Display current stats."""
        # Only display if verbose
        if not self.verbose:
            return

        runtime = datetime.now() - self.stats["started"]
        hours = runtime.total_seconds() / 3600
        
        collector_stats = self.collector.get_stats()
        analyzer_stats = self.analyzer.get_stats()
        predictor_stats = self.predictor.get_stats()
        
        print("\n" + "="*50)
        print("📊 LEARNING STATS")
        print("="*50)
        print(f"Runtime: {runtime}")
        print(f"\n📥 Collection:")
        print(f"   Cycles: {self.stats['collections']}")
        print(f"   Total posts: {collector_stats['total_posts']}")
        print(f"   Accounts: {collector_stats['accounts_tracked']}")
        print(f"\n🔍 Analysis:")
        print(f"   Sessions: {analyzer_stats['sessions']}")
        print(f"   Posts analyzed: {analyzer_stats['total_posts_analyzed']}")
        print(f"   Code terms learned: {analyzer_stats['code_terms_learned']}")
        print(f"\n📈 Predictions:")
        print(f"   Total: {predictor_stats['total_predictions']}")
        print(f"   Accuracy: {predictor_stats['accuracy']}")
        print("="*50 + "\n")
    
    def collect_cycle(self) -> None:
        """Run one collection cycle."""
        self.log.header("Collection Cycle")
        
        if not self.x_client:
            self.log.warning("No X client - skipping collection")
            return
        
        try:
            results = self.collector.collect_all_targets()
            
            self.stats["collections"] += 1
            self.stats["posts_collected"] += results.get("total_new", 0)
            
            self.log.success(f"Collected {results['total_new']} new posts")
            
            for account, count in results.get("accounts", {}).items():
                if count > 0:
                    self.log.stats(f"@{account}", f"{count} posts", "cyan")
            
        except Exception as e:
            self.log.error(f"Collection error: {e}")
    
    def analyze_cycle(self) -> None:
        """Run one analysis cycle."""
        self.log.header("Analysis Cycle")
        
        # Get all collected post texts
        all_posts = self.collector.get_all_post_texts()
        
        if len(all_posts) < 10:
            self.log.warning(f"Not enough posts for analysis ({len(all_posts)} posts)")
            return
        
        try:
            # Analyze by account
            for username, posts in self.collector.posts.get("accounts", {}).items():
                if len(posts) < 5:
                    continue
                
                post_texts = [p.get("text", "") for p in posts if p.get("text")]
                
                if len(post_texts) >= 5:
                    analysis = self.analyzer.analyze_posts(post_texts, account=username)
                    self.stats["analyses"] += 1
                    self.stats["posts_analyzed"] += len(post_texts)
                    
                    if self.verbose:
                        self.log.stats(f"@{username} directness", 
                                      analysis.get("directness_score", "N/A"),
                                      "green" if analysis.get("directness_score", 0) > 7 else "yellow")
                        
                        if analysis.get("code_terms_found"):
                            self.log.stats("Code terms", 
                                         ", ".join(analysis["code_terms_found"][:5]),
                                         "cyan")
            
            self.log.success(f"Analysis complete")
            
        except Exception as e:
            self.log.error(f"Analysis error: {e}")
    
    def predict_cycle(self) -> None:
        """Update prediction models."""
        self.log.header("Prediction Update")
        
        # Get high engagement posts to learn from
        high_engagement = self.collector.get_high_engagement_posts(min_likes=10)
        
        if not high_engagement:
            self.log.warning("No high engagement posts to learn from")
            return
        
        try:
            # Learn from top posts
            for post in high_engagement[:20]:
                self.predictor.predict_traction(post)
            
            # Display best patterns
            if self.verbose:
                self.log.stats("Viral topics", 
                             ", ".join(self.predictor.metrics.get("viral_topics", [])[:5]) or "Still learning",
                             "green")
                self.log.stats("Best hours", 
                             str(self.predictor.metrics.get("best_hours", [])),
                             "cyan")
            
            self.log.success("Prediction models updated")
            
        except Exception as e:
            self.log.error(f"Prediction update error: {e}")
    
    def synthesize_personality(self) -> None:
        """Update personality synthesis."""
        self.log.header("Personality Synthesis")
        
        try:
            # Reload learned patterns
            self.personality = PersonalityEngine()
            
            # Display current personality
            if self.verbose:
                print(self.personality.describe())
            
            self.log.success("Personality synthesized")
            
        except Exception as e:
            self.log.error(f"Personality synthesis error: {e}")
    
    def step(self) -> None:
        """
        Run one step of the learning cycle.
        Checks all timers and runs pending tasks.
        """
        # Intervals
        collect_interval = timedelta(minutes=15)
        analyze_interval = timedelta(hours=6)
        predict_interval = timedelta(hours=12)
        synth_interval = timedelta(hours=24)
        
        now = datetime.now()
        
        # Check collection
        if now - self.last_collect >= collect_interval:
            self.collect_cycle()
            self.last_collect = now
        
        # Check analysis
        if now - self.last_analyze >= analyze_interval:
            self.analyze_cycle()
            self.last_analyze = now
        
        # Check prediction
        if now - self.last_predict >= predict_interval:
            self.predict_cycle()
            self.last_predict = now
        
        # Check synthesis
        if now - self.last_synth >= synth_interval:
            self.synthesize_personality()
            self.last_synth = now
        
        # Show stats every hour
        runtime = now - self.stats["started"]
        if runtime.total_seconds() > 0 and runtime.total_seconds() % 3600 < 60:
            self._display_stats()

    def run_learning_loop(self) -> None:
        """
        Main learning loop - runs forever.
        Wrapper around step() for standalone execution.
        """
        self.running = True
        
        self.log.header("Starting Continuous Learning")
        print("Press Ctrl+C to stop\n")
        
        # Initial run of all cycles to populate data
        self.collect_cycle()
        self.analyze_cycle()
        self.predict_cycle()
        self.synthesize_personality()
        self._display_stats()
        
        # Initialize timers
        now = datetime.now()
        self.last_collect = now
        self.last_analyze = now
        self.last_predict = now
        self.last_synth = now
        
        if self.test_mode:
            self.log.info("Test mode - exiting after initial cycle")
            return
        
        # Main loop
        while self.running:
            try:
                self.step()
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.log.error(f"Loop error: {e}")
                time.sleep(60)
        
        self.log.header("Learning Stopped")
        self._display_stats()
    
    def stop(self) -> None:
        """Stop the learning loop."""
        self.running = False
        self.log.info("Stopping learning loop...")


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="X Reply Bot - Autonomous Learning Mode"
    )
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Run single learning cycle then exit"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Reduce output verbosity"
    )
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="Show stats and exit"
    )
    
    args = parser.parse_args()
    
    # Start keep alive for Render deployment
    keep_alive = start_keep_alive()
    
    # If just showing stats
    if args.stats:
        learner = LearningMode(test_mode=True, verbose=True)
        learner._display_stats()
        return
    
    # Run learning
    learner = LearningMode(
        test_mode=args.test,
        verbose=not args.quiet
    )
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n")
        learner.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start learning
    learner.run_learning_loop()


if __name__ == "__main__":
    main()
