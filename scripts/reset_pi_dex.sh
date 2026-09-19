#!/bin/bash
# Run this ON THE PI, and only after confirming the scp pull to your laptop
# actually succeeded -- this deletes the Pi's copy of dex/log.csv and crops
# so the next flight starts clean instead of the Pi accumulating data forever.
set -e
cd ~/PassionJuice
head -1 dex/log.csv > dex/log.csv.new && mv dex/log.csv.new dex/log.csv
rm -rf dex/crops && mkdir dex/crops
echo "Pi's dex/ reset to empty -- ready for the next flight."
