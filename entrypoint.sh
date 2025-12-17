#!/bin/bash
set -e

echo "Starting command: $@"

mn -c


# Start OVS in background
/usr/share/openvswitch/scripts/ovs-ctl start

# Now launch your command (e.g., Mininet)
exec "$@"
