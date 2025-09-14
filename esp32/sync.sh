#!/bin/bash
# sync.sh - Simple ESP32 file synchronization

echo "🔄 Syncing ESP32 files..."

# Check if mpremote is available
if ! command -v mpremote &> /dev/null; then
    echo "❌ Error: mpremote not found. Install with: pip install mpremote"
    exit 1
fi

# Ensure we're in the esp32 directory
if [[ ! -f "tracker.py" ]]; then
    echo "❌ Error: Must be run from esp32/ directory"
    echo "💡 Usage: cd esp32/ && ./sync.sh"
    exit 1
fi

# Copy all Python files to ESP32
echo "📁 Copying files..."
for file in *.py; do
    if [[ -f "$file" ]]; then
        echo "  → $file"
        mpremote fs cp "$file" : || { echo "❌ Failed to copy $file"; exit 1; }
    fi
done

echo "🔄 Restarting ESP32..."
mpremote reset

echo "✅ Sync complete!"
echo "💡 Use 'mpremote repl' to connect for debugging"