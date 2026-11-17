#!/bin/sh
# Manual install / removal of os-ntopng-export, without building the package.
# Run as root on the OPNsense firewall, from the plugin directory:
#   sh install.sh          install (or update)
#   sh install.sh remove   remove
set -e

DEST=/usr/local/opnsense
cd "$(dirname "$0")"

flush() {
    # the web GUI keeps its menu and ACL caches in /var/lib/php/tmp
    rm -f /var/lib/php/tmp/opnsense_menu_cache.xml /var/lib/php/tmp/opnsense_acl_cache.json \
          /tmp/opnsense_menu_cache.xml /tmp/opnsense_acl_cache.json
    service configd restart
}

if [ "$1" = "remove" ]; then
    rm -rf "${DEST}/mvc/app/controllers/OPNsense/NtopngExport" \
           "${DEST}/mvc/app/models/OPNsense/NtopngExport" \
           "${DEST}/mvc/app/views/OPNsense/NtopngExport" \
           "${DEST}/scripts/ntopngexport" \
           "${DEST}/service/conf/actions.d/actions_ntopngexport.conf"
    flush
    echo "os-ntopng-export removed (settings in config.xml are kept)."
    exit 0
fi

cp -R src/opnsense/. "${DEST}/"
chmod 755 "${DEST}/scripts/ntopngexport/export.py"
flush
echo "os-ntopng-export installed. Reload the web GUI: Services -> ntopng Export."
