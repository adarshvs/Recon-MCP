#external-recon/main.py
#!/usr/bin/env python3
import sys, json, subprocess

def whois_tool(params):
    domain = params.get("domain","")
    return subprocess.run(["whois", domain], capture_output=True, text=True).stdout

def dig_tool(params):
    domain = params.get("domain","")
    return subprocess.run(["dig", domain], capture_output=True, text=True).stdout

TOOLS = {
    "whois": whois_tool,
    "dig":   dig_tool
}

def main():
    req_raw = sys.stdin.read()
    try:
        req = json.loads(req_raw)
    except json.JSONDecodeError:
        print(json.dumps({"jsonrpc":"2.0","error":"Invalid JSON"}))
        return

    method = req.get("method","")
    params = req.get("params",{})
    func   = TOOLS.get(method)

    if not func:
        result = f"Unknown method: {method}"
    else:
        try:
            result = func(params)
        except Exception as e:
            result = str(e)

    resp = {"jsonrpc":"2.0","id":req.get("id"),"result":result}
    print(json.dumps(resp))

if __name__ == "__main__":
    main()
