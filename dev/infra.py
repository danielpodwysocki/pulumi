""" Those classes provide a set of abstractions to create and manage
infrastracture across cloud providers.

The idea is to allow the user to not have to worry about the underlying
provider and quickly migrate to a different one if needed.

For a provider to be functional, they must support:
- VPS (Server class)
- Private networks and subnets
- Security groups/Firewall rules
"""

from abc import ABC
import pulumi_hcloud as hcloud
import pulumiverse_scaleway as scaleway
import logging

logger = logging.getLogger(__name__)


class SecurityGroup:
    """A uniform way to define security groups across providers"""

    def __init__(self, name, rules):
        self.name = name
        self.rules = rules


class Provider(ABC):
    """A class to define a cloud-agnostic interface for all my infra
    It allows the Infra class to have a reliable way of creating and managing
    infrastracture across cloud providers.
    :param provider_config: a dictionary containing the configuration for the
    specific provider
    It can contain the following keys:
    - network_config: a dictionary containing the configuration for the
    private network. It can contain the following keys:
        - private_ip_range (str): the main IP range for the network
        - subnets: a list of dictionaries containing the configuration for the
        subnets. Each dictionary can contain the following keys:
            - subnet_ip_range (str): the IP range for the subnet
            - name (str): the name of the subnet
    """

    def __init__(self, ssh_keys=None, provider_config=None) -> None:
        logger.info("Initializing provider, config: %s", provider_config)
        self.ssh_keys = ssh_keys
        self.provider_config = provider_config
        self.set_sizes()
        self.set_images()
        # if self.network_config_is_valid(self.provider_config["network_config"]):
        self.network = self.provision_private_network()
        self.subnets = self.provision_private_subnets()
        self.servers = []

    # @abstractmethod
    def set_sizes(self):
        """Set the sizes for the different types of servers
        Each provider class is expected to define the values for those
        keys on its own.
        """
        self.sizes = {
            "small": "instance_type_small",
            "medium": "instance_type_medium",
            "large": "instance_type_large",
            "xlarge": "instance_type_xlarge",
        }

    def set_images(self):
        """Set the images for different distros
        Each provider class is expected to define the values for those
        keys on its own.
        """
        self.images = {
            "ubuntu20": "ubuntu_20_04",
            "debian11": "debian_11",
            "rocky9": "rocky_9",
        }

    def provision_private_network(self):
        pass

    def provision_private_subnets(self):
        pass

    def provision_server(self, size, image):
        """Provision a server
        :param size: the size of the server. Should be one of the keys in the
        sizes dictionary
        :type size: str
        :param image: the image to use for the server

        """
        pass

    def provision_security_group(self, security_group):
        """Provision a security group using the provider's API
        :param security_group: a SecurityGroup object
        """
        pass

    def network_config_is_valid(self, network_config):
        """Check if the network configuration is valid
        This can differ from provider to provider. For example, Hetzner supports
        subnets within your network, while Scaleway does not.
        By default, we assume that subnets are supported.
        :param network_config: a dictionary containing the network configuration
        :type network_config: dict
        :todo: implement this
        """
        return True
        # if all(k in network_config for k in ("private_ip_range", "subnets")) and type(
        #    network_config.get("subnets", None) == list )
        # ):
        #    return True
        # return False

    def server_object_is_valid(self, server):
        """Check if the server object is valid
        :param server: a Server object
        :type server: Server
        :todo: check if the IP address is valid
        """
        if server.image in self.images.keys() and server.size in self.sizes.keys():
            return True
        return False


class HCloudProvider(Provider):
    """A class to define a provider for Hetzner Cloud
    :param provider_config: a dictionary containing the configuration for HCloud
    It can contain the following keys:
    - network_config: a dictionary containing the configuration for the
    private network. It can contain the following keys:
        - private_ip_range (str): the main IP range for the network
        - subnets: a list of dictionaries containing the configuration for the
        subnets. Each dictionary can contain the following keys:
            - subnet_ip_range (str): the IP range for the subnet
            - name (str): the name of the subnet
    - location (str) - the location to use for the servers, for example "fsn1"
    :type provider_config: dict
    """

    def set_images(self):
        self.images = {
            "ubuntu22": "ubuntu-20.04",
            "debian11": "debian-11",
            "rocky9": "rocky-9",
            "centos7": "centos-7",
        }

    def set_sizes(self):
        self.sizes = {
            "small": "cx11",
            "medium": "cx21",
            "large": "cx31",
            "xlarge": "cx41",
        }

    def provision_private_network(self):
        logger.info("Provisioning private network")
        return hcloud.Network(
            "network",
            ip_range=self.provider_config["network_config"]["private_ip_range"],
        )

    def provision_private_subnets(self):
        ret = []
        for subnet in self.provider_config["network_config"]["subnets"]:
            ret.append(
                hcloud.NetworkSubnet(
                    subnet["name"],
                    network_id=self.network.id,
                    ip_range=subnet["subnet_ip_range"],
                    network_zone="eu-central",
                    type="cloud",
                )
            )
        return ret

    def provision_server(self, server):
        """Provision a server
        :param server: a Server object
        :type server: Server
        """
        if self.server_object_is_valid(server):
            server_instance = hcloud.Server(
                server.name,
                server_type=self.sizes[server.size],
                image=self.images[server.image],
                ssh_keys=self.ssh_keys,
                networks=[
                    hcloud.ServerNetworkArgs(
                        network_id=self.network.id, ip=server.ip_address
                    )
                ],
                location=self.provider_config["location"],
            )
            self.servers.append(server_instance)
        else:
            raise Exception("Invalid server object")


class ScalewayProvider(Provider):
    """A class to define a provider for Scaleway
    :param provider_config: a dictionary containing the configuration for Scaleway
    It can contain the following keys:
    :type provider_config: dict
    """

    def set_images(self):
        # curl -s 'https://api-marketplace.scaleway.com/images?page=1&per_page=100' | sed 's/par1/fr-par-1/g; s/ams1/nl-ams-1/g' | jq '.images | map({"key": .label | gsub("_";"-"), "value": .versions[0].local_images}) | from_entries' | grep -i rock
        self.images = {
            "ubuntu22": "ubuntu_jammy",
            "debian11": "debian_bullseye",
            "rocky9": "rockylinux_9",
            "centos7": "centos_7.9",
        }

    def set_sizes(self):
        self.sizes = {
            "small": "DEV1-S",
            "medium": "DEV1-M",
            "large": "DEV1-L",
            "xlarge": "DEV1-XL",
        }

    def provision_server(self, server):
        if self.server_object_is_valid(server):
            ip = scaleway.InstanceIp(f"public_ip_{server.name}")
            server_instance = scaleway.InstanceServer(
                server.name,
                image=self.images[server.image],
                type=self.sizes[server.size],
                ip_id=ip.id,
            )

            self.servers.append(server)
        else:
            raise Exception("Invalid server object")


class Infra:
    """A class representing all infrastracture
    for a given environment.
    :param providers: A dict of providers to use, each implementing the Provider interface
    The keys should be the provider name, and the values should be Provider objects
    :type providers: list
    """

    def __init__(self, providers) -> None:
        self.providers = providers

    def provision_server(self, server, provider_name):
        """Provision a server on a given provider
        :param server: a Server object
        :type server: Server
        :param provider_name: the name of the provider to use
        :type provider_name: str
        """
        self.providers[provider_name].provision_server(server)

    def deploy(self):
        """Apply Ansible to all servers"""
        pass


class Server:
    """A class representing a server.
    It can be passed to a provider to provision it. The configuration doesn't
    need to be changed for each provider - it is universal.
    :param name: the name of the server
    :type name: str
    :param size: the size of the server. Should be one of the items in the sizes
    list
    :type size: str
    :param image: the image to use for the server. Should be one of the items in
    the images list
    :type image: str
    :param ip_address: the IP address to assign to the server
    :type ip_address: str
    """

    def __init__(
        self, name: str, size: str, image: str, ip_address: str = None
    ) -> None:
        self.name = name
        self.size = size
        self.image = image
        self.ip_address = ip_address
        pass

    def deploy(self):
        """Apply Ansible to the host"""
        pass
