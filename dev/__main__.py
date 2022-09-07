"""A Python Pulumi program"""
import infra
import logging

logger = logging.getLogger(__name__)

SSH_KEYS = ["daniel@Daniels-MBP"]

HETZNER_LOCATION = "fsn1"

servers = [infra.Server("xardas", "small", "rocky9", "172.21.0.10")]

hetzner_config = {
    "network_config": {
        "private_ip_range": "172.21.0.0/16",
        "subnets": [
            {"subnet_ip_range": "172.21.0.0/24", "name": "subnet1"},
        ],
    },
    "location": HETZNER_LOCATION,
}
scaleway_config = {"network_config": {"private_ip_range": "172.22.0.0/16"}}

# todo: move out ssh keys to the infra class
hetzner_provider = infra.HCloudProvider(SSH_KEYS, hetzner_config)
scaleway_provider = infra.ScalewayProvider(SSH_KEYS, scaleway_config)

providers = {"hetzner": hetzner_provider, "scaleway": scaleway_provider}

infra = infra.Infra(providers)
infra.provision_server(servers[0], "hetzner")
