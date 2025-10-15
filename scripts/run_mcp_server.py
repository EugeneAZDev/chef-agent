#!/usr/bin/env python3
"""
Script to run the MCP server.

Usage:
  python -m scripts.run_mcp_server
"""

import asyncio
import sys
from pathlib import Path

from adapters.mcp.server import main

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    asyncio.run(main())
