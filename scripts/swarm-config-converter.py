#!/usr/bin/env python3
"""
Convert docker-compose config to Swarm-compatible format.
Removes unsupported options and fixes type issues.
"""
import sys

import yaml


class IntegerDumper(yaml.SafeDumper):
    """Custom dumper that keeps integers unquoted."""

    pass


def represent_int(dumper, data):
    return yaml.ScalarNode("tag:yaml.org,2002:int", str(data))


IntegerDumper.add_representer(int, represent_int)


def convert_to_swarm(data):
    """Remove Swarm-unsupported options and fix types."""

    # Remove top-level 'name' (not allowed in Swarm)
    if "name" in data:
        del data["name"]

    # Convert networks to overlay driver (required for Swarm)
    for net_name, net_config in data.get("networks", {}).items():
        if net_config is None:
            data["networks"][net_name] = {"driver": "overlay"}
        elif isinstance(net_config, dict):
            net_config["driver"] = "overlay"
            # Remove 'name' from networks
            if "name" in net_config:
                del net_config["name"]

    # Keys not supported in Swarm mode
    unsupported_service_keys = [
        "depends_on",
        "memswap_limit",
        "mem_swappiness",
        "restart",  # Use deploy.restart_policy instead
        "container_name",  # Swarm generates names
    ]

    for svc_name, svc in data.get("services", {}).items():
        # Remove unsupported keys
        for key in unsupported_service_keys:
            if key in svc:
                del svc[key]

        # Add image name if build is specified (Swarm doesn't support build)
        if "build" in svc and "image" not in svc:
            svc["image"] = f"convertica-{svc_name}:latest"
        # Remove build section
        if "build" in svc:
            del svc["build"]

        # Fix cpus to be string (Swarm requirement)
        deploy = svc.get("deploy", {})
        resources = deploy.get("resources", {})
        for res_type in ["limits", "reservations"]:
            if res_type in resources:
                if "cpus" in resources[res_type]:
                    resources[res_type]["cpus"] = str(resources[res_type]["cpus"])

        # Ensure ports published are integers
        if "ports" in svc:
            for port in svc["ports"]:
                if isinstance(port, dict) and "published" in port:
                    if isinstance(port["published"], str):
                        port["published"] = int(port["published"])

    return data


def main():
    data = yaml.safe_load(sys.stdin)
    converted = convert_to_swarm(data)
    print(
        yaml.dump(
            converted, Dumper=IntegerDumper, default_flow_style=False, sort_keys=False
        )
    )


if __name__ == "__main__":
    main()
