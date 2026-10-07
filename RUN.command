#!/bin/bash
cd -- "$(dirname -- "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if command -v python3 >/dev/null 2>&1; then
    python3 run_local.py
else
    echo "Python 3.12 yoki yangiroq versiyasini o‘rnating."
fi
read -r -p "Yopish uchun Enter bosing..."
