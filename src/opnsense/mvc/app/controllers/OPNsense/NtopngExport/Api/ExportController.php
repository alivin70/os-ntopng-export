<?php

/*
 * Copyright (C) 2026 Vincenzo Bruno <https://github.com/alivin70>
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice,
 *    this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
 * INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
 * AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 * AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
 * OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

namespace OPNsense\NtopngExport\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Backend;
use OPNsense\NtopngExport\NtopngExport;

class ExportController extends ApiControllerBase
{
    /**
     * Fetch the hourly traffic of one configured host for one day.
     * POST: day (YYYY-MM-DD), ip
     * returns {status: ok, filename, csv} or {status: error, message}
     */
    public function csvAction()
    {
        if (!$this->request->isPost()) {
            return ['status' => 'error', 'message' => 'POST required'];
        }

        $day = (string)$this->request->getPost('day');
        $ip = (string)$this->request->getPost('ip');

        // strict validation: these values end up as arguments of a backend command
        if (!preg_match('/^(\d{4})-(\d{2})-(\d{2})$/', $day, $m) || !checkdate((int)$m[2], (int)$m[3], (int)$m[1])) {
            return ['status' => 'error', 'message' => gettext('Invalid date.')];
        }
        $mdl = new NtopngExport();
        $allowed = array_filter(explode(',', (string)$mdl->general->Hosts));
        if (filter_var($ip, FILTER_VALIDATE_IP) === false || !in_array($ip, $allowed, true)) {
            return ['status' => 'error', 'message' => gettext('Invalid or unknown IP address.')];
        }

        $raw = (new Backend())->configdpRun('ntopngexport export', [$day, $ip]);
        $result = json_decode(trim($raw), true);
        if (!is_array($result) || !isset($result['status'])) {
            return ['status' => 'error', 'message' => gettext('Unable to run the export backend action.')];
        }
        return $result;
    }
}
