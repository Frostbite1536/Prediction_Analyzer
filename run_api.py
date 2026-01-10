#!/usr/bin/env python3
"""
FastAPI server launcher for Prediction Analyzer

Usage:
    python run_api.py [--host HOST] [--port PORT] [--reload]

Examples:
    python run_api.py                    # Start on http://127.0.0.1:8000
    python run_api.py --port 3000        # Start on http://127.0.0.1:3000
    python run_api.py --reload           # Start with auto-reload for development
    python run_api.py --host 0.0.0.0     # Allow external connections
"""
import argparse
import sys


def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []

    try:
        import fastapi
    except ImportError:
        missing.append("fastapi")

    try:
        import uvicorn
    except ImportError:
        missing.append("uvicorn")

    try:
        import sqlalchemy
    except ImportError:
        missing.append("sqlalchemy")

    try:
        import jose
    except ImportError:
        missing.append("python-jose[cryptography]")

    try:
        import passlib
    except ImportError:
        missing.append("passlib[bcrypt]")

    try:
        import pydantic_settings
    except ImportError:
        missing.append("pydantic-settings")

    if missing:
        print("Missing required dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        print("\nInstall with:")
        print("  pip install -r requirements.txt")
        sys.exit(1)


def main():
    """Run the FastAPI server"""
    check_dependencies()

    parser = argparse.ArgumentParser(
        description="Run the Prediction Analyzer API server"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )

    args = parser.parse_args()

    import uvicorn

    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║           Prediction Analyzer API Server                      ║
╠═══════════════════════════════════════════════════════════════╣
║  Server running at: http://{args.host}:{args.port:<24}║
║  API Documentation: http://{args.host}:{args.port}/docs{' ' * 18}║
║  ReDoc:            http://{args.host}:{args.port}/redoc{' ' * 17}║
╚═══════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "prediction_analyzer.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
    )


if __name__ == "__main__":
    main()
