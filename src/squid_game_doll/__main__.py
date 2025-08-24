#!/usr/bin/env python3
"""Entry point for squid_game_doll package when run as module.

This allows running the package with:
    python -m squid_game_doll
or with the console script:
    squid-game-doll
"""

from .run import run

def main():
    """Main entry point for console script."""
    run()

if __name__ == "__main__":
    main()