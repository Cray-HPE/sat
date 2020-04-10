"""
Session capture and playback for the sensors subcommand.

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import json
import glob
import logging
import shutil
import tarfile
import tempfile
import os.path
import os

from functools import partial, partialmethod
from datetime import datetime, timezone, timedelta
from argparse import Namespace

from sat.report import Report
from sat.cli.sensors.bmc import BMC
from sat.cli.sensors import __name__ as subcommand_name

LOGGER = logging.getLogger(__name__)

CAPTURE_NAME = os.getenv('SAT_SENSORS_CAPTURE', None)

# A capture is enabled by setting the environment variable SAT_SENSORS_CAPTURE,
# and setting one or more of the command line parameters --capture-comm,
# --capture-data, --capture-logs. Usage help is available for these if the
# environment variable is set.

# A captured session is generated in a temporary directory and then saved to a
# .tgz when capture is complete, unless --no-zip is specified, in which case
# the temporary directory is retained. Its location was logged at the INFO
# level at the beginning of the capture session.

# Three components may be captured: the BMC query cache, consisting of Redfish
# requests and responses, data, consisting of a row passed to the Report class,
# serialized to JSON, and logs under sat.cli.sensors. Log entries outside sat.
# cli.sensors or in external libraries (such as requests or urllib3) are not
# included.

# The tgz file has a flat structure, but all files are one directory deep. This
# allows for easy expanding without accidental overwriting. The single entry is
# generated from the SAT_SENSORS_CAPTURE value, which may be any filesystem-
# friendly string, but is suggested to be the name of the system the capture is
# run on (i.e. rocket), combined with a timestamp.

# Within this directory each BMC query cache is stored separately, and the
# combined data and logs are stored in a log file, if either data or logs
# is captured. Additionally, some meta-information is saved.


class CaptureReport(Report):
    def add_row(self, row):
        super().add_row(row)
        LOGGER.data(json.dumps(row))


class CaptureManager:
    def __init__(self, args):
        self._seq = []

        self._bmc = None
        self._bmc_t0 = None

        self._handler = None
        self.timestamp = datetime.now(timezone.utc)

        self.capture_def = capture_def = Namespace(name=CAPTURE_NAME)

        if capture_def.name is None:
            capture_def.comm = False
            capture_def.data = False
            capture_def.logs = False

            self.output_dir = None
            self.no_zip = False
        else:
            capture_def.comm = args.capture_comm
            capture_def.data = args.capture_data
            capture_def.logs = args.capture_logs

            self.output_dir = args.capture_dir
            self.no_zip = args.no_zip

        if self:
            self.temp_dir = tempfile.mkdtemp()
            LOGGER.info('Capture enabled; temporary directory: %s', self.temp_dir)

            if capture_def.data or capture_def.logs:
                # A LogHandler is created that saves logs from sat.cli.sensors.*
                # and data (if enabled) in a combined logfile saved to the capture.
                # This ensures that logs and data are in sequence without dependence
                # on clocks, which may be unresolvable during playback, and would have
                # to be filtered out before comparisons are made.

                # A new logLevel "DATA" is introduced for the data entries. Its numeric
                # value depends on whether the other log messages are to be captured or
                # not.

                # If log capturing is enabled, the DATA logLevel is set low, so that
                # normal log entries will have a higher priority, and a handler set to
                # log at DATA's priority and higher will also log these.

                # If log capturing is off but data capturing is on, the loglevel of data
                # is set to be higher than CRITICAL, so the rest of the logs are lower
                # priority and are passed over.

                # If log capturing is on, but not data capturing, then the DEBUG priority is used,
                # to capture all (under sat.cli.sensors).

                # A side-effect is if the higher priority is used, data entries will be sent to the
                # console (and log file). This is a developer's nuisance that doesn't arise in normal
                # usage, and should be fixable with the logging framework's filters.

                if capture_def.data:
                    logging.DATA = (logging.DEBUG - 5) if capture_def.logs else (logging.CRITICAL + 5)
                    logging.addLevelName(logging.DATA, 'DATA')

                    logging.Logger.data = partialmethod(logging.Logger.log, logging.DATA)
                    logging.data = partial(logging.log, logging.DATA)

                    logLevel = logging.DATA
                else:
                    logLevel = logging.DEBUG

                captureHandler = logging.FileHandler(os.path.join(self.temp_dir, self.log_filename))

                captureFormatter = logging.Formatter('CAPTURE %(levelname)s - %(name)s - %(message)s')
                captureHandler.setFormatter(captureFormatter)

                captureLogger = logging.getLogger(subcommand_name)
                captureLogger.addHandler(captureHandler)
                captureLogger.setLevel(logLevel)

                self._handler = captureHandler

        else:
            if CAPTURE_NAME:
                LOGGER.warning('Capture enabled, but not defined. Pass one or more of: '
                               '--capture-comm, --capture-data, --capture-args, or -h/'
                               '--help for usage information')

    @property
    def log_filename(self):
        return ('_'.join((['data'] if self.capture_def.data else []) +
                         (['logs'] if self.capture_def.logs else [])) + '.log')

    def shutdown(self):
        if not self:
            return

        if self._handler:
            self._handler.close()

        if self._bmc:
            self._close_bmc()

        capture_def = self.capture_def

        with open(os.path.join(self.temp_dir, 'capture_info.json'), 'w') as f:
            json.dump(dict(
                version=1,
                BMCs=self._seq,
                timestamp=str(self.timestamp),
                capture_def=vars(capture_def)), f)

        if not self.no_zip:
            output_dir = self.output_dir or '.'

            if not os.path.exists(output_dir):
                LOGGER.error('Capture output directory "%s" does not exist', output_dir)
                return

            fs_id = 'sat_sensors_capture-{}-{}'.format(CAPTURE_NAME, self.timestamp.strftime('%Y%m%d_%H%M%S'))
            base_filename = os.path.join(self.output_dir or '.', fs_id + '.tgz')

            if os.path.exists(base_filename):
                n = 1
                while True:
                    filename = '{}.{:d}'.format(base_filename, n)
                    if os.path.exists(filename):
                        n += 1
                    else:
                        break
            else:
                filename = base_filename

            with tarfile.open(filename, 'w:gz') as tf:
                for fn in glob.glob(os.path.join(self.temp_dir, '*')):
                    tf.add(fn, os.path.join(fs_id, os.path.basename(fn)))

            LOGGER.info('Saved captured session to: %s', filename)

            shutil.rmtree(self.temp_dir)

    def __bool__(self):
        """Instance evaluates as True if any of the capture streams is active.
        """

        capture_def = self.capture_def
        return capture_def.comm or capture_def.data or capture_def.logs

    def _close_bmc(self):
        if self.capture_def.comm:
            with open(os.path.join(self.temp_dir, self._bmc.xname) + '_comm.json', 'w') as f:
                self._bmc.dump(f)

        self._seq.append(dict(xname=self._bmc.xname,
                         elapsed_ms=(datetime.now(timezone.utc) - self._bmc_t0) / timedelta(milliseconds=1)))

    def bmc_factory(self, xname, username, password):
        """Thin wrapper that simply logs each BMC and the amount of time it was "active".
        """

        # False/failed or unset
        if self._bmc:
            self._close_bmc()

        self._bmc_t0 = datetime.now(timezone.utc)
        self._bmc = BMC(xname, username, password)

        return self._bmc

    def get_report(self, *args, **kwargs):
        """Factory for Report (or a subclass) instances.

           Returns a CaptureReport instance if data capture is enabled.
        """

        if self.capture_def.data:
            return CaptureReport(*args, **kwargs)
        else:
            return Report(*args, **kwargs)
