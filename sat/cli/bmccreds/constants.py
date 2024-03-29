#
# MIT License
#
# (C) Copyright 2021, 2024 Hewlett Packard Enterprise Development LP
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
Constant values for the bmccreds subcommand.
"""
import string

# The username that bmccreds will always use
BMC_USERNAME = 'root'

# The maximum length of user-supplied passwords
USER_PASSWORD_MAX_LENGTH = 8

# The maximum number of xnames to display in the confirmation message
MAX_XNAMES_TO_DISPLAY = 20

# The length of randomly-generated passwords
RANDOM_PASSWORD_LENGTH = 8

VALID_CHAR_SETS = {
    'alpha': string.ascii_letters,
    'numeric': string.digits,
    'symbols': '!@#$%^&*'
}

VALID_CHAR_SETS_STRING = ''.join(VALID_CHAR_SETS.values())
