#
# MIT License
#
# (C) Copyright 2023 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
"""
Configure how warnings from the warnings module should be logged.
"""

import logging
import re
import warnings

from urllib3.exceptions import InsecureRequestWarning

from sat.config import get_config_value


def configure_insecure_request_warnings():
    """Configure the handling of InsecureRequestWarning.

    Returns:
        None.
    """
    logging.captureWarnings(True)

    # Use filters with regexes matching the API gateway and s3 host parameters, so that
    # the 'once' action will log one warning per host to which an insecure request is made,
    # rather than just one warning after the first insecure request.
    warnings.filterwarnings(
        action='once', category=InsecureRequestWarning,
        message=rf'^.*\'{re.escape(get_config_value("api_gateway.host"))}\''
    )
    s3_hostname = re.sub(r'https?://', '', get_config_value("s3.endpoint"))
    warnings.filterwarnings(
        action='once', category=InsecureRequestWarning,
        message=rf'.*\'{re.escape(s3_hostname)}\''
    )

    # Overriding format_warning makes the format of the insecure request warnings
    # look much nicer.
    orig_format_warning = warnings.formatwarning

    def format_warning(warning, *args, **kwargs):
        if not isinstance(warning, InsecureRequestWarning):
            return orig_format_warning(warning, *args, **kwargs)

        return str(warning)
    warnings.formatwarning = format_warning
