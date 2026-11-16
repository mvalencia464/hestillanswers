#!/bin/bash
# Downloads the public-domain artwork listed in backgrounds/credits.csv (The Met, Open Access)
# into backgrounds/, named by post id, so the image engine can use it. Double-click to run.
cd "$(dirname "$0")/.." || exit 1
mkdir -p backgrounds
ok=0; bad=0
while IFS= read -r line; do
  line="${line%$'\r'}"; id="${line%%,*}"; url="${line##*,}"
  [ "$id" = "id" ] && continue; [ -z "$url" ] && continue
  printf "%s ... " "$id"
  if curl -L --fail -sS -m 180 -A "Mozilla/5.0 (Macintosh)" -o "backgrounds/$id.jpg" "$url"; then echo "ok"; ok=$((ok+1)); else echo "FAILED"; rm -f "backgrounds/$id.jpg"; bad=$((bad+1)); fi
  sleep 1
done < backgrounds/credits.csv
echo; echo "$ok downloaded, $bad failed."
if python3 -c "import PIL, numpy" 2>/dev/null; then python3 engine/build_csv.py && python3 engine/render.py
else echo "Now tell Claude: \"photos are in\" and it will re-render those posts."; fi
echo; read -n 1 -s -r -p "Press any key to close."
