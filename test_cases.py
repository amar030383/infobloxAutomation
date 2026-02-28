#!/usr/bin/env python3
"""
Test harness for infoblox_reserve.py workflows.

Scenarios:
1) Requested IP is free -> reserve it.
2) Requested IP is not free -> do not reserve.
3) Ask for next free IP from subnet.

Safety:
- By default, write tests are disabled.
- Set RUN_WRITE_TESTS = True to create reservations.
"""

from datetime import datetime

import infoblox_reserve as ib


# -------------------------
# Test configuration
# -------------------------
BASE_URL = "https://192.168.67.70"
WAPI_VERSION = "v2.7.1"
USERNAME = "admin"
PASSWORD = "Server@123"
NETWORK = "192.168.67.0/24"
NETWORK_VIEW = "default"
VERIFY_SSL = False

# Set True only when you want reservation-creating tests to run.
RUN_WRITE_TESTS = False

# Known-used IP in your environment.
KNOWN_USED_IP = "192.168.67.130"


def _unique_suffix():
    return datetime.now().strftime("%Y%m%d%H%M%S")


def _print_result(name, data):
    print(f"\n{name}")
    print("-" * len(name))
    for key, value in data.items():
        print(f"{key}: {value}")


def test_case_1_free_ip_then_reserve(auth):
    """
    Case 1:
    - Find a currently free IP from subnet.
    - Try check_and_reserve_requested_ip on that IP.
    """
    free_ip = ib.find_next_free_ip(
        base_url=BASE_URL,
        wapi_version=WAPI_VERSION,
        auth=auth,
        network=NETWORK,
        network_view=NETWORK_VIEW,
        verify_ssl=VERIFY_SSL,
    )
    suffix = _unique_suffix()
    fqdn = f"netpeace-free-{suffix}.automation.com"
    mac = f"aa:bb:cc:dd:ee:{int(suffix[-2:]) % 99:02d}"

    if not RUN_WRITE_TESTS:
        return {
            "mode": "DRY_RUN",
            "candidate_free_ip": free_ip,
            "would_reserve_fqdn": fqdn,
            "would_use_mac": mac,
            "note": "Set RUN_WRITE_TESTS=True to execute reservation.",
        }

    result = ib.check_and_reserve_requested_ip(
        base_url=BASE_URL,
        wapi_version=WAPI_VERSION,
        auth=auth,
        network=NETWORK,
        network_view=NETWORK_VIEW,
        requested_ip=free_ip,
        fqdn=fqdn,
        mac=mac,
        verify_ssl=VERIFY_SSL,
    )
    result["fqdn"] = fqdn
    result["mac"] = mac
    return result


def test_case_2_ip_not_free(auth):
    """
    Case 2:
    - Use known used IP.
    - Verify status shows used and no reservation is created.
    """
    result = ib.check_and_reserve_requested_ip(
        base_url=BASE_URL,
        wapi_version=WAPI_VERSION,
        auth=auth,
        network=NETWORK,
        network_view=NETWORK_VIEW,
        requested_ip=KNOWN_USED_IP,
        fqdn="netpeace.automation.com",
        mac="aa:bb:cc:dd:ee:ff",
        verify_ssl=VERIFY_SSL,
    )
    return result


def test_case_3_find_next_free_ip(auth):
    """
    Case 3:
    - Ask Infoblox for next free IP in subnet.
    """
    next_ip = ib.find_next_free_ip(
        base_url=BASE_URL,
        wapi_version=WAPI_VERSION,
        auth=auth,
        network=NETWORK,
        network_view=NETWORK_VIEW,
        verify_ssl=VERIFY_SSL,
    )
    return {"next_free_ip": next_ip}


def main():
    auth = ib.build_auth(USERNAME, PASSWORD)

    case1 = test_case_1_free_ip_then_reserve(auth)
    _print_result("CASE 1: FREE IP THEN RESERVE", case1)

    case2 = test_case_2_ip_not_free(auth)
    _print_result("CASE 2: REQUESTED IP NOT FREE", case2)

    case3 = test_case_3_find_next_free_ip(auth)
    _print_result("CASE 3: FIND NEXT FREE IP", case3)


if __name__ == "__main__":
    main()
