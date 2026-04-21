"""Quick start script for TTS System."""

import os
import subprocess
import sys
from pathlib import Path


def check_uv_installed():
    """Check if uv is installed."""
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main():
    """Quick start the TTS system."""
    print("🚀 TTS System Quick Start")
    print("=" * 50)

    # Check uv
    if not check_uv_installed():
        print("❌ uv is not installed!")
        print("Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("Or visit: https://github.com/astral-sh/uv")
        sys.exit(1)

    print("✓ uv is installed")

    # Sync dependencies
    print("\n📦 Installing dependencies...")
    try:
        subprocess.run(["uv", "sync"], check=True)
        print("✓ Dependencies installed")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)

    # Create .env if not exists
    env_file = Path(".env")
    if not env_file.exists():
        print("\n📝 Creating .env file...")
        example_env = Path(".env.example")
        if example_env.exists():
            with open(example_env, "r") as src:
                with open(env_file, "w") as dst:
                    dst.write(src.read())
            print("✓ Created .env from .env.example")
            print("⚠️  Please edit .env to add your API keys")
        else:
            print("⚠️  .env.example not found, skipping")
    
    # Read API_PORT from .env file if it exists
    api_port = "8000"  # default
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                if line.startswith("API_PORT="):
                    api_port = line.split("=", 1)[1].strip()
                    break

    # Initialize database
    print("\n🗄️  Initializing database...")
    db_dir = Path("database")
    db_dir.mkdir(exist_ok=True)
    
    try:
        subprocess.run(["uv", "run", "alembic", "upgrade", "head"], check=True)
        print("✓ Database initialized")
    except subprocess.CalledProcessError:
        print("❌ Failed to initialize database")
        sys.exit(1)

    # Start server
    print("\n🌐 Starting TTS System API...")
    print("=" * 50)
    print(f"API will be available at: http://localhost:{api_port}")
    print(f"API docs: http://localhost:{api_port}/api/v1/docs")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    print()

    try:
        subprocess.run([
            "uv", "run", "uvicorn",
            "packages.api.main:app",
            "--host", "0.0.0.0",
            "--port", api_port,
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down TTS System...")
        print("Goodbye!")


if __name__ == "__main__":
    main()
