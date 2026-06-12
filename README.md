# Laitoxx Multi-Tool V2.3.1

[English](README.md) | [Русский](docs/README.ru.md) | [Українська](docs/README.uk.md) | [Türkçe](docs/README.tr.md)

<img src="./screenshot.png" alt="Laitoxx banner" width="100%"/>

---

Laitoxx is a powerful OSINT (Open-Source Intelligence) and cybersecurity toolkit, featuring a modern, user-friendly Graphical User Interface (GUI). It is designed for educational and research purposes, helping users collect publicly available data for security analysis, penetration testing, and digital footprint assessment.

⚠ **Disclaimer**: This tool is created for educational purposes only. The developers are not responsible for any misuse of this software.

### 🔌 Plugin Development (Lua)
Laitoxx supports extensibility through a powerful Lua-based plugin system. 
Full guide: 👉 [Plugin Development Guide (English)](docs/pluginBuilding.en.md)

### 🔹 Features
* **Modern GUI**
* **Extensible via Plugins (Lua)**
* **Customizable Themes**
* **Graph Editor (Relationship Visualization)**
* **SOCKS5 Proxy Support**
* **Performance Mode**

#### OSINT Tools:
* Global Wi-Fi & MAC Tracking
* Advanced Metadata Viewer & Forensics
* Phone number lookup
* IP tracking & scanning (with interactive maps)
* Email OSINT & validation
* Telegram OSINT
* Username search & Nickname generation (500+ sites)
* Image-Based Search
* Google OSINT (Advanced dorks)
* Local Database search
* Web-crawler
* Info Website (Whois, etc.)

#### Web & Network Tools:
* Port scanner (Nmap-based)
* Nmap Scanner
* Subdomain finder
* CMS Detector
* Technologies Fingerprinting
* Web security tools (SSL, CORS, Open Redirect, HTTP inspecting, JWT analyzer, etc.)
* CIDR Range Calculator
* REGEX Tester

#### Utilities:
* Hash Tools (Text Hasher, Hash Identifier, Rainbow Table Generator)
* Text Transformer (Encode/decode: Leet, Morse, Base64, Hex, ROT-13, etc.)
* Password Generator

### 🚀 Installation & Usage

Laitoxx provides convenient installation scripts for all major operating systems. You can download the tool using Git or by downloading the ZIP archive.

#### 🔽 Option 1: With Git (Recommended)
1. **Clone the repository:**
   ```sh
   git clone https://github.com/Laitoxx/Laitoxx-Multi-Tool.git
   cd Laitoxx-Multi-Tool
   ```

#### 🔽 Option 2: Without Git
1. Download the repository as a ZIP file from GitHub (Click **Code** -> **Download ZIP**).
2. Extract the ZIP file and open a terminal/command prompt in the extracted folder (`Laitoxx-Multi-Tool-main`).

---

#### 🐧 Ubuntu/Debian (Linux)
Run the automated installation script:
```sh
chmod +x install.sh
./install.sh
```
*To run the tool later, simply use: `python3 start.py`*

#### 🍎 MacOS
Run the automated installation script:
```sh
chmod +x install.sh
./install.sh
```
*To run the tool later, simply use: `python3 start.py`*

#### 🪟 Windows
Double-click the `install.bat` file, or run it via Command Prompt:
```cmd
install.bat
```
*To run the tool later, simply use: `python start.py`*

### ✨ Changelog v2.3.1
* **Global Wi-Fi Tracking**: Locate Wi-Fi routers worldwide. You can now reveal the exact coordinates of entire neighborhoods of routers just by searching an IP address or a single MAC address.
* **Smart Interactive Maps**: Maps now automatically highlight residential buildings, cafes, parks, and nearby Wi-Fi spots to help visualize the physical location of a target.
* **Advanced Metadata Viewer**: Added a powerful tool to extract, analyze, and safely erase hidden metadata (Exif, GPS, author info) from images and documents.
* **User Interface Polish**: Added smooth loading animations and improved background processing so the app stays fast and responsive during heavy searches.
* **Multi-language Support**: Network OSINT windows are now fully translated and dynamically switch between English, Russian, Ukrainian, and Turkish.
* **Performance Improvements**: Massive internal optimizations and code cleanups for a more stable, secure, and faster experience.
