#!/bin/sh
export PYTHONPATH="/app/lib/python3.11/site-packages:/app/lib/python3.12/site-packages:/app/lib/python3.13/site-packages:/app/share/aresta-editor:$PYTHONPATH"
exec python3 -m editor.main "$@"
