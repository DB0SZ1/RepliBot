"""
Keep Alive System for Render Deployment
Prevents the server from sleeping by self-pinging every 5 minutes.
"""

import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import requests
import os


class HealthHandler(BaseHTTPRequestHandler):
    """Simple health endpoint handler."""
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "status": "alive",
                "timestamp": datetime.now().isoformat(),
                "service": "x-reply-bot"
            }
            self.wfile.write(str(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class KeepAlive:
    """
    Keep alive system for Render deployment.
    
    Creates a simple HTTP server with a /health endpoint
    and pings it regularly to prevent the service from sleeping.
    """
    
    def __init__(self, port: int = 8080, ping_interval: int = 300):
        """
        Initialize keep alive system.
        
        Args:
            port: Port for health server (default 8080)
            ping_interval: Seconds between pings (default 300 = 5 min)
        """
        self.port = int(os.getenv('PORT', port))
        self.ping_interval = ping_interval
        self.server = None
        self.server_thread = None
        self.pinger_thread = None
        self._stop_event = threading.Event()
        
        # Get the Render URL or use localhost
        self.health_url = os.getenv('RENDER_EXTERNAL_URL', f'http://localhost:{self.port}')
        if not self.health_url.startswith('http'):
            self.health_url = f'https://{self.health_url}'
        self.health_url = f"{self.health_url}/health"
    
    def _start_server(self) -> None:
        """Start the HTTP server."""
        try:
            self.server = HTTPServer(('0.0.0.0', self.port), HealthHandler)
            print(f"[KEEP ALIVE] Health server running on port {self.port}")
            print(f"[KEEP ALIVE] Health endpoint: {self.health_url}")
            self.server.serve_forever()
        except Exception as e:
            print(f"[KEEP ALIVE] Server error: {e}")
    
    def _ping_loop(self) -> None:
        """Continuously ping the health endpoint."""
        # Wait for server to start
        time.sleep(5)
        
        while not self._stop_event.is_set():
            try:
                response = requests.get(self.health_url, timeout=10)
                if response.status_code == 200:
                    print(f"[KEEP ALIVE] Ping successful at {datetime.now().strftime('%H:%M:%S')}")
                else:
                    print(f"[KEEP ALIVE] Ping returned {response.status_code}")
            except requests.exceptions.ConnectionError:
                # Try localhost if external URL fails
                try:
                    local_url = f"http://localhost:{self.port}/health"
                    requests.get(local_url, timeout=5)
                    print(f"[KEEP ALIVE] Local ping successful")
                except:
                    print(f"[KEEP ALIVE] Ping failed - server may not be ready")
            except Exception as e:
                print(f"[KEEP ALIVE] Ping error: {e}")
            
            # Wait for next ping
            self._stop_event.wait(self.ping_interval)
    
    def start(self) -> None:
        """Start the keep alive system (server + pinger)."""
        self._stop_event.clear()
        
        # Start health server in background
        self.server_thread = threading.Thread(
            target=self._start_server,
            daemon=True,
            name="HealthServer"
        )
        self.server_thread.start()
        
        # Start pinger in background
        self.pinger_thread = threading.Thread(
            target=self._ping_loop,
            daemon=True,
            name="KeepAlivePinger"
        )
        self.pinger_thread.start()
        
        print("[KEEP ALIVE] System started")
    
    def stop(self) -> None:
        """Stop the keep alive system."""
        self._stop_event.set()
        
        if self.server:
            self.server.shutdown()
        
        print("[KEEP ALIVE] System stopped")
    
    def is_alive(self) -> bool:
        """Check if the system is running."""
        return (
            self.server_thread is not None and 
            self.server_thread.is_alive() and
            self.pinger_thread is not None and
            self.pinger_thread.is_alive()
        )


# Global instance for easy access
_keep_alive_instance = None


def start_keep_alive(port: int = 8080, ping_interval: int = 300) -> KeepAlive:
    """
    Start the keep alive system.
    
    Args:
        port: Port for health server
        ping_interval: Seconds between pings
        
    Returns:
        KeepAlive instance
    """
    global _keep_alive_instance
    
    if _keep_alive_instance is None or not _keep_alive_instance.is_alive():
        _keep_alive_instance = KeepAlive(port=port, ping_interval=ping_interval)
        _keep_alive_instance.start()
    
    return _keep_alive_instance


def stop_keep_alive() -> None:
    """Stop the keep alive system."""
    global _keep_alive_instance
    
    if _keep_alive_instance:
        _keep_alive_instance.stop()
        _keep_alive_instance = None


# Test
if __name__ == "__main__":
    print("Testing Keep Alive System...")
    
    keep_alive = KeepAlive(port=8080, ping_interval=10)  # 10s for testing
    keep_alive.start()
    
    try:
        # Run for 60 seconds
        for i in range(6):
            print(f"Running... ({i+1}/6)")
            time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        keep_alive.stop()
        print("Test complete")
