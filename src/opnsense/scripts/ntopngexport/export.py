#!/usr/local/bin/python3

"""
    Copyright (C) 2026 Vincenzo Bruno <https://github.com/alivin70>
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
     this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
    AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
    AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
    OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.

    --------------------------------------------------------------------------------------

    usage: export.py <YYYY-MM-DD> <ip>

    Query the ntopng REST API for the hourly traffic of a host and print a json
    document on stdout:
        {"status": "ok", "filename": "...", "csv": "..."}
        {"status": "error", "message": "..."}
"""
import csv
import io
import json
import re
import ssl
import sys
import xml.etree.ElementTree as ET
from base64 import b64encode
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

CONFIG_XML = '/conf/config.xml'
MB = 1024 * 1024  # 1 MB = 1024*1024 bytes, same convention ntopng uses


def finish(obj):
    print(json.dumps(obj))
    sys.exit(0)


def fail(message):
    finish({'status': 'error', 'message': message})


def load_settings():
    try:
        root = ET.parse(CONFIG_XML).getroot()
    except (OSError, ET.ParseError) as err:
        fail('Unable to read the configuration: %s' % err)
    node = root.find('OPNsense/ntopngexport/general')
    if node is None:
        fail('The plugin is not configured yet. Open the Settings page and save it.')

    def val(name, default=''):
        el = node.find(name)
        return el.text.strip() if el is not None and el.text else default

    settings = {
        'url': val('Url').rstrip('/'),
        'verify': val('VerifySsl') == '1',
        'ifid': val('IfId', '0'),
        'username': val('Username'),
        'password': val('Password'),
        'token': val('ApiToken'),
        'hosts': [h for h in val('Hosts').split(',') if h],
        'tz': root.findtext('system/timezone') or 'UTC',
    }
    return settings


def fetch(settings, host, day):
    try:
        tz = ZoneInfo(settings['tz'])
    except Exception:
        tz = timezone.utc
    y, m, d = (int(x) for x in day.split('-'))
    begin = int(datetime(y, m, d, 0, 1, tzinfo=tz).timestamp())
    end = int(datetime(y, m, d, 23, 59, tzinfo=tz).timestamp())

    qs = urlencode({
        'ts_schema': 'host:traffic',
        'ts_query': 'ifid:%s,host:%s' % (settings['ifid'], host),
        'tskey': host,
        'epoch_begin': begin,
        'epoch_end': end,
        'zoom': '1d',
        'limit': 180,
        'version': 4,
    })
    req = Request('%s/lua/rest/v2/get/timeseries/ts.lua?%s' % (settings['url'], qs))
    if settings['token']:
        req.add_header('Authorization', 'Token %s' % settings['token'])
    elif settings['username']:
        cred = b64encode(('%s:%s' % (settings['username'], settings['password'])).encode()).decode()
        req.add_header('Authorization', 'Basic %s' % cred)
    else:
        fail('No ntopng credentials configured (API token or username/password).')

    if settings['url'].startswith('https'):
        ctx = ssl.create_default_context()
        if not settings['verify']:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
    else:
        ctx = None

    try:
        with urlopen(req, context=ctx, timeout=60) as resp:
            body = resp.read().decode('utf-8', 'replace')
    except URLError as err:
        fail('Unable to contact ntopng: %s' % err)
    except Exception as err:
        fail('Request to ntopng failed: %s' % err)
    try:
        return json.loads(body), tz
    except ValueError:
        fail('Authentication refused or invalid response from ntopng.')


def build_csv(data, tz):
    if data.get('rc') not in (0, None):
        fail('ntopng error: %s' % data.get('rc_str', data.get('rc')))
    rsp = data.get('rsp', {})
    series = {s['id']: s['data'] for s in rsp.get('series', []) if 'id' in s}
    meta = rsp.get('metadata')
    if not series or not isinstance(meta, dict) or 'bytes_sent' not in series or 'bytes_rcvd' not in series:
        fail('No data available for this host and day (history expired, wrong interface id, '
             'or host timeseries not enabled in ntopng).')

    start, step = meta['epoch_begin'], meta['epoch_step']
    sent, rcvd = series['bytes_sent'], series['bytes_rcvd']

    def fmt(rate):
        # ntopng returns null for points without data: leave the cell empty
        if rate is None:
            return ''
        # values are average bytes/s: x step = total bytes in the interval
        return ('%.1f' % (rate * step / MB)).replace('.', ',')  # decimal comma for it_IT spreadsheets

    out = io.StringIO()
    w = csv.writer(out, delimiter=';', lineterminator='\r\n')
    w.writerow(['timestamp', 'MB_inviati', 'MB_ricevuti'])
    for i in range(len(sent)):
        t = datetime.fromtimestamp(start + i * step, tz).strftime('%Y-%m-%d %H:%M:%S')
        w.writerow([t, fmt(sent[i]), fmt(rcvd[i])])
    return out.getvalue()


def main():
    if len(sys.argv) != 3:
        fail('usage: export.py <YYYY-MM-DD> <ip>')
    day, host = sys.argv[1], sys.argv[2]
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
        fail('Invalid date.')
    try:
        datetime.strptime(day, '%Y-%m-%d')
    except ValueError:
        fail('Invalid date.')
    if not re.fullmatch(r'[0-9A-Fa-f:.]{2,45}', host):
        fail('Invalid IP address.')

    settings = load_settings()
    if host not in settings['hosts']:
        fail('Host is not in the configured list.')

    data, tz = fetch(settings, host, day)
    csv_text = build_csv(data, tz)
    finish({
        'status': 'ok',
        'filename': 'traffico_%s_%s.csv' % (host.replace(':', '_'), day),
        'csv': csv_text,
    })


if __name__ == '__main__':
    main()
