export PROJECT_DIR = $(shell pwd)
export DOCKER_SCRIPTS = $(shell pwd)/scripts

export P4_PROGRAM_DIRNAME ?=
export P4_PROGRAM_NAME ?=
export P4RT_PROGRAM_DIRNAME ?=
export P4RT_PROGRAM_NAME ?=


export name ?=
export grpc_port ?= 

APP_NAME = cdnapp

export PYTHON = python3



.PHONY: help mininet enable-vlan disable-vlan controller controller-logs bridge switch host clean

help: 
	@echo "Example usage ...\n"

	@echo "- Clean All: make clean\n"

# Usage: make mininet topo=linear,2,2
mininet:
	$(DOCKER_SCRIPTS)/mn-stratum.run-script /workdir/venv/bin/python3  topo/topo.py
	make clean

mininet-simple:
# 	$(DOCKER_SCRIPTS)/mn-stratum
	$(DOCKER_SCRIPTS)/mn-stratum.run-script /workdir/venv/bin/python3  topo/simple_topo.py
	make clean



# Usage: make controller name=bridge grpc_port=50001 topo=linear,2,2
# controller:
# 	make .controller-$(name)

# Usage: make controller-logs name=bridge grpc_port=50001
controller-logs:
	make .controller-$(name)-logs

# Usage: make host name=h1s1
host:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec $(name)


.mininet-install-prereqs:
	docker exec -it mn-stratum bash -c \
		"echo 'deb http://archive.debian.org/debian buster main contrib non-free' >> /etc/apt/sources.list && \
		echo 'deb http://archive.debian.org/debian-security buster/updates main contrib non-free' >> /etc/apt/sources.list && \
		apt-get --allow-insecure-repositories --allow-unauthenticated update ; \
		apt-get -y --allow-unauthenticated install vlan"



origin:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script origin "python3 traffic/icn_origin.py"

simple-origin:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script origin "python3 traffic/origin_server.py"
simple-infra:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script-d cdn1 "python3 traffic/simple_cdn.py"
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script-d cdn2 "python3 traffic/simple_cdn.py"
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script-d cdn3 "python3 traffic/simple_cdn.py"
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script-d origin "python3 traffic/origin_server.py"
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script-d proxy "python3 traffic/proxy.py"
sdn-infra:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-d-script cdn1 "python3 traffic/icn_cdn.py --id cdn1"
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-d-script cdn2 "python3 traffic/icn_cdn.py --id cdn2"
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-d-script cdn3 "python3 traffic/icn_cdn.py --id cdn3"
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-d-script origin "python3 traffic/icn_origin.py"


simple-client1:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script client1 "python3 traffic/simple_client.py"


simple-cdn1:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script cdn1 "python3 traffic/simple_cdn.py"

simple-cdn2:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script cdn2 "python3 traffic/simple_cdn.py"

simple-cdn3:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script cdn3 "python3 traffic/simple_cdn.py"

proxy:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script proxy "python3 traffic/proxy.py"

simple-origin:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script origin "python3 traffic/origin_server.py"

cdn1:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script cdn1 "python3 traffic/icn_cdn.py --id cdn1"
# 		python3 traffic/cdn2.py --id h1 --port 8000

cdn2:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script cdn2 "python3 traffic/icn_cdn.py --id cdn2"

cdn3:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script cdn3 "python3 traffic/icn_cdn.py --id cdn3"

client1:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec-script client1 "python3 traffic/icn_client.py --id client1"


controllers:
	make controller grpc_port=50001 name=s1
	make controller grpc_port=50002 name=s2

controller:
	P4_PROGRAM_NAME=switch \
	P4RT_PROGRAM_NAME=switch \
	make .p4rt-script


.p4rt-script: .p4-build
	mkdir -p logs/$(P4_PROGRAM_DIRNAME)
	P4RUNTIME_SH_DOCKER_NAME=p4runtime-sh-$(grpc_port) \
	$(DOCKER_SCRIPTS)/p4runtime-sh.run-script \
		"p4rt-src/switch.py --grpc-port=$(grpc_port) --topo-config=topo/topo.json --name=$(name)"


clean: .p4rt-clean .p4-clean

.p4rt-clean:
	rm -rf logs

.p4-clean:
	rm -rf cfg

.p4-build:
	mkdir -p cfg/$(P4_PROGRAM_DIRNAME)
	$(DOCKER_SCRIPTS)/p4c p4c-bm2-ss --arch v1model \
		-o cfg/$(P4_PROGRAM_DIRNAME)/$(P4_PROGRAM_NAME)-$(grpc_port).json \
		-DTARGET_BMV2 -DCPU_PORT=255 \
		--p4runtime-files cfg/$(P4_PROGRAM_DIRNAME)/$(P4_PROGRAM_NAME)-$(grpc_port)-p4info.txt \
		p4-src/$(P4_PROGRAM_NAME).p4



host:
	$(SCRIPTS)/utils/mn-stratum/exec $(name)

