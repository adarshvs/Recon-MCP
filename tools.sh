# 0) Make sure brew is in PATH (for Apple Silicon)
/opt/homebrew/bin/brew --version >/dev/null 2>&1 || \
  echo "Install Homebrew first: https://brew.sh"

eval "$(/opt/homebrew/bin/brew shellenv)"
brew update

# 1) ProjectDiscovery tools
brew tap projectdiscovery/tap
brew install projectdiscovery/tap/subfinder \
             projectdiscovery/tap/httpx \
             projectdiscovery/tap/dnsx \
             projectdiscovery/tap/naabu \
             projectdiscovery/tap/asnmap \
             projectdiscovery/tap/nuclei

# 2) Other common recon tools (from core)
brew install amass nmap masscan rustscan ffuf parallel jq

# 3) Tools not in brew core

## WhatWeb (Ruby gem)
brew install ruby   # if you don’t have it
gem install whatweb

## WAFW00F (Python)
brew install pipx
pipx ensurepath
pipx install wafw00f

## SecLists (wordlists)
git clone https://github.com/danielmiessler/SecLists.git ~/SecLists
# optional: symlink somewhere global
sudo ln -s ~/SecLists /usr/local/share/seclists 2>/dev/null || true

