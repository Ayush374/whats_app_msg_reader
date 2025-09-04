# WhatsApp Message Reader 📱

A powerful Python script that automatically monitors and extracts messages from multiple WhatsApp groups using Selenium WebDriver. Perfect for tracking important conversations across different groups without manually checking each one.

## 🌟 Features

- **Multi-Group Monitoring**: Monitor multiple WhatsApp groups simultaneously
- **Real-time Message Extraction**: Continuously checks for new messages
- **Media Detection**: Identifies and logs images, videos, audio files, and documents
- **Data Export**: Saves messages to both JSON and Excel formats
- **Persistent Session**: Uses Chrome user data to maintain WhatsApp Web login
- **Duplicate Prevention**: Tracks seen messages to avoid duplicates
- **Robust Search**: Multiple fallback mechanisms to find and open chats

## 📋 Prerequisites

Before running this script, make sure you have:

- Python 3.7+
- Google Chrome browser
- ChromeDriver (matching your Chrome version)
- Active WhatsApp account with WhatsApp Web access

## 🛠️ Installation

1. **Clone the repository**:
```bash
git clone https://github.com/Ayush374/smart-whatsapp-assistant.git
cd smart-whatsapp-assistant
```

2. **Install required packages**:
```bash
pip install selenium pandas openpyxl
```

3. **Install ChromeDriver**:
   - Download from [ChromeDriver Downloads](https://chromedriver.chromium.org/)
   - Add to PATH or place in project directory
   - Ensure version matches your Chrome browser

## ⚙️ Configuration

Edit the configuration section in the script:

```python
# ------------ CONFIG ------------
GROUP_NAMES = [
    "Testing automation",
    "SD Tulshan Family", 
    "Adarsh b'day party",
    "Tulshan Family"
]
USER_DATA_DIR = "./User_Data"
OUT_DIR = "./logs"      # per-group JSON files
POLL_SECS = 5           # pause between cycles
SEARCH_SETTLE = 1.2     # time to let results populate after typing
# --------------------------------
```

### Configuration Options:

- **GROUP_NAMES**: List of WhatsApp group/chat names to monitor
- **USER_DATA_DIR**: Directory to store Chrome user data (maintains login)
- **OUT_DIR**: Directory where message logs will be saved
- **POLL_SECS**: Time interval between monitoring cycles (seconds)
- **SEARCH_SETTLE**: Wait time after typing in search box (seconds)

## 🚀 Usage

1. **First Run Setup**:
```bash
python connect_wa_whitelist.py
```

2. **Login to WhatsApp Web**:
   - Script will open Chrome with WhatsApp Web
   - Scan QR code with your phone (first time only)
   - Wait for "Waiting for WhatsApp Web to load and login..." message

3. **Automatic Monitoring**:
   - Script will cycle through your configured groups
   - New messages will be displayed in terminal
   - Files are automatically saved to the logs directory

4. **Stop the Script**:
   - Press `Ctrl+C` to stop monitoring

## 📁 Output Files

For each monitored group, the script creates:

- **`{group_name}.json`**: JSON format with message data
- **`{group_name}.xlsx`**: Excel spreadsheet format

### Message Format:
```json
{
  "time": "[14:30, 04/09/2025]",
  "text": "Hello everyone!"
}
```

## 🔍 Message Types Detected

The script identifies and logs:
- **Text Messages**: Regular chat messages
- **Media Messages**: 
  - `[Image]` - Photos and images
  - `[Video]` - Video files
  - `[Audio]` - Voice messages and audio files
  - `[Document]` - PDF, DOC, and other documents
- **Media with Captions**: Shows media type + caption text

## 🛡️ Safety Features

- **Duplicate Prevention**: Tracks seen messages to avoid logging duplicates
- **Error Handling**: Continues running even if individual messages fail to parse
- **Graceful Shutdown**: Properly closes browser on script termination
- **Search Cleanup**: Clears search box between group switches

## 🔧 Troubleshooting

### Common Issues:

1. **ChromeDriver not found**:
   ```
   selenium.common.exceptions.WebDriverException: 'chromedriver' executable needs to be in PATH
   ```
   **Solution**: Install ChromeDriver and add to PATH

2. **WhatsApp Web not loading**:
   ```
   TimeoutException: Message: 
   ```
   **Solution**: Check internet connection, try refreshing browser

3. **Group not found**:
   ```
   ❌ No search result clickable for 'Group Name'
   ```
   **Solution**: Verify group name spelling matches exactly in WhatsApp

4. **Permission errors**:
   ```
   PermissionError: [Errno 13] Permission denied
   ```
   **Solution**: Run with appropriate permissions or change output directory

### Debug Tips:

- Check that group names in `GROUP_NAMES` match exactly (case-sensitive)
- Ensure WhatsApp Web is fully loaded before the script starts monitoring
- Verify Chrome browser and ChromeDriver versions are compatible

## 📊 Example Output

```
🌀 ===== New cycle over all groups =====
🔍 Searching for group: Testing automation
✅ Group 'Testing automation' opened.
🔄 Checking for new messages in 'Testing automation'...
📨 Found 15 total messages in DOM.
🆕 New message in 'Testing automation': [14:30, 04/09/2025] Hello team!
💾 Writing 1 messages for 'Testing automation' → ./logs/Testing_automation.json
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## ⚠️ Disclaimer

This tool is for personal use only. Please respect WhatsApp's Terms of Service and privacy policies. Use responsibly and ensure you have permission to monitor the groups you're accessing.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Selenium WebDriver](https://selenium-python.readthedocs.io/)
- Data processing with [Pandas](https://pandas.pydata.org/)
- WhatsApp Web interface

---

**Author**: Ayush374  
**Contact**: ayushtul@gmail.com  
**Repository**: https://github.com/Ayush374/smart-whatsapp-assistant
