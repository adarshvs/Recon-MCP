# app/config.py

# ---- Local LLM ----
LLM_MODEL = "llama3.1:8b"  # you have this pulled

# ---- Absolute tool paths (from your message) ----
TOOL_PATHS = {
    "amass":     "/Volumes/Ext-SSD/Tools/bin/amass",
    "asnmap":    "/Volumes/Ext-SSD/Tools/bin/asnmap",
    "dnsx":      "/Volumes/Ext-SSD/Tools/bin/dnsx",
    "ffuf":      "/Volumes/Ext-SSD/Tools/bin/ffuf",
    "gowitness": "/Volumes/Ext-SSD/Tools/bin/gowitness",
    "httpx":     "/Volumes/Ext-SSD/Tools/bin/httpx",
    "knockpy":   "/Volumes/Ext-SSD/Tools/bin/knockpy",
    "masscan":   "/Volumes/Ext-SSD/Tools/bin/masscan",
    "naabu":     "/Volumes/Ext-SSD/Tools/bin/naabu",
    "nmap":      "/Volumes/Ext-SSD/Tools/bin/nmap",
    "nuclei":    "/Volumes/Ext-SSD/Tools/bin/nuclei",
    "rustscan":  "/Volumes/Ext-SSD/Tools/bin/rustscan",
    "subfinder": "/Volumes/Ext-SSD/Tools/bin/subfinder",
    "wafw00f":   "/Volumes/Ext-SSD/Tools/bin/wafw00f",
    "whatweb":   "/Volumes/Ext-SSD/Tools/bin/whatweb",

    # system tools
    "traceroute": "traceroute",
    "tracert":    "tracert",
    "whois":      "whois",
    "dig":        "dig",
}

# ---- Extra resources ----
SECLISTS_DIR       = "/Volumes/Ext-SSD/Tools/seclists"
NUCLEI_TEMPLATES   = "/Volumes/Ext-SSD/Tools/nuclei-templates"
NUCLEI_CONFIG_FILE = "/Volumes/Ext-SSD/Tools/nuclei-config/nuclei-config.yaml"

# Where to store job outputs/reports
WORK_DIR = "jobs"  # will be created if missing
