#!/usr/bin/env bash
set -o errexit

# Python dependencies for the mcp to run
pip install -r requirements.txt

STORAGE_DIR=/opt/render/project/.render

if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "...Downloading Chrome"
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  wget -P ./ https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x ./google-chrome-stable_current_amd64.deb $STORAGE_DIR/chrome
  rm ./google-chrome-stable_current_amd64.deb
  cd $HOME/project/src
else
  echo "...Using Chrome from cache"
fi

# Add Chrome to PATH
export PATH="${PATH}:${STORAGE_DIR}/chrome/opt/google/chrome"
echo "Build completed! Chrome binary is at $STORAGE_DIR/chrome/opt/google/chrome/google-chrome"

