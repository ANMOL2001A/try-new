#!/usr/bin/env python3
"""
LiveKit AI Car Call Centre - Run Script
This script helps you start the backend services easily.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_path = Path(".env")
    if not env_path.exists():
        logger.error(".env file not found!")
        logger.info("Please create a .env file with your credentials")
        return False
    
    required_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY", 
        "LIVEKIT_API_SECRET",
        "GROQ_API_KEY"
    ]
    
    # Read .env file
    with open(env_path) as f:
        env_content = f.read()
    
    missing_vars = []
    for var in required_vars:
        if f"{var}=" not in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing environment variables in .env: {missing_vars}")
        return False
        
    logger.info("✓ Environment file is properly configured")
    return True

def install_requirements():
    """Install Python requirements"""
    logger.info("Installing Python requirements...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True, text=True)
        logger.info("✓ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install requirements: {e}")
        logger.error(e.stderr)
        return False

def run_server():
    """Run the Flask server"""
    logger.info("Starting Flask server...")
    try:
        subprocess.Popen([sys.executable, "server.py"])
        logger.info("✓ Flask server started on http://localhost:5001")
        return True
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        return False

def run_agent():
    """Run the LiveKit agent"""
    logger.info("Starting LiveKit agent...")
    try:
        subprocess.run([sys.executable, "agent.py", "start"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Agent failed: {e}")
        return False
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
        return True

def main():
    """Main function to run the entire setup"""
    logger.info("🚗 Starting LiveKit AI Car Call Centre Backend")
    logger.info("="*50)
    
    # Check environment
    if not check_env_file():
        logger.error("❌ Environment setup failed")
        sys.exit(1)
    
    # Install requirements
    if not install_requirements():
        logger.error("❌ Requirements installation failed")
        sys.exit(1)
    
    print("\nWhat would you like to run?")
    print("1. Start Flask server only")
    print("2. Start LiveKit agent only") 
    print("3. Start both (recommended)")
    
    choice = input("Enter your choice (1-3): ").strip()
    
    if choice == "1":
        run_server()
        input("Press Enter to stop...")
        
    elif choice == "2":
        run_agent()
        
    elif choice == "3":
        # Start server in background
        if run_server():
            logger.info("Server started, now starting agent...")
            # Small delay to let server start
            import time
            time.sleep(2)
            run_agent()
        else:
            logger.error("Failed to start server")
            sys.exit(1)
    else:
        logger.error("Invalid choice")
        sys.exit(1)

if __name__ == "__main__":
    main()