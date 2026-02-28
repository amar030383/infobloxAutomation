#!/usr/bin/env python3
import sys

import requests
import urllib3
from requests.auth import HTTPBasicAuth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Update these values before running.
GM_URL = "https://192.168.67.70"
WAPI_VERSION = "v2.7.1"
USERNAME = "admin"
PASSWORD = "Server@123"
NETWORK = "192.168.67.0/24"
NETWORK_VIEW = "default"
REQUESTED_IP = "192.168.67.131"
HOST_FQDN = "netpeace.automation.com"
MAC_ADDRESS = "aa:bb:cc:dd:ee:ff"
VERIFY_SSL = False
# Allowed values: "check_then_reserve" or "next_free_then_reserve"
WORKFLOW_MODE = "check_then_reserve"


def wapi_get(base_url, wapi_version, endpoint, auth, params=None, verify_ssl=False):
    url = f"{base_url}/wapi/{wapi_version}/{endpoint}"
    response = requests.get(url, auth=auth, params=params, verify=verify_ssl, timeout=30)
    response.raise_for_status()
    return response.json()


def wapi_post(base_url, wapi_version, endpoint, auth, payload=None, verify_ssl=False):
    url = f"{base_url}/wapi/{wapi_version}/{endpoint}"
    response = requests.post(url, auth=auth, json=payload or {}, verify=verify_ssl, timeout=30)
    response.raise_for_status()
    if not response.text:
        return {}
    try:
        return response.json()
    except Exception:
        return response.text


def check_ip_status(base_url, wapi_version, auth, network, ip_addr, network_view, verify_ssl=False):
    params = {
        "network": network,
        "ip_address": ip_addr,
        "network_view": network_view,
    }
    result = wapi_get(
        base_url,
        wapi_version,
        "ipv4address",
        auth,
        params=params,
        verify_ssl=verify_ssl,
    )
    if not result:
        return "UNKNOWN"
    return result[0].get("status", "UNKNOWN")


def reserve_fixed_address(base_url, wapi_version, auth, fqdn, ip_addr, mac, network_view, verify_ssl=False):
    payload = {
        "name": fqdn,
        "ipv4addr": ip_addr,
        "mac": mac,
        "network_view": network_view,
    }
    return wapi_post(
        base_url,
        wapi_version,
        "fixedaddress",
        auth,
        payload=payload,
        verify_ssl=verify_ssl,
    )


def get_network_ref(base_url, wapi_version, auth, network, network_view, verify_ssl=False):
    params = {
        "network": network,
        "network_view": network_view,
    }
    result = wapi_get(
        base_url,
        wapi_version,
        "network",
        auth,
        params=params,
        verify_ssl=verify_ssl,
    )
    if not result:
        raise RuntimeError(f"Network not found: {network} (view: {network_view})")
    return result[0]["_ref"]


def get_next_available_ip(base_url, wapi_version, auth, network_ref, count=1, verify_ssl=False):
    endpoint = f"{network_ref}?_function=next_available_ip"
    payload = {"num": count}
    result = wapi_post(
        base_url,
        wapi_version,
        endpoint,
        auth,
        payload=payload,
        verify_ssl=verify_ssl,
    )
    return result.get("ips", [])


def build_auth(username, password):
    return HTTPBasicAuth(username, password)


def check_and_reserve_requested_ip(
    base_url,
    wapi_version,
    auth,
    network,
    network_view,
    requested_ip,
    fqdn,
    mac,
    verify_ssl=False,
):
    status = check_ip_status(
        base_url,
        wapi_version,
        auth,
        network=network,
        ip_addr=requested_ip,
        network_view=network_view,
        verify_ssl=verify_ssl,
    )

    result = {
        "requested_ip": requested_ip,
        "status": status,
        "reserved": False,
        "reservation_ref": None,
    }

    if status == "UNUSED":
        reservation_ref = reserve_fixed_address(
            base_url,
            wapi_version,
            auth,
            fqdn=fqdn,
            ip_addr=requested_ip,
            mac=mac,
            network_view=network_view,
            verify_ssl=verify_ssl,
        )
        result["reserved"] = True
        result["reservation_ref"] = reservation_ref

    return result


def find_next_free_ip(base_url, wapi_version, auth, network, network_view, verify_ssl=False):
    network_ref = get_network_ref(
        base_url,
        wapi_version,
        auth,
        network=network,
        network_view=network_view,
        verify_ssl=verify_ssl,
    )
    next_ips = get_next_available_ip(
        base_url,
        wapi_version,
        auth,
        network_ref=network_ref,
        count=1,
        verify_ssl=verify_ssl,
    )
    if not next_ips:
        raise RuntimeError(f"No available IP returned for network {network}")
    return next_ips[0]


def find_next_free_ip_and_reserve(
    base_url,
    wapi_version,
    auth,
    network,
    network_view,
    fqdn,
    mac,
    verify_ssl=False,
):
    next_ip = find_next_free_ip(
        base_url,
        wapi_version,
        auth,
        network=network,
        network_view=network_view,
        verify_ssl=verify_ssl,
    )
    reservation_ref = reserve_fixed_address(
        base_url,
        wapi_version,
        auth,
        fqdn=fqdn,
        ip_addr=next_ip,
        mac=mac,
        network_view=network_view,
        verify_ssl=verify_ssl,
    )
    return {
        "next_ip": next_ip,
        "reserved": True,
        "reservation_ref": reservation_ref,
    }


def main():
    auth = build_auth(USERNAME, PASSWORD)

    if WORKFLOW_MODE == "check_then_reserve":
        print("[Section 1] Check requested IP and reserve if free")
        try:
            section1 = check_and_reserve_requested_ip(
                GM_URL,
                WAPI_VERSION,
                auth,
                network=NETWORK,
                network_view=NETWORK_VIEW,
                requested_ip=REQUESTED_IP,
                fqdn=HOST_FQDN,
                mac=MAC_ADDRESS,
                verify_ssl=VERIFY_SSL,
            )
            print(f"    Requested IP: {section1['requested_ip']}")
            print(f"    Status: {section1['status']}")
            if section1["reserved"]:
                print(f"    Reservation created: {section1['reservation_ref']}")
            else:
                print("    IP is not free; skipped reservation.")
        except Exception as exc:
            print(f"    Section 1 failed: {exc}")
            if isinstance(exc, requests.HTTPError) and exc.response is not None:
                print(f"    Response: {exc.response.text}")
            sys.exit(1)

    elif WORKFLOW_MODE == "next_free_then_reserve":
        print("[Section 2] Find next free IP and reserve")
        try:
            section2 = find_next_free_ip_and_reserve(
                GM_URL,
                WAPI_VERSION,
                auth,
                network=NETWORK,
                network_view=NETWORK_VIEW,
                fqdn=HOST_FQDN,
                mac=MAC_ADDRESS,
                verify_ssl=VERIFY_SSL,
            )
            print(f"    Next free IP reserved: {section2['next_ip']}")
            print(f"    Reservation created: {section2['reservation_ref']}")
        except Exception as exc:
            print(f"    Section 2 failed: {exc}")
            if isinstance(exc, requests.HTTPError) and exc.response is not None:
                print(f"    Response: {exc.response.text}")
            sys.exit(1)

    else:
        print(
            f"Invalid WORKFLOW_MODE: {WORKFLOW_MODE}. "
            'Use "check_then_reserve" or "next_free_then_reserve".'
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
