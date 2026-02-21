#!/usr/bin/env python3
"""
Deep Research Analyst — main entry point.

Usage:
    python app.py                          # interactive REPL
    python app.py "AI in Healthcare 2025"  # single-shot research
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
        from src.cli.interactive import run_research

        run_research(topic)
    else:
        from src.cli.interactive import interactive_loop

        interactive_loop()


if __name__ == "__main__":
    main()
