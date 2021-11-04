"""
Client for querying the API gateway.

(C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP.

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
# Import these names so that they can still be imported from the apiclient package directly
from sat.apiclient.bos import BOSClient
from sat.apiclient.capmc import CAPMCClient, CAPMCError
from sat.apiclient.cfs import CFSClient
from sat.apiclient.fabric import FabricControllerClient
from sat.apiclient.fas import FASClient
from sat.apiclient.fox import FoxClient
from sat.apiclient.gateway import APIError, APIGatewayClient, ReadTimeout
from sat.apiclient.hsm import HSMClient
from sat.apiclient.ims import IMSClient
from sat.apiclient.sls import SLSClient
from sat.apiclient.telemetry import TelemetryAPIClient


# The following simple API clients for CRUS, NMD, and SCSD only define their
# base_resource_path, so they don't warrant having their own modules yet.

class CRUSClient(APIGatewayClient):
    base_resource_path = 'crus/'


class NMDClient(APIGatewayClient):
    base_resource_path = 'v2/nmd/'


class SCSDClient(APIGatewayClient):
    base_resource_path = 'scsd/v1/'
