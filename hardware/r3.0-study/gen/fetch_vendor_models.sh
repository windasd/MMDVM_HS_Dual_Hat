#!/bin/sh
# Fetch the manufacturer 3D models that are freely downloadable into ../3dmodels/vendor (git-ignored:
# the files carry no redistribution licence, so they are not committed). Then run link_models.py.
set -e
cd "$(dirname "$0")/../3dmodels"
mkdir -p vendor
UA="Mozilla/5.0"
# RAKwireless download centre (linked from the RAK4630 documentation page)
curl -fsSL -o vendor/3D_RAK4630.stp "https://downloads.rakwireless.com/3D_File/WisDuo/3D_RAK4630.stp"
# Alps Alpine product page, "3D CAD" (zip with STEP + PDF)
tmp=$(mktemp -d)
curl -fsSL -A "$UA" -o "$tmp/skrt.zip" "https://tech.alpsalpine.com/cms.media/product_3dcad_skrtlae010_en_0a8d627682.zip"
unzip -q -o "$tmp/skrt.zip" -d "$tmp"
cp "$tmp/SKRTLAE010/SKRTLA.STEP" vendor/SKRTLA.STEP
rm -rf "$tmp"
ls -l vendor
