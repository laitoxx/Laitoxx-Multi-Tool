#!/usr/bin/env python3
import os
import urllib.request
import subprocess

def main():
    dest_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "resources", "js"))
    os.makedirs(dest_dir, exist_ok=True)
    dest_file = os.path.join(dest_dir, "vis-network.min.js")

    urls = [
        "https://unpkg.com/vis-network@9.1.2/standalone/umd/vis-network.min.js",
        "https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/vis-network.min.js"
    ]

    success = False
    for url in urls:
        print(f"Trying to download from: {url}")
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                content = response.read()
                with open(dest_file, "wb") as f:
                    f.write(content)
            print("Successfully downloaded from CDN!")
            success = True
            break
        except Exception as e:
            print(f"Failed download: {e}")

    if not success:
        print("Trying local npm install...")
        try:
            # Try npm install
            subprocess.run(["npm", "install", "vis-network"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            npm_file = os.path.join("node_modules", "vis-network", "standalone", "umd", "vis-network.min.js")
            if os.path.exists(npm_file):
                with open(npm_file, "rb") as f_in, open(dest_file, "wb") as f_out:
                    f_out.write(f_in.read())
                print("Successfully acquired via npm!")
                success = True
        except Exception as e:
            print(f"npm install failed: {e}")

    if not success:
        print("Falling back to writing mock placeholder script...")
        mock_content = """/* vis-network.min.js mock placeholder for offline mode */
window.vis = {
  DataSet: function(data) {
    this._data = data || [];
    this.add = function(item) { this._data.push(item); };
    this.get = function(id) { return this._data.find(x => x.id === id); };
  },
  Network: function(container, data, options) {
    this.container = container;
    this.data = data;
    this.options = options || {};
    this.listeners = {};
    
    this.on = function(event, callback) {
      if (!this.listeners[event]) {
        this.listeners[event] = [];
      }
      this.listeners[event].push(callback);
    };
    
    this.off = function(event, callback) {
      if (this.listeners[event]) {
        this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
      }
    };
    
    this.selectNodes = function(nodeIds) {
      // Mock selection logic
    };
    
    this.selectEdges = function(edgeIds) {
      // Mock selection logic
    };
    
    this.getNodeAt = function(pos) {
      return null;
    };
    
    this.getEdgeAt = function(pos) {
      return null;
    };
    
    this.setData = function(data) {
      this.data = data;
    };
    
    this.destroy = function() {};
    
    // Draw a placeholder layout
    let html = '<div style="color: #f1f0ff; padding: 20px; text-align: center; font-family: sans-serif;">';
    html += '<h3>Vis-Network Offline Mock</h3>';
    html += '<p>Visual graph representation (Offline Fallback)</p>';
    html += '<div style="margin-top: 15px; text-align: left; display: inline-block;">';
    if (data.nodes) {
      html += '<strong>Nodes:</strong><ul>';
      const nodesArr = Array.isArray(data.nodes) ? data.nodes : (data.nodes._data || []);
      nodesArr.forEach(n => {
        html += `<li>[${n.type || 'Node'}] ${n.label || n.id}</li>`;
      });
      html += '</ul>';
    }
    if (data.edges) {
      html += '<strong>Edges:</strong><ul>';
      const edgesArr = Array.isArray(data.edges) ? data.edges : (data.edges._data || []);
      edgesArr.forEach(e => {
        html += `<li>${e.source || e.from} -> ${e.target || e.to} (${e.label || 'connected'})</li>`;
      });
      html += '</ul>';
    }
    html += '</div></div>';
    container.innerHTML = html;
  }
};
"""
        with open(dest_file, "w", encoding="utf-8") as f:
            f.write(mock_content)
        print("Successfully wrote mock placeholder script to resources/js/vis-network.min.js")

if __name__ == "__main__":
    main()
