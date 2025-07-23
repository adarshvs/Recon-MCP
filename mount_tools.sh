#!/bin/zsh

SSD_MOUNT="/Volumes/Ext-SSD"
TOOLS_DIR="$SSD_MOUNT/Tools"
BIN_DIR="$TOOLS_DIR/bin"
GO_DIR="$TOOLS_DIR/go"
CACHE_DIR="$TOOLS_DIR/gocache"
PIPX_HOME="$TOOLS_DIR/pipx"
PIPX_BIN_DIR="$BIN_DIR"
SECLISTS_DIR="$TOOLS_DIR/seclists"
NUCLEI_TEMPLATES="$TOOLS_DIR/nuclei-templates"
NUCLEI_CONFIG_DIR="$TOOLS_DIR/nuclei-config"
NUCLEI_CONFIG="$NUCLEI_CONFIG_DIR/nuclei-config.yaml"
AQUATONE_DIR="$TOOLS_DIR/aquatone"
EYEWITNESS_DIR="$TOOLS_DIR/eyewitness"
MASSDNS_DIR="$TOOLS_DIR/massdns"

# Check SSD is mounted
if [ ! -d "$SSD_MOUNT" ]; then
  echo "❌ SSD not mounted at $SSD_MOUNT. Please connect it."
  return 1
fi

# Create required dirs
mkdir -p "$BIN_DIR" "$GO_DIR" "$CACHE_DIR" "$PIPX_HOME" "$SECLISTS_DIR" "$NUCLEI_CONFIG_DIR"

# Set environment
export GOPATH="$GO_DIR"
export GOCACHE="$CACHE_DIR"
export GOBIN="$BIN_DIR"
export PIPX_HOME="$PIPX_HOME"
export PIPX_BIN_DIR="$PIPX_BIN_DIR"
export PATH="$BIN_DIR:$PATH"
export NUCLEI_TEMPLATES="$NUCLEI_TEMPLATES"
export NUCLEI_CONFIG="$NUCLEI_CONFIG"

echo "✅ Environment variables set:
  GOPATH=$GOPATH
  GOCACHE=$GOCACHE
  GOBIN=$GOBIN
  PIPX_HOME=$PIPX_HOME
  PIPX_BIN_DIR=$PIPX_BIN_DIR
  NUCLEI_TEMPLATES=$NUCLEI_TEMPLATES
  NUCLEI_CONFIG=$NUCLEI_CONFIG
  PATH includes $BIN_DIR
"

install_tool() {
  cmd="$1"; shift
  check="$1"; shift
  install_cmd="$*"
  if command -v "$check" &> /dev/null; then
    echo "✅ $cmd already installed, skipping"
  else
    echo "⬇️ Installing $cmd..."
    eval "$install_cmd"
  fi
}

if [[ "$1" == "--install" ]]; then
  echo "🔧 Installing missing tools..."

  # Go-based tools
  for pkg in \
    "subfinder github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest" \
    "httpx github.com/projectdiscovery/httpx/cmd/httpx@latest" \
    "dnsx github.com/projectdiscovery/dnsx/cmd/dnsx@latest" \
    "naabu github.com/projectdiscovery/naabu/v2/cmd/naabu@latest" \
    "nuclei github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest" \
    "asnmap github.com/projectdiscovery/asnmap/cmd/asnmap@latest" \
    "ffuf github.com/ffuf/ffuf@latest" \
    "gowitness github.com/sensepost/gowitness@latest" \
    "subjack github.com/haccer/subjack@latest"
  do
    install_tool "${(z)pkg}"
  done

  # pipx and Python tools
  install_tool "pipx" "pipx" "python3 -m pip install --user pipx"
  for pytool in wafw00f whatweb knockpy; do
    install_tool "$pytool" "$pytool" "pipx install $pytool"
  done

  # Homebrew tools → move binary to SSD
  for br in amass nmap masscan rustscan; do
    install_tool "$br" "$br" "brew install $br && cp \$(which $br) $BIN_DIR/"
  done

  # SecLists
  if [ -d "$SECLISTS_DIR/.git" ]; then
    echo "✅ SecLists already present, pulling updates..."
    git -C "$SECLISTS_DIR" pull
  else
    echo "⬇️ Cloning SecLists..."
    git clone https://github.com/danielmiessler/SecLists "$SECLISTS_DIR"
  fi

  # Nuclei templates
  if [ -d "$NUCLEI_TEMPLATES/.git" ]; then
    echo "✅ nuclei-templates exist, pulling updates..."
    git -C "$NUCLEI_TEMPLATES" pull
  else
    echo "⬇️ Cloning nuclei-templates to SSD..."
    git clone https://github.com/projectdiscovery/nuclei-templates "$NUCLEI_TEMPLATES"
  fi

  # Create nuclei config on SSD
  if [ ! -f "$NUCLEI_CONFIG" ]; then
    echo "templates-directory: \"$NUCLEI_TEMPLATES\"" > "$NUCLEI_CONFIG"
    echo "✅ Created nuclei config at $NUCLEI_CONFIG"
  fi

  # Aquatone
  if [ ! -f "$BIN_DIR/aquatone" ]; then
    echo "⬇️ Installing Aquatone..."
    curl -sL https://github.com/michenriksen/aquatone/releases/latest/download/aquatone_macos_amd64.zip -o "$TOOLS_DIR/aquatone.zip"
    unzip -o "$TOOLS_DIR/aquatone.zip" -d "$AQUATONE_DIR"
    mv "$AQUATONE_DIR/aquatone" "$BIN_DIR/"
    chmod +x "$BIN_DIR/aquatone"
    rm "$TOOLS_DIR/aquatone.zip"
  else
    echo "✅ Aquatone already installed"
  fi

  # EyeWitness
  if [ ! -d "$EYEWITNESS_DIR" ]; then
    echo "⬇️ Cloning EyeWitness..."
    git clone https://github.com/FortyNorthSecurity/EyeWitness "$EYEWITNESS_DIR"
  else
    echo "✅ EyeWitness already present"
  fi

  # MassDNS
  if [ ! -f "$BIN_DIR/massdns" ]; then
    echo "⬇️ Installing MassDNS..."
    git clone https://github.com/blechschmidt/massdns "$MASSDNS_DIR"
    make -C "$MASSDNS_DIR"
    cp "$MASSDNS_DIR/bin/massdns" "$BIN_DIR/"
  else
    echo "✅ MassDNS already installed"
  fi

  echo "🎉 All tools installed on SSD at: $BIN_DIR"
  echo "📁 Nuclei templates at: $NUCLEI_TEMPLATES"
  echo "⚙️  Nuclei config at: $NUCLEI_CONFIG"
fi
