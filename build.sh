#!/usr/bin/env bash

# Exit on error
set -o errexit

# 1. Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# 2. MANUAL TAILWIND BUILD
echo "🚀 Starting Manual Tailwind Build..."
cd theme/static_src

# Clean and setup bin directory
rm -rf bin
mkdir -p bin

echo "⬇️ Downloading Tailwind v3.4.17..."
curl -L https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-linux-x64 -o bin/tailwindcss
chmod +x bin/tailwindcss

echo "🎨 Compiling CSS..."
./bin/tailwindcss -i ./src/input.css -o ../static/css/dist/styles.css --minify
cd ../..

# 3. FORCE STATIC FILES (The Nuclear Option)
echo "💣 DELETING old staticfiles folder..."
rm -rf staticfiles
mkdir -p staticfiles

echo "📦 Collecting Static Files..."
# We use || true because Whitenoise/Django might complain about missing files
# that we are about to manually copy anyway.
python manage.py collectstatic --no-input --clear || true

echo "💪 MANUALLY COPYING IMAGES & ASSETS..."
# Ensures theme assets are physically present in the final serving directory
cp -r theme/static/* staticfiles/

# 4. DEBUG: PRINT FILE LIST
echo "🔍 DEBUG: Checking file names in staticfiles/img..."
if [ -d "staticfiles/img" ]; then
    ls -la staticfiles/img/
else
    echo "⚠️ No img folder found in staticfiles/"
fi

# 5. Create Runtime Script
echo "📝 Creating run.sh..."
cat << 'EOF' > run.sh
#!/bin/bash
set -e
echo "➡️  Running Database Migrations..."
python manage.py migrate
echo "➡️  Starting Server..."
gunicorn config.wsgi:application --log-file -
EOF

chmod +x run.sh

echo "✅ Build Process Complete!"