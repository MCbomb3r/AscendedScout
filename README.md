# AscendedScout 🦖

**Real-time OCR monitoring tool for ARK: Survival Ascended with Discord Bot integration**

AscendedScout is a Python-based screen monitoring application that uses OCR (Optical Character Recognition) to automatically detect and log player activities and structure destruction events in ARK: Survival Ascended. Includes **Secret Spy Discord Bot** for real-time notifications. Perfect for server tribes who want to keep track of what's happening on the server or to prevent offline raids.

## ▶️ Demonstration Video

[![▶️ Watch Demo on YouTube](https://img.shields.io/badge/Watch%20Demo-red?style=for-the-badge&logo=youtube)](https://www.youtube.com/watch?v=-mQdloW0OS4)

## ✨ Features

### Core OCR Monitoring
- **Real-time Player Activity Monitoring**: Detects when players join or leave the server
- **Tribe Member Tracking**: Specifically tracks tribemember activities separately
- **Structure Destruction Alerts**: Monitors and logs when your structures are destroyed
- **Multi-zone Screen Capture**: Monitors different areas of the screen simultaneously
- **Advanced OCR Processing**: Uses multiple color-based filters and preprocessing techniques for accurate text recognition
- **Duplicate Prevention**: Smart timestamp-based deduplication system
- **Automatic Logging**: Organized log files for different types of events

### Discord Bot Integration (Secret Spy)
- **Real-time Discord Notifications**: Instant alerts sent to your Discord server
- **Audio Alerts**: Optional sound notifications for critical events
- **Customizable Channels**: Send different types of alerts to specific channels
- **Rich Embeds**: Beautifully formatted Discord messages with timestamps

## 🔧 Requirements

### System Requirements
- Windows (currently configured for Windows paths)
- Python 3.7+
- Tesseract OCR installed

### Python Dependencies
```bash
pip install -r requirements.txt
```

**Full dependencies list:**
- `opencv-python` - Computer vision and image processing
- `numpy` - Numerical computing
- `pytesseract` - OCR engine wrapper
- `mss` - Screen capture
- `discord.py` - Discord bot framework
- `aiohttp` - Async HTTP client

### External Dependencies
- **Tesseract OCR**: Download and install from [GitHub Tesseract releases](https://github.com/tesseract-ocr/tesseract)
  - Default installation path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
  - Make sure to add Tesseract to your system PATH

## 🚀 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/MCbomb3r/AscendedScout.git
   cd AscendedScout
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Tesseract OCR**:
   - Download from [Tesseract GitHub releases](https://github.com/tesseract-ocr/tesseract/releases)
   - Install to default location or update the path in the script
   - Ensure English language pack is included

4. **Discord Bot Setup** (Optional):
   - Create a Discord bot at [Discord Developer Portal](https://discord.com/developers/applications)
   - Get your bot token and add it to `bot.py`
   - Invite the bot to your server with appropriate permissions
   - Configure channel IDs in the bot script

5. **Configure screen regions** (if needed):
   - The script is pre-configured for standard ARK UI positions
   - Modify `top_zone` and `center_zone` coordinates if your setup differs

## 📖 Usage

### OCR Monitoring Only
1. **Launch ARK: Survival Ascended** and get to the main game screen
2. **Run AscendedScout**:
   ```bash
   python ascendedscout.py
   ```

### With Discord Bot Integration  
1. **Launch ARK: Survival Ascended** and get to the main game screen
2. **Configure your Discord bot token** in `bot.py`
3. **Run the main application**:
   ```bash
   python main.py
   ```
   
### Monitoring Output
- **Console**: Real-time detection feedback
- **Log files** in the `logs/` directory:
   - `tribemembers_log.txt` - Tribe member activities
   - `players_log.txt` - General player activities  
   - `center_log.txt` - Structure destruction events
- **Discord**: Real-time notifications (if bot is configured)

### Stopping the Application
Press `Ctrl+C` to stop monitoring gracefully.

## 📁 Project Structure

```
AscendedScout/
├── ascendedscout.py          # Core OCR monitoring application
├── bot.py                    # Secret Spy Discord bot
├── main.py                   # Integrated launcher (OCR + Bot)
├── requirements.txt          # Python dependencies
├── logs/                     # Generated log files (auto-created)
│   ├── tribemembers_log.txt  # Tribe member events
│   ├── players_log.txt       # Player join/leave events
│   └── center_log.txt        # Structure destruction events
├── assets/                   # Audio files and resources
│   └── ALERT NUKE.mp3       # Alert sound for critical events
├── README.md                 # This file
└── LICENSE                   # MIT License
```

## ⚙️ Configuration

### Screen Regions
The script monitors two specific areas of your screen:

- **Top Region** (`top_zone`): Player join/leave notifications
  - Default: `{'top': 0, 'left': 750, 'width': 550, 'height': 100}`
- **Center Region** (`center_zone`): Structure destruction messages
  - Default: `{'top': 211, 'left': 772, 'width': 374, 'height': 539}`

### Tesseract Path
If Tesseract is installed in a different location, update this line:
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

## 🎯 How It Works

1. **Screen Capture**: Uses MSS (Multi-Screen Shot) to capture specific screen regions
2. **Change Detection**: Compares frames to detect new notifications
3. **OCR Processing**: Multiple preprocessing techniques for different text colors and conditions
4. **Pattern Recognition**: Regex patterns extract player names, actions, and timestamps
5. **Smart Logging**: Deduplication and organized logging prevent spam and maintain clean records

### OCR Processing Pipeline
- **Color-based filtering**: Separate processing for red, blue, and green text
- **Image preprocessing**: Gaussian blur, bilateral filtering, and threshold optimization
- **Multi-method approach**: Combines results from different OCR configurations
- **Text normalization**: Unicode normalization and cleanup for consistent results

## 🐛 Troubleshooting

### Common Issues

**OCR not detecting text properly**:
- Ensure ARK is running in windowed or borderless windowed mode
- Check that Tesseract is properly installed and in PATH
- Verify screen coordinates match your display setup
- Try adjusting game UI scale settings

**High CPU usage**:
test done on intel i5-14600k
CPU: ~11–12% on average (peaks up to ~20%), RAM: ~81 MB average (74 MB idle, up to ~86 MB peak), Threads: ~55 threads in active mode (32 idle)
Disk I/O: Read: ~50–200 KB/s, Write: ~100–400 KB/s during active logging

- Increase the sleep interval in the main loop if it's too much for your CPU(default: 1 second)
- Reduce monitoring region sizes if possible

**False positives/negatives**:
- Check if game UI elements are overlapping monitored regions
- Adjust OCR confidence thresholds
- Update regex patterns for your server's specific messages

### Debug Mode
Add print statements to see raw OCR output:
```python
print(f"[DEBUG OCR] Raw text: {raw_text}")
```

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Report bugs** - Create detailed issue reports
2. **Suggest features** - Ideas for new monitoring capabilities
3. **Submit pull requests** - Code improvements and fixes
4. **Documentation** - Help improve setup guides and troubleshooting

### Development Setup
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📋 Roadmap

- [ ] GUI interface for easier configuration
- [ ] Advanced analytics and reporting

## 🎮 Secret Spy Discord Bot

The included Discord bot provides:
- **Instant notifications** for all detected events
- **Custom channel routing** for different alert types
- **Rich embed messages** with formatted timestamps
- **Audio alerts** for critical structure destruction events
- **Configurable filtering** to reduce notification spam

> **💡 Tip**: The bot is designed to work seamlessly with the OCR monitor. Run `main.py` to start both components together!

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is designed for monitoring purposes and should be used in accordance with ARK: Survival Ascended's terms of service. The developers are not responsible for any issues arising from the use of this software.

## 🙏 Acknowledgments

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - OCR engine
- [OpenCV](https://opencv.org/) - Computer vision library
- [MSS](https://github.com/BoboTiG/python-mss) - Screen capture library
- ARK: Survival Ascended community

---

**Made with ❤️ for the ARK community**

*Star ⭐ this repository if you find it useful!*

## Support
This project is MIT and free. If it saves your base one night, you can
[buy me a coffee](https://buymeacoffee.com/aminechadjaa) ☕. Thanks!
