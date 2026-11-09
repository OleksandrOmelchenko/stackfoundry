#!/bin/bash
# Copy the python-fastapi fixture with its stackfoundry profile into the empty eval workspace and commit it.
set -euo pipefail
SCAFFOLD_LIB="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/../../../../fixtures/scaffold-lib.sh"
. "$SCAFFOLD_LIB"
scaffold python-fastapi with-profile
