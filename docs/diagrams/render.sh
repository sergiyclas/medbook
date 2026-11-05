#!/bin/sh
# Renders every diagram to docs/diagrams/out/*.png after checking that the
# classes they show exist in the code. Needs Java, Graphviz and plantuml.jar:
#   PLANTUML_JAR=~/Downloads/plantuml/plantuml-1.2026.9.jar sh docs/diagrams/render.sh
set -e
cd "$(dirname "$0")"
: "${PLANTUML_JAR:?set PLANTUML_JAR to the path of plantuml.jar}"
python3 check_classes.py
java -DPLANTUML_LIMIT_SIZE=12000 -jar "$PLANTUML_JAR" -charset UTF-8 -tpng -o out ./*.puml
echo "Rendered: $(ls out | wc -l) diagrams in docs/diagrams/out"
