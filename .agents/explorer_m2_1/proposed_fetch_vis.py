import os
import urllib.request
import subprocess
import shutil
import tempfile

CDNS = [
    "https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/standalone/umd/vis-network.min.js",
    "https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js",
    "https://cdn.jsdelivr.net/npm/vis-network@9.1.9/standalone/umd/vis-network.min.js"
]

FALLBACK_JS = """\
window.vis = {
  Network: function(container, data, options) {
    container.innerHTML = `
      <div style="
        color: #f87171;
        padding: 40px 20px;
        font-family: 'Segoe UI', system-ui, sans-serif;
        text-align: center;
        background: #0d0d1a;
        height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
      ">
        <h3 style="margin-bottom: 10px; color: #f472b6; font-size: 18px;">Vis-Network Library Missing</h3>
        <p style="color: #a99fc0; max-width: 400px; font-size: 13px; line-height: 1.6;">
          Could not load <code>resources/js/vis-network.min.js</code>. The interactive network rendering is currently unavailable.
        </p>
        <p style="color: #6b6580; font-size: 12px; margin-top: 15px;">
          Please run the download script or place the <code>vis-network.min.js</code> file manually in <code>resources/js/</code>.
        </p>
      </div>
    `;
    return {
      on: function() {},
      off: function() {},
      setData: function() {},
      destroy: function() {},
      focus: function() {},
      fit: function() {},
      zoomOut: function() {},
      zoomIn: function() {}
    };
  }
};
"""

def fetch_vis_network():
    # Target path relative to the root project directory (assuming we run from root)
    dest_dir = os.path.abspath("resources/js")
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, "vis-network.min.js")

    # Strategy 1: CDN Download
    print("Attempting to download vis-network.min.js from CDNs...")
    for url in CDNS:
        try:
            print(f"Trying {url}...")
            # Using urllib with custom headers to bypass simple CDN blocks
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read()
                if len(content) > 100000:  # verify it's a substantial file
                    with open(dest_path, "wb") as f:
                        f.write(content)
                    print(f"Successfully downloaded to {dest_path}")
                    return True
        except Exception as e:
            print(f"Failed to fetch from CDN: {e}")

    # Strategy 2: NPM fallback
    print("Attempting to install vis-network via npm...")
    if shutil.which("npm"):
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                print(f"Running npm install in {tmpdir}...")
                subprocess.run(["npm", "install", "vis-network@9.1.9"], cwd=tmpdir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                src_file = os.path.join(tmpdir, "node_modules", "vis-network", "standalone", "umd", "vis-network.min.js")
                if os.path.exists(src_file):
                    shutil.copy(src_file, dest_path)
                    print(f"Successfully copied npm package asset to {dest_path}")
                    return True
        except Exception as e:
            print(f"Failed to install or copy from npm: {e}")
    else:
        print("npm is not available on this system.")

    # Strategy 3: Place placeholder
    print("Using robust fallback placeholder script...")
    try:
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(FALLBACK_JS)
        print(f"Written fallback placeholder script to {dest_path}")
        return False
    except Exception as e:
        print(f"Failed to write fallback script: {e}")
        return False

if __name__ == "__main__":
    fetch_vis_network()
