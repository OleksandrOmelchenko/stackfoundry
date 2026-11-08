#!/bin/bash
# Copy the dotnet-web-and-wpf fixture into the empty eval workspace and commit it.
set -euo pipefail
SCAFFOLD_LIB="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/../../../../fixtures/scaffold-lib.sh"
. "$SCAFFOLD_LIB"
scaffold dotnet-web-and-wpf 
