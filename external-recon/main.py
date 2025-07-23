#!/usr/bin/env python3
import sys, json, subprocess

def whois_tool(params):
    domain = params.get("domain","")
    return subprocess.run(["whois", domain], capture_output=True, text=True).stdout

def dig_tool(params):
    domain = params.get("domain","")
    return subprocess.run(["dig", domain], capture_output=True, text=True).stdout

TOOLS = {"whois": whois_tool, "dig": dig_tool}

def main():
    try:
        req = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        print(json.dumps({"jsonrpc":"2.0","error":"Invalid JSON"}))
        return

    method = req.get("method","")
    func = TOOLS.get(method)
    params = req.get("params",{})
    if not func:
        result = f"Unknown method: {method}"
    else:
        try:
            result = func(params)
        except Exception as e:
            result = str(e)

    print(json.dumps({"jsonrpc":"2.0","id":req.get("id"),"result":result}))

if __name__ == "__main__":
    main()
