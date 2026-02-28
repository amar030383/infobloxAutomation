# Infoblox Reservation Script (Modular)

This project uses `infoblox_reserve.py` to work with Infoblox WAPI in two modular sections:

1. `check_ip_status` + `reserve_fixed_address` (reserve a specific requested IP if free)
2. find next free IP in subnet + `reserve_fixed_address`

The script is written so functions are easy to import into other Python files.

## Configuration in Script

Update values at the top of `infoblox_reserve.py`:

- `GM_URL`
- `WAPI_VERSION`
- `USERNAME`
- `PASSWORD`
- `NETWORK`
- `NETWORK_VIEW`
- `REQUESTED_IP`
- `HOST_FQDN`
- `MAC_ADDRESS`
- `VERIFY_SSL`
- `WORKFLOW_MODE` (`check_then_reserve` or `next_free_then_reserve`)

## Install Dependency

```powershell
py -m pip install requests
```

## Run as Script

```powershell
py .\infoblox_reserve.py
```

## Import-Friendly Functions

Core helpers:

- `build_auth(username, password)`
- `check_ip_status(...)`
- `reserve_fixed_address(...)`
- `find_next_free_ip(...)`

Workflow wrappers:

- `check_and_reserve_requested_ip(...)`
- `find_next_free_ip_and_reserve(...)`

## Test Results (Live on 192.168.67.70)

These tests were executed against:

- Grid Manager: `https://192.168.67.70`
- WAPI: `v2.7.1`
- Network: `192.168.67.0/24`
- Network view: `default`

### 1) What happens when requested IP is free and then reserved

Test call:

```python
import infoblox_reserve as m
auth = m.build_auth("admin", "Server@123")
res = m.check_and_reserve_requested_ip(
    base_url="https://192.168.67.70",
    wapi_version="v2.7.1",
    auth=auth,
    network="192.168.67.0/24",
    network_view="default",
    requested_ip="192.168.67.2",
    fqdn="netpeace-free-test.automation.com",
    mac="aa:bb:cc:dd:ee:11",
    verify_ssl=False,
)
print(res)
```

Observed result:

- `status = UNUSED`
- `reserved = true`
- reservation created at `192.168.67.2`

### 2) What happens when requested IP is not free

Test call:

```python
import infoblox_reserve as m
auth = m.build_auth("admin", "Server@123")
res = m.check_and_reserve_requested_ip(
    base_url="https://192.168.67.70",
    wapi_version="v2.7.1",
    auth=auth,
    network="192.168.67.0/24",
    network_view="default",
    requested_ip="192.168.67.130",
    fqdn="netpeace.automation.com",
    mac="aa:bb:cc:dd:ee:ff",
    verify_ssl=False,
)
print(res)
```

Observed result:

- `status = USED`
- `reserved = false`
- no new reservation created

### 3) What happens when user asks for a free IP from subnet

Test call:

```python
import infoblox_reserve as m
auth = m.build_auth("admin", "Server@123")
ip = m.find_next_free_ip(
    base_url="https://192.168.67.70",
    wapi_version="v2.7.1",
    auth=auth,
    network="192.168.67.0/24",
    network_view="default",
    verify_ssl=False,
)
print(ip)
```

Observed result:

- next free IP returned: `192.168.67.1`

## Optional: Reserve Next Free IP Directly

```python
import infoblox_reserve as m
auth = m.build_auth("admin", "Server@123")
res = m.find_next_free_ip_and_reserve(
    base_url="https://192.168.67.70",
    wapi_version="v2.7.1",
    auth=auth,
    network="192.168.67.0/24",
    network_view="default",
    fqdn="netpeace-nextfree.automation.com",
    mac="aa:bb:cc:dd:ee:22",
    verify_ssl=False,
)
print(res)
```

## Notes

- Infoblox does not allow same MAC in two fixed addresses in the same subnet.
- If reusing MACs, expect `Client.Ibap.Data.Conflict`.
- For production, use a dedicated API user instead of `admin`.
