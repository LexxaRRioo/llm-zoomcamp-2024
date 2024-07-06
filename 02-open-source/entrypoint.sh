#!/bin/bash

# Start Ollama in the background.
/bin/ollama serve &
# Record Process ID.
pid=$!

# Pause for Ollama to start.
sleep 5

ollama -v

echo "🔴 Q2. Retrieve gemma:2b model..."
ollama pull gemma:2b
echo "🟢 Done!"

echo "🔴 Q3. Testing model..."
ollama run gemma:2b "10 * 10"
echo "🟢 Done!"

echo "🔴 Q4. Counting weights fulder size..."
du -h /root/.ollama/models
echo "🟢 Done!"

# Wait for Ollama process to finish.
wait $pid
