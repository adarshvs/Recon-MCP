# external-recon/main.py

import asyncio
from mcp import Tool, run_server
import subprocess

class DigTool(Tool):
    name = "dig"
    description = "Resolves DNS records"
    parameters = {"domain": str}

    async def run(self, domain: str):
        result = subprocess.run(["dig", domain], capture_output=True, text=True)
        return {"output": result.stdout.strip()}

class WhoisTool(Tool):
    name = "whois"
    description = "Performs whois lookup"
    parameters = {"domain": str}

    async def run(self, domain: str):
        result = subprocess.run(["whois", domain], capture_output=True, text=True)
        return {"output": result.stdout.strip()}

async def main():
    await run_server([DigTool(), WhoisTool()])

if __name__ == "__main__":
    asyncio.run(main())
