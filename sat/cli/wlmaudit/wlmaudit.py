#
# MIT License
#
# (C) Copyright 2025 Hewlett Packard Enterprise Development LP
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
Handle WLM audit commands
"""

# import logging
import json
import requests

from csm_api_client.service.gateway import APIError, APIGatewayClient
from sat.apiclient.fabric import FabricControllerClient
from sat.report import Report
from sat.session import SATSession


LOGGER = logging.getLogger(__name__)

from kubernetes import client, config


def get_slurm_net_topo_config():
    """Read configmap slurm-map from user namespace and return"""
    ret = {}
    # Load Kubernetes configuration
    config.load_kube_config()
    # Create an API client for CoreV1
    v1 = client.CoreV1Api()
    # Define the namespace and ConfigMap name
    namespace = "user"
    configmap_name = "slurm-map"
    key = "slurm.conf"
    try:
        get_switchconfig_frm_configmap(configmap_name, key, namespace, ret, v1)

    except client.exceptions.ApiException as e:
        print(f"Error fetching ConfigMap: {e}")
        return {}

    # Read configmap slurm-map for all tenants
    # Create an API client for Custom Resources
    custom_api = client.CustomObjectsApi()

    # slurmcluster's API group definitions
    api_group = "wlm.hpe.com"
    api_version = "v1alpha1"
    cr_name = "slurmclusters"
    try:
        slurm_clusters = custom_api.list_cluster_custom_object(
            api_group, api_version, cr_name
        )
        for item in slurm_clusters.get("items", []):
            print(
                f"Fetching configmap for SlurmCluster: {item['metadata']['name']} (Namespace: {item['metadata']['namespace']})"
            )

            get_switchconfig_frm_configmap(f"{item['metadata']['name']}-slurm-conf", key, f"{item['metadata']['namespace']}", ret, v1)

    except client.exceptions.ApiException as e:
        print(f"Error fetching ConfigMap for slurmclusters: {e}")
        return {}

    return ret


def get_switchconfig_frm_configmap(configmap_name, key, namespace, ret, v1):
    """Fetch switch related settings from the ConfigMap"""
    local_cf_settings = {}
    configmap = v1.read_namespaced_config_map(
        name=configmap_name, namespace=namespace
    )
    # Print the ConfigMap data
    print(f"ConfigMap '{configmap.metadata.name}' retrieved successfully")
    slurm_config = configmap.data[key]
    for config_line in slurm_config.split("\n"):
        if config_line.startswith("#") or not config_line:
            continue
        key, value = config_line.split("=", 1)
        if key in ("SwitchType", "SwitchParameters"):
            local_cf_settings[key] = value
            print(f"Read from slurm-config {key} : {value}")
    # for key, value in configmap.data.items():
    #     print(f"{key}: {value}")
    if len(local_cf_settings) > 0:
        ret[configmap_name] = local_cf_settings


def get_fabricmgr_vni_partitions():
    """Get VNI partitions from fabric manager"""
    ret = {}
    fabric_client = FabricControllerClient(SATSession())
    response = fabric_client.get("fabric", "vni", "partitions")
    # headers = {
    #     "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICI5OXhaeGJKQVV2Q2ZkSEJjbGxzOTN5aW5PMTRoa2NMbHdXR21kS0pOVkowIn0.eyJleHAiOjE3NjU2NjQ0NzAsImlhdCI6MTczNDEyODQ3MCwianRpIjoiNDhmM2QxYjktNWU5Ni00NzYxLTg5ZGEtNDU0ZjcxNTBlODNjIiwiaXNzIjoiaHR0cHM6Ly9hcGktZ3ctc2VydmljZS1ubW4ubG9jYWwva2V5Y2xvYWsvcmVhbG1zL3NoYXN0YSIsImF1ZCI6WyJzaGFzdGEiLCJjcmF5IiwiYWNjb3VudCJdLCJzdWIiOiI1YTliOWU0Yi1mM2QwLTRhNzktYTA4ZC0wZmNhODQ4NTBjODEiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJzaGFzdGEiLCJzZXNzaW9uX3N0YXRlIjoiNWQ5NjhhZGQtMTgxMi00MzE2LTk2MjItZTM4NTgxYzg3NmE4IiwiYWNyIjoiMSIsInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzLXNoYXN0YSIsIm9mZmxpbmVfYWNjZXNzIiwidW1hX2F1dGhvcml6YXRpb24iXX0sInJlc291cmNlX2FjY2VzcyI6eyJzaGFzdGEiOnsicm9sZXMiOlsiYWRtaW4iXX0sImNyYXkiOnsicm9sZXMiOlsiYWRtaW4iXX0sImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIGVtYWlsIHByb2ZpbGUiLCJzaWQiOiI1ZDk2OGFkZC0xODEyLTQzMTYtOTYyMi1lMzg1ODFjODc2YTgiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsIm5hbWUiOiJzc2lhZG1pbiBzc2lhZG1pbiIsImdyb3VwcyI6W10sInByZWZlcnJlZF91c2VybmFtZSI6InNzaWFkbWluIiwiZ2l2ZW5fbmFtZSI6InNzaWFkbWluIiwiZmFtaWx5X25hbWUiOiJzc2lhZG1pbiJ9.G3BD1I15_31MnO062_sDoZW_pZlfVP4tvk2FvhbnUL-9woZD01vjjORq3nh0pDKOgn_gpLrjkPSO68Qe4nuEPoLeizzS96XhwU9qtsVEpbAhXFIoMpHZ6xBjb57ggOpn-jgi_xH6bcI0U0eqyd3Wuh-jBSVVYgWvLs978JYnU6HsARNw4nRmERTfLio0KKhpGT22mOSYXOGQUWWVs9VqJhs7OvL_43nNHriubIO3dKrRw83OrtE0XTTdJ19D3Gop1JXzaYGnOvBz6hiLsAtSZblLufyoJR7yLyYIjis3KNokT3pVkGMpZ2UPSPxhSv-GYg2S0LEyzTWPrBCIKC6hkw"
    # }
    # response = requests.get(
    #     "https://api-gw-service-nmn.local/apis/fabric-manager/fabric/vni/partitions",
    #     headers=headers,
    # )

    if response.status_code == 200:
        if len(json.loads(response.text)["documentLinks"]) <= 0:
            print(f"Error no VNI partitions defined in slingshot fabric")
            return ret
        for partition in json.loads(response.text)["documentLinks"]:
            # response = json.loads(
            #     requests.get(
            #         f"https://api-gw-service-nmn.local/apis/fabric-manager/{partition}",
            #         headers=headers,
            #     ).text
            # )
            response = json.loads(fabric_client.get(f"{partition}"))
            ret[response["partitionName"]] = response["vniRanges"]
            print(
                f"Read from fabric-manager {response['partitionName']}:{response['vniRanges']}"
            )
    return ret


def find_intersecting_range(list_a, list_b):
    """
    Problem Statement: Find all ranges in list_a that intersect with any range in list_b
    You are given two lists of number ranges. Each range is represented as a
    string "start-end", where start and end are integers (start ≤ end). Your
    task is to find all intersecting ranges between the two lists.

    Input
        *	list_a: A list of number range strings (e.g., ["1025-11775",
            "1025-65535"]).
        *	list_b: Another list of number range strings (e.g., ["11776-22526",
            "22527-33277", "54781-65535"]).

    Output
        *	A list of intersecting number ranges in the format "start-end".
        *	If no intersections exist, return an empty list [].
    Assumptions:
        *   As list_a and list_b are of similar length, both are for VNI ranges
            on the same machine. The range from slingshot fabric might have a few
            additional items remaining after the admin deleted the slum cluster.
    """

    def parse_ranges(ranges):
        """Convert a list of 'start-end' strings into sorted (start, end) tuples."""
        return sorted([tuple(map(int, r.split('-'))) for r in ranges])

    # Convert string ranges to sorted (start, end) tuples
    ranges_a = parse_ranges(list_a)
    ranges_b = parse_ranges(list_b)

    # Results to return
    intersections = []
    # Two pointers for list_a and list_b
    self_compare = list_a == list_b
    i, j = 0, 0

    while i < len(ranges_a) and j < len(ranges_b):
        start_a, end_a = ranges_a[i]
        start_b, end_b = ranges_b[j]
        if i == j and self_compare:
            j += 1
            continue
        # Check if ranges overlap
        if end_a >= start_b and end_b >= start_a:
            if f"{start_a}-{end_a}" not in intersections:
                intersections.append(f"{start_a}-{end_a}")  # Add intersecting range
            if f"{start_b}-{end_b}" not in intersections:
                intersections.append(f"{start_b}-{end_b}")  # Add the other intersecting range

        # Move the pointer for the range that ends first
        if end_a < end_b:
            i += 1
        else:
            j += 1

    return intersections


def do_audit():
    # Get information from slurm.conf in the configmap:slurm-map
    slurm_switch_paramters = {}
    slurm_configs = get_slurm_net_topo_config()
    if len(slurm_configs) <= 0:
        print(
            f"Error reading slurmconfig from kubernetes configmap: slurm-map"
        )
        return
    # We get list of slurm configmaps. One for slurm in non-tenant deployment.
    # And others for each individual tenant.
    for slurm_config_key in slurm_configs:
        slurm_config = slurm_configs[slurm_config_key]
        if slurm_config["SwitchType"] == "switch/hpe_slingshot":
            if "SwitchParameters" not in slurm_config:
                print(
                    f"Error SwitchParameters not in slurmconfig from kubernetes configmap: slurm-map"
                )
                return
            for config_line in slurm_config["SwitchParameters"].split(","):
                key, value = config_line.split("=")
                print(f"\tRead {key} : {value}")
                slurm_switch_paramters[slurm_config_key] = value

    # Get information from the fabric manager
    fabric_mgr_vni_partitions = get_fabricmgr_vni_partitions()
    if len(fabric_mgr_vni_partitions) <= 0:
        print(f"Error reading VNI partitions from slingshot fabric manager")
        return

    # Compare VNI partition in slurm_config and fabric_mgr_vni_partitions
    slurm_range = list(slurm_switch_paramters.values())
    ss_fabric_range = list(fabric_mgr_vni_partitions.values())
    ss_fabric_range = [r[0] for r in ss_fabric_range]
    conflict_vni_ranges = set()
    # Find conflicts within slurm configurations
    conflicts = find_intersecting_range(slurm_range, slurm_range)
    conflict_vni_ranges.update(conflicts)
    # Find conflicts between slurm, fabric manager, and self
    conflicts = find_intersecting_range(slurm_range, ss_fabric_range)
    conflict_vni_ranges.update(conflicts)
    # Find conflicts within fabric manager
    conflicts = find_intersecting_range(ss_fabric_range, ss_fabric_range)
    conflict_vni_ranges.update(conflicts)

    if len(conflict_vni_ranges) > 0:
        print(f"Error VNI range conflict detected among: {conflict_vni_ranges}")
        print(f"Error in VNI range allocated by slurm, or fabric manager")
        conflict_translations = []
        for conflict in conflict_vni_ranges:
            # Find key where value matches
            key = next((k for k, v in slurm_switch_paramters.items() if v == conflict), None)
            if not key:
                key = next((k for k, v in fabric_mgr_vni_partitions.items() if v[0] == conflict), None)
            conflict_translations.append(key)
        print(f"Please check VNI range configured in Slurm configmap(s) and fabric manager: {sorted(conflict_translations)}")
    else:
        print(f"No VNI conflicts detected in slurm configmap and slingshot fabric manager")
    return None

if __name__ == "__main__":
    do_audit()
