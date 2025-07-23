#!/bin/zsh

SSD_MOUNT="/Volumes/Ext-SSD"
TOOLS_DIR="$SSD_MOUNT/Tools"
BIN_DIR="$TOOLS_DIR/bin"
GO_DIR="$TOOLS_DIR/go"
CACHE_DIR="$TOOLS_DIR/gocache"
PIPX_HOME="$TOOLS_DIR/pipx"
SECLISTS_DIR="$TOOLS_DIR/seclists"
NUCLEI_TEMPLATES="$TOOLS_DIR/nuclei-templates"
NUCLEI_CONFIG_DIR="$TOOLS_DIR/nuclei-config"
NUCLEI_CONFIG="$NUCLEI_CONFIG_DIR/nuclei-config.yaml"
EYEWITNESS_DIR="$TOOLS_DIR/eyewitness"
KNOCKPY_DIR="$TOOLS_DIR/knockpy"

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
export PATH="$BIN_DIR:$PATH"
export NUCLEI_TEMPLATES="$NUCLEI_TEMPLATES"
export NUCLEI_CONFIG="$NUCLEI_CONFIG"

echo "✅ Environment set to use SSD at $TOOLS_DIR"

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
  echo "🔧 Installing tools to SSD..."

  # ProjectDiscovery core + extra tools
  for pkg in \
    "subfinder github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest" \
    "httpx github.com/projectdiscovery/httpx/cmd/httpx@latest" \
    "dnsx github.com/projectdiscovery/dnsx/cmd/dnsx@latest" \
    "naabu github.com/projectdiscovery/naabu/v2/cmd/naabu@latest" \
    "nuclei github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest" \
    "asnmap github.com/projectdiscovery/asnmap/cmd/asnmap@latest" \
    "ffuf github.com/ffuf/ffuf@latest" \
    "gowitness github.com/sensepost/gowitness@latest" \
    "subjack github.com/haccer/subjack@latest" \
    "katana github.com/projectdiscovery/katana/cmd/katana@latest" \
    "uncover github.com/projectdiscovery/uncover/cmd/uncover@latest" \
    "cloudlist github.com/projectdiscovery/cloudlist/cmd/cloudlist@latest" \
    "cvemap github.com/projectdiscovery/cvemap/cmd/cvemap@latest" \
    "tlsx github.com/projectdiscovery/tlsx/cmd/tlsx@latest" \
    "notify github.com/projectdiscovery/notify/cmd/notify@latest" \
    "pdtm github.com/projectdiscovery/pdtm/cmd/pdtm@latest" \
    "mapcidr github.com/projectdiscovery/mapcidr/cmd/mapcidr@latest" \
    "cdncheck github.com/projectdiscovery/cdncheck/cmd/cdncheck@latest" \
    "aix github.com/projectdiscovery/aix/cmd/aix@latest" \
    "proxify github.com/projectdiscovery/proxify/cmd/proxify@latest"
  do
    install_tool "${(z)pkg}"
  done

  # pipx and Python tools
  install_tool "pipx" "pipx" "python3 -m pip install --user pipx"
  for pytool in wafw00f whatweb; do
    install_tool "$pytool" "$pytool" "pipx install $pytool"
  done

  # Knockpy via git clone and pip install
  if [ ! -d "$KNOCKPY_DIR" ]; then
    echo "⬇️ Cloning knockpy..."
    git clone https://github.com/guelfoweb/knock.git "$KNOCKPY_DIR"
    pip3 install -e "$KNOCKPY_DIR"
  else
    echo "✅ knockpy already cloned"
  fi
  if [ ! -f "$BIN_DIR/knockpy" ]; then
    ln -s "$KNOCKPY_DIR/bin/knockpy" "$BIN_DIR/knockpy"
    chmod +x "$BIN_DIR/knockpy"
    echo "✅ knockpy symlink created"
  fi

  # Homebrew tools (binary copied to SSD)
  for br in amass nmap masscan rustscan; do
    if ! command -v "$br" &>/dev/null; then
      echo "⬇️ Installing $br with brew..."
      brew install "$br"
    fi
    cp "$(which $br)" "$BIN_DIR/"
  done

  # SecLists
  if [ -d "$SECLISTS_DIR/.git" ]; then
    echo "🔄 Updating SecLists..."
    git -C "$SECLISTS_DIR" pull
  else
    echo "⬇️ Cloning SecLists..."
    git clone https://github.com/danielmiessler/SecLists "$SECLISTS_DIR"
  fi

  # Nuclei templates
  if [ -d "$NUCLEI_TEMPLATES/.git" ]; then
    echo "🔄 Updating nuclei-templates..."
    git -C "$NUCLEI_TEMPLATES" pull
  else
    echo "⬇️ Cloning nuclei-templates..."
    git clone https://github.com/projectdiscovery/nuclei-templates "$NUCLEI_TEMPLATES"
  fi

  # Nuclei config
  if [ ! -f "$NUCLEI_CONFIG" ]; then
    echo "templates-directory: \"$NUCLEI_TEMPLATES\"" > "$NUCLEI_CONFIG"
    echo "✅ Created nuclei config"
  fi

  # EyeWitness
  if [ ! -d "$EYEWITNESS_DIR" ]; then
    echo "⬇️ Cloning EyeWitness..."
    git clone https://github.com/FortyNorthSecurity/EyeWitness "$EYEWITNESS_DIR"
  else
    echo "✅ EyeWitness already present"
  fi

  echo ""
  echo "🎉 All tools installed. Paths:"
  echo "----------------------------------------"
  for bin in $(ls "$BIN_DIR"); do
    echo "$bin: $BIN_DIR/$bin"
  done
  echo "----------------------------------------"
  echo "📁 SecLists:           $SECLISTS_DIR"
  echo "📁 Nuclei templates:   $NUCLEI_TEMPLATES"
  echo "⚙️  Nuclei config:      $NUCLEI_CONFIG"
fi
