#!/data/data/com.termux/files/usr/bin/bash
# One-time Termux environment setup for the YouTube Shorts splitter script.
# Run this once with: bash setup_termux.sh

echo "Updating Termux packages..."
pkg update -y && pkg upgrade -y

echo "Installing Python, Git, and DejaVu font (for video watermark text)..."
pkg install python git ttf-dejavu -y

echo "Installing required Python packages..."
pip install -r requirements.txt

echo "Setup complete! You can now run: python youtube_shorts_splitter.py"