<div align="center">

# 🌌 ALFEONULL STUDIO

**Next-Generation Portable Video Rendering & Processing Framework**

[![Python](https://img.shields.io/badge/Python-3.9%2B-45a29e?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Engines](https://img.shields.io/badge/Engines-FFmpeg%20%7C%20MLT-0b0c10?style=for-the-badge&color=f28482)](https://ffmpeg.org)

*No installation required. Pure local rendering power.*

</div>

---

## ⚡ Overview

**Alfeonull Studio** is a standalone, cross-platform multimedia environment designed for automated, high-performance video rendering. Built on a hybrid architecture, it combines the flexibility of a **Flask-based local web server** with a custom **hardware-accelerated PyQt5 Bootloader**, delivering an enterprise-grade experience without the need for complex installations.

Powered by industry-standard engines — **FFmpeg** and the **MLT Multimedia Framework** — Alfeonull Studio provides a zero-dependency local rendering pipeline straight out of the box.

## 🔥 Core Features

- **🚀 Zero-Install Architecture**: 100% portable. Download, extract, and launch. All dependencies, engines, and environments are self-contained.
- **⚙️ Dual-Engine Render Core**: Seamlessly integrates `FFmpeg` for ultra-fast encoding and `MLT` (Shotcut Engine) for complex multi-layered timeline processing.
- **🖥️ Tactical GUI Bootloader**: A sleek, borderless initialization dashboard providing real-time system diagnostics, CPU telemetry, and dependency validation before mounting the server.
- **📡 Local Flask Environment**: Operates entirely offline via `127.0.0.1:5000`. No cloud dependencies, ensuring total data privacy.
- **🗄️ SQLite Database Integration**: Built-in persistent storage for render jobs, caching, and asset management.

---

## 🛠️ Quick Start

Alfeonull Studio is ready to run on any operating system immediately after downloading. 

### 1. Download the Latest Release
Grab the compiled portable version for your OS from the [Releases Tab](../../releases/latest).

### 2. Launch the Studio
Extract the archive and run the respective launcher for your system:

*Note: On the very first launch, the bootloader will automatically initialize the environment and verify the integrity of the multimedia engines.*

---

## 🏗️ System Architecture

Alfeonull Studio utilizes a highly decoupled, multi-threaded approach:

1. **The Bootloader (`run.py / PyQt5`)**: Validates system architecture, checks FFmpeg/MLT binaries, and provides a graphical terminal experience.
2. **The WSGI Server (`Flask`)**: Serves the modern, responsive web UI and handles RESTful requests.
3. **The Render Worker (`threading.Thread`)**: A background daemon that parses MLT XML files (`.mlt`) and pipes frames directly into FFmpeg (`libvpx-vp9`, `yuva420p`) via background subprocesses, keeping the main UI highly responsive.

---

## ⚙️ Minimum System Requirements

- **OS:** Windows 10/11, macOS 11+, or modern Linux distro (Ubuntu 20.04+)
- **CPU:** 4-Core Processor (x86_64 or ARM64)
- **RAM:** 4 GB Minimum (8 GB+ Recommended for 1080p+ rendering)
- **Disk:** ~500 MB free space (for the portable environment)

---

<div align="center">
  <p><i>Engineered for seamless local rendering.</i></p>
</div>
