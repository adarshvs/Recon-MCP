from pathlib import Path

# Adjust if you move things
TOOLS = {
    "subfinder": "/Volumes/Ext-SSD/Tools/bin/subfinder",
    "dnsx":      "/Volumes/Ext-SSD/Tools/bin/dnsx",
    "httpx":     "/Volumes/Ext-SSD/Tools/bin/httpx",
    "wafw00f":   "/Volumes/Ext-SSD/Tools/bin/wafw00f",
    "whatweb":   "/Volumes/Ext-SSD/Tools/bin/whatweb",
    "nuclei":    "/Volumes/Ext-SSD/Tools/bin/nuclei",
    "nmap":      "/Volumes/Ext-SSD/Tools/bin/nmap",
    "amass":     "/Volumes/Ext-SSD/Tools/bin/amass",
    # add more as you wire them (masscan, rustscan, ffuf, gowitness…)
}

BASE_DIR        = Path(__file__).resolve().parent.parent
JOBS_DIR        = BASE_DIR / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# Paths you printed earlier
SECLISTS_DIR    = Path("/Volumes/Ext-SSD/Tools/seclists")
NUCLEI_TEMPLATES= Path("/Volumes/Ext-SSD/Tools/nuclei-templates")
NUCLEI_CONFIG   = Path("/Volumes/Ext-SSD/Tools/nuclei-config/nuclei-config.yaml")

DEFAULT_TIMEOUT = 120  # seconds per step
OLLAMA_MODEL    = "llama3.1:8b"   # change if you load a better one
OLLAMA_URL      = "http://127.0.0.1:11434/api/generate"
