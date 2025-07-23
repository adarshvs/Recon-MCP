import subprocess
import json
import re
import platform


IS_MAC_OR_LINUX = platform.system() in ["Linux", "Darwin"]

ALLOWED_COMMANDS = ['whois', 'dig', 'nslookup', 'traceroute']
if not IS_MAC_OR_LINUX:
    ALLOWED_COMMANDS.append('tracert')

def query_llm(prompt: str) -> str:
    result = subprocess.run(
        ["ollama", "run", "mistral"],
        input=prompt.encode(),
        capture_output=True
    )
    return result.stdout.decode().strip()


import re


def parse_llm_response(llm_response: str):
    """
    Extracts a shell command from the LLM response and ensures it's a safe, supported one.
    """
    # Extract the description
    description_match = re.search(r'Description:\s*(.+?)(?:\n|$)', llm_response, re.IGNORECASE)
    description = description_match.group(1).strip() if description_match else "No description found."

    # Try to extract command inside backticks or from a heading
    command_patterns = [
        r'`{1,3}([a-zA-Z0-9\.\-\s/_]+)`{1,3}',  # backtick command
        r'Command to Run:\s*\n?(.+)',
        r'\n([a-z]+ [a-zA-Z0-9\.\-]+\.com)\n'
    ]

    command = None
    for pattern in command_patterns:
        match = re.search(pattern, llm_response, re.IGNORECASE)
        if match:
            command = match.group(1).strip()
            break

    if not command:
        command = "echo 'No command found.'"
    else:
        binary = command.split()[0].lower()

        # OS-specific substitution
        if binary == "tracert" and IS_MAC_OR_LINUX:
            command = command.replace("tracert", "traceroute")

        # Validate command
        binary = command.split()[0]
        if binary not in ALLOWED_COMMANDS:
            command = f"echo 'Blocked unsafe command: {binary}'"

    return description, command


def run_command(command: str) -> str:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Error: {str(e)}"

def process_query(user_query: str):
    # Step 1: Ask LLM to interpret
    prompt = f"""
You're a recon assistant. Interpret the user's query, and return:
- A short description of what it means
- A suitable command to run for reconnaissance

Format:
Description: <summary>
Command: <shell command>

User query: {user_query}
"""
    llm_full_response = query_llm(prompt)
    description, command = parse_llm_response(llm_full_response)
    output = run_command(command)

    # Step 2: Only call summary LLM if output is valid and not a blocked/echoed command
    formatted_output = ""
    if command and not command.startswith("echo"):
        summary_prompt = f"Summarize the following output:\n\n{output}"
        formatted_output = query_llm(summary_prompt)

    return {
        "llm_response": description,
        "command": command,
        "output": output,
        "formatted_output": formatted_output
    }