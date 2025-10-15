"""
MCP Server entry point.

This module provides the main entry point for running the MCP server
in stdio mode for Docker containers.
"""

import asyncio

from .server import main

if __name__ == "__main__":
    asyncio.run(main())
