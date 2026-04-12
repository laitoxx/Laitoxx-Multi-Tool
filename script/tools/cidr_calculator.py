"""
CIDR Calculator — IPv4 / IPv6 network analysis.

Output
------
  - Network address, broadcast, netmask, wildcard
  - Prefix length, host count
  - First / last usable host
  - Host address check (is a given IP in range?)
  - Subnetting: split into N equal subnets

GUI  → cidr_calculator_tool({"cidr": "192.168.1.0/24", "subnet_count": 4})
       cidr_calculator_tool({"cidr": "192.168.1.0/24", "check_ip": "192.168.1.50"})
CLI  → cidr_calculator_tool()
"""

import ipaddress

from ..shared_utils import Color


def _row(label: str, value, width: int = 22):
    print(f"{Color.DARK_GRAY}  - {Color.LIGHT_RED}{label:<{width}}{Color.WHITE}{value}")


def cidr_calculator_tool(data=None):
    if data:
        cidr_str     = data.get("cidr", "").strip()
        check_ip     = data.get("check_ip", "").strip()
        subnet_count = int(data.get("subnet_count", 0))
    else:
        print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
              f" CIDR Calculator\n")
        cidr_str = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
            f" Enter CIDR (e.g. 192.168.1.0/24): {Color.RESET}"
        ).strip()
        check_ip = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
            f" Check if IP is in range (leave empty to skip): {Color.RESET}"
        ).strip()
        try:
            subnet_count = int(input(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
                f" Split into N subnets (0 to skip): {Color.RESET}"
            ).strip() or 0)
        except ValueError:
            subnet_count = 0

    if not cidr_str:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No CIDR provided.")
        return

    try:
        net = ipaddress.ip_network(cidr_str, strict=False)
    except ValueError as e:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}"
              f" Invalid CIDR notation: {e}")
        return

    is_v6   = isinstance(net, ipaddress.IPv6Network)
    version = 6 if is_v6 else 4

    print(f"\n{Color.DARK_RED}┌─[ {Color.LIGHT_RED}Network Info · IPv{version} {Color.DARK_RED}]" + "─" * 18)
    _row("CIDR",             str(net))
    _row("Network address",  str(net.network_address))
    _row("Prefix length",    f"/{net.prefixlen}")

    if not is_v6:
        _row("Subnet mask",      str(net.netmask))
        _row("Wildcard mask",    str(net.hostmask))
        _row("Broadcast",        str(net.broadcast_address))

    num_hosts = net.num_addresses - (2 if not is_v6 and net.prefixlen < 31 else 0)
    _row("Total addresses",  f"{net.num_addresses:,}")
    _row("Usable hosts",     f"{max(0, num_hosts):,}")

    if not is_v6 and net.prefixlen < 31:
        hosts = list(net.hosts())
        if hosts:
            _row("First usable",    str(hosts[0]))
            _row("Last usable",     str(hosts[-1]))
    elif is_v6:
        hosts_gen = net.hosts()
        try:
            first = next(hosts_gen)
            _row("First host",      str(first))
        except StopIteration:
            pass

    if check_ip:
        print(f"\n{Color.DARK_RED}├─[ {Color.LIGHT_RED}IP Check {Color.DARK_RED}]" + "─" * 29)
        try:
            ip_obj = ipaddress.ip_address(check_ip)
            if ip_obj in net:
                print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]"
                      f"{Color.LIGHT_GREEN} {check_ip} is IN {net}")
            else:
                print(f"{Color.DARK_GRAY}  [{Color.RED}✖{Color.DARK_GRAY}]"
                      f"{Color.RED} {check_ip} is NOT in {net}")
        except ValueError as e:
            print(f"{Color.DARK_GRAY}  [{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}"
                  f" Invalid IP: {e}")

    if subnet_count and subnet_count > 1:
        print(f"\n{Color.DARK_RED}├─[ {Color.LIGHT_RED}Subnets ({subnet_count}) {Color.DARK_RED}]" + "─" * 24)

        bits_needed = (subnet_count - 1).bit_length()
        new_prefix = net.prefixlen + bits_needed

        max_prefix = 128 if is_v6 else 32
        if new_prefix > max_prefix:
            print(f"{Color.DARK_GRAY}  [{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}"
                  f" Cannot split /{net.prefixlen} into {subnet_count} subnets"
                  f" (would require /{new_prefix}).")
        else:
            subnets = list(net.subnets(new_prefix=new_prefix))
            display_limit = min(len(subnets), 16)
            per_subnet = subnets[0].num_addresses

            print(f"{Color.DARK_GRAY}  New prefix: {Color.WHITE}/{new_prefix}"
                  f"  {Color.DARK_GRAY}Addresses/subnet: {Color.WHITE}{per_subnet:,}"
                  f"  {Color.DARK_GRAY}Total subnets: {Color.WHITE}{len(subnets)}")
            print(f"{Color.DARK_RED}  {'─'*40}")

            for i, sn in enumerate(subnets[:display_limit]):
                if not is_v6 and sn.prefixlen < 31:
                    hs = list(sn.hosts())
                    detail = (f"  {Color.DARK_GRAY}hosts: {Color.WHITE}{hs[0]} – {hs[-1]}"
                              if hs else "")
                else:
                    detail = ""
                print(f"{Color.DARK_GRAY}  [{Color.LIGHT_RED}{i+1:>3}{Color.DARK_GRAY}]"
                      f"  {Color.WHITE}{str(sn):<22}{detail}")

            if len(subnets) > display_limit:
                print(f"{Color.DARK_GRAY}  ... ({len(subnets) - display_limit} more subnets)")

    print(f"\n{Color.DARK_RED}└" + "─" * 45)
    print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN}"
          f" CIDR calculation complete.")
