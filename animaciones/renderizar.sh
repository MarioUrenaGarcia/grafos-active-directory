#!/usr/bin/env bash
# Renderiza las escenas indicadas, una por una, con sus tiempos de escenas.json.
set -u
cd "$1"; shift
export HYPERFRAMES_NO_TELEMETRY=1 HYPERFRAMES_SKIP_SKILLS=1
for nombre in "$@"; do
  read -r ini fin < <(python -c "
import json, sys
e = {x['escena']: x for x in json.load(open('escenas.json'))}[sys.argv[1]]
print(e['inicio'], e['inicio'] + e['duracion'])" "$nombre")
  if npx --yes hyperframes@0.9.19 render --start "$ini" --end "$fin" --crf 24 --output "clips/$nombre.mp4" > "clips/$nombre.log" 2>&1; then
    echo "ok $nombre $(du -k "clips/$nombre.mp4" | cut -f1) KB"
  else
    echo "FALLO $nombre (ver clips/$nombre.log)"
  fi
done
