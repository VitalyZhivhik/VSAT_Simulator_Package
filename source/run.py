#!/usr/bin/env python3
"""
VSAT Satellite Terminal Simulator — Launcher

Run this script to start the server:
    python run.py

Also works as PyInstaller entry point.
"""

import sys
import os
import logging
import webbrowser
import threading

# When frozen by PyInstaller, ensure the bundled directory is on sys.path
if getattr(sys, "frozen", False):
    base_dir = os.path.dirname(sys.executable)
    os.chdir(base_dir)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

# Ensure the project root is importable
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)


def setup_logging() -> None:
    """Configure file + console logging."""
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "vsat_server.log")

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — INFO level (our app logs)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)

    # Console handler — INFO level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    # Suppress noisy third-party loggers
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(fh)
    root.addHandler(ch)

    logging.getLogger("vsat").info("Logging initialized → %s", log_file)


def open_browser(port: int) -> None:
    """Open admin panel in default browser after a short delay."""
    import time
    time.sleep(2)
    webbrowser.open(f"http://localhost:{port}/admin")


def main() -> None:
    setup_logging()
    logger = logging.getLogger("vsat")

    try:
        import uvicorn
        from server.config import load_config
    except ImportError as e:
        logger.critical("Failed to import dependencies: %s", e)
        logger.critical("Run: pip install -r requirements.txt")
        input("Press Enter to exit...")
        sys.exit(1)

    try:
        config = load_config()
        logger.info("Config loaded: port=%s, debug=%s, partial_mode=%s",
                     config["server"]["port"],
                     config["server"].get("debug", False),
                     config["simulation"]["partial_mode"])
    except Exception as e:
        logger.critical("Failed to load config.json: %s", e, exc_info=True)
        input("Press Enter to exit...")
        sys.exit(1)

    host = config["server"]["host"]
    port = config["server"]["port"]

    # Open browser on first run (only if not debug/reload mode)
    if not config["server"].get("debug", False):
        t = threading.Thread(target=open_browser, args=(port,), daemon=True)
        t.start()

    # Check if port is already in use
    import socket
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        test_sock.bind(("0.0.0.0", port))
        test_sock.close()
    except OSError:
        logger.critical("Port %s is already in use! Close the other server first.", port)
        print(f"\n  ERROR: Port {port} is already in use.")
        print("  Close the other instance or change port in config.json.\n")
        input("Press Enter to exit...")
        sys.exit(1)

    logger.info("Starting uvicorn on %s:%s", host, port)
    try:
        uvicorn.run(
            "server.main:app",
            host=host,
            port=port,
            reload=config["server"].get("debug", False),
            log_level="info",
        )
    except OSError as e:
        if "address" in str(e).lower() or "10048" in str(e):
            logger.critical("Port %s is already in use: %s", port, e)
            print(f"\n  ERROR: Port {port} is already in use.")
            print("  Close the other instance or change port in config.json.\n")
        else:
            logger.critical("Server failed to start: %s", e, exc_info=True)
        input("Press Enter to exit...")
        sys.exit(1)
    except Exception as e:
        logger.critical("Server failed to start: %s", e, exc_info=True)
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
