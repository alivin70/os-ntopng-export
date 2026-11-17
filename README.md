# os-ntopng-export

An [OPNsense](https://opnsense.org/) plugin that exports the **traffic history of a single host**
(the data behind the ntopng charts) to a **CSV file**, with values in MB.

ntopng Community Edition shows per-host traffic only as a chart and has no data export.
This plugin adds a page under **Services → ntopng Export** where you pick a day and an IP
address and download the hourly traffic as CSV, ready to open in Excel or LibreOffice.

> **Disclaimer:** this is an independent project. It is not affiliated with, endorsed by,
> or supported by ntop or the OPNsense project.

## Features

- Pick a **day** (calendar) and a **host** (from a configurable list), download the CSV.
- Uses the ntopng **REST API**, so it works with ntopng **Community**. No extra software to install.
- Authenticates with an ntopng **API token** (recommended) or username/password.
- Access controlled by OPNsense's own login and privileges (**"Services: ntopng Export"**).
- Day boundaries follow the firewall's timezone.

### Output

```
timestamp;MB_inviati;MB_ricevuti
2026-10-03 23:00:00;2,2;1,0
2026-10-04 00:00:00;;2,5
2026-10-04 01:00:00;1,2;
```

- Semicolon separator, **decimal comma**, one decimal digit (Italian-locale spreadsheets open it directly in columns).
- Values are **total MB per hour** (1 MB = 1024 × 1024 bytes). ntopng reports average bytes/s;
  the plugin multiplies by the step.
- Empty cells where ntopng has no data (it returns `null`).
- For past days ntopng keeps **hourly** resolution, so that is what you get.

## Tested with

- OPNsense 26.1.10
- ntopng Community v6.6 (`os-ntopng` plugin)

Other versions are likely to work as long as the ntopng timeseries REST endpoint
(`/lua/rest/v2/get/timeseries/ts.lua`) behaves the same, but they have not been tested.

## Installation

OPNsense can only install plugins from a repository, not from a file uploaded in the web UI,
so there are two options.

### Option 1: install the files directly (simplest)

On the firewall, as root (SSH, then menu option **8) Shell**):

```sh
cd /tmp
fetch -o os-ntopng-export.tar.gz https://github.com/alivin70/os-ntopng-export/archive/refs/heads/main.tar.gz
tar xzf os-ntopng-export.tar.gz
cd os-ntopng-export-main
sh install.sh
```

Then reload the web GUI (Ctrl+F5). The entry appears under **Services → ntopng Export**.

- Update: repeat the same steps.
- Remove: `sh install.sh remove` (your settings stay in the configuration).
- Files installed this way are not tracked by the package manager. After a major OPNsense
  upgrade, if the menu entry disappears, simply run `sh install.sh` again.

If the menu entry does not show up, clear the GUI caches and reload:

```sh
rm -f /var/lib/php/tmp/opnsense_menu_cache.xml /var/lib/php/tmp/opnsense_acl_cache.json
```

### Option 2: build the package

On an OPNsense/FreeBSD build host with the
[plugins repository](https://github.com/opnsense/plugins) checked out
(for example under `/usr/plugins`):

```sh
cp -R os-ntopng-export /usr/plugins/net-mgmt/ntopng-export
cd /usr/plugins/net-mgmt/ntopng-export
make package
pkg add work/pkg/os-ntopng-export-*.pkg   # on the firewall
```

## Configuration

**Services → ntopng Export → Settings**

| Field | Description |
|-------|-------------|
| ntopng URL | Address ntopng listens on, e.g. `https://127.0.0.1:3443` |
| Verify certificate | Leave off for a self-signed certificate |
| ntopng interface id | The value after `ifid:` in ntopng requests (visible in the URL when browsing an interface in ntopng). It is **not** always `0` |
| API token | Recommended. ntopng: user menu → Manage Users → API token. Takes precedence over username/password |
| Username / Password | Alternative to the token |
| Hosts | IP addresses selectable on the export page |

## Usage

1. Open **Services → ntopng Export → Export**.
2. Choose the **day** and the **IP address**.
3. Click **Download CSV** (`traffico_<IP>_<YYYY-MM-DD>.csv`).

If no data is returned, check the interface id, that the day is within ntopng's retention,
and that host timeseries are enabled in ntopng (Settings → Preferences → Timeseries).

### Troubleshooting

Run the backend by hand on the firewall; it prints JSON with the CSV or the error:

```sh
configctl ntopngexport export 2026-10-04 100.100.100.110
```

Logs: **System → Log Files** (Backend and Web GUI).

## How it works

```
Export page ──▶ /api/ntopngexport/export/csv ──▶ configd action ──▶ export.py ──▶ ntopng REST API
                (validates day + host)                              (reads /conf/config.xml)
```

```
src/opnsense/
├── mvc/app/controllers/OPNsense/NtopngExport/   pages, API, settings form
├── mvc/app/models/OPNsense/NtopngExport/        model, menu, ACL
├── mvc/app/views/OPNsense/NtopngExport/         Export and Settings pages
├── scripts/ntopngexport/export.py               backend (runs as root via configd)
└── service/conf/actions.d/actions_ntopngexport.conf
```

## Security notes

- The API token / password is stored in the OPNsense configuration (`config.xml`). Prefer the token.
- Day and host are strictly validated, and the host must be in the configured list, before
  anything is passed to the backend command.
- TLS verification is off by default because ntopng commonly uses a self-signed certificate.
  Keep this in mind if ntopng is reached over an untrusted network.

## Roadmap / ideas

- Configurable CSV language (headers), decimal separator and delimiter.
- Date ranges spanning several days; export of other series (e.g. per-protocol traffic).
- Package published through a repository, so it can be installed from the Firmware page.

## Contributing

Issues and pull requests are welcome at <https://github.com/alivin70/os-ntopng-export>.
Please mention your OPNsense and ntopng versions when reporting a problem.

## License

BSD 2-Clause. See [LICENSE](LICENSE).
