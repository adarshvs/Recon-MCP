# external-recon/main.py
import sys
import json
import subprocess

def handle_whois(params):
    domain = params.get("domain")
    result = subprocess.run(["whois", domain], capture_output=True, text=True)
    return result.stdout

def handle_dig(params):
    domain = params.get("domain")
    result = subprocess.run(["dig", domain], capture_output=True, text=True)
    return result.stdout

def main():
    request = json.loads(sys.stdin.read())
    
    method = request.get("method")
    params = request.get("params", {})

    if method == "whois":
        result = handle_whois(params)
    elif method == "dig":
        result = handle_dig(params)
    else:
        result = f"Unknown method: {method}"

    response = {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "result": result
    }

    print(json.dumps(response))

if __name__ == "__main__":
    main()
