############################################################################
##
##     This file is part of Purdue CS 536.
##
##     Purdue CS 536 is free software: you can redistribute it and/or modify
##     it under the terms of the GNU General Public License as published by
##     the Free Software Foundation, either version 3 of the License, or
##     (at your option) any later version.
##
##     Purdue CS 536 is distributed in the hope that it will be useful,
##     but WITHOUT ANY WARRANTY; without even the implied warranty of
##     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##     GNU General Public License for more details.
##
##     You should have received a copy of the GNU General Public License
##     along with Purdue CS 536. If not, see <https://www.gnu.org/licenses/>.
##
#############################################################################



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




# run mininet locally now
# 	venv37/bin/python topo/topo.py





# Usage: make controller name=bridge grpc_port=50001 topo=linear,2,2
# controller:
# 	make .controller-$(name)

# Usage: make controller-logs name=bridge grpc_port=50001
controller-logs:
	make .controller-$(name)-logs

onos-start:
	ONOS_APPS=gui,proxyarp,drivers.bmv2,lldpprovider,hostprovider \
	$(DOCKER_SCRIPTS)/onos
onos-cli:
	$(DOCKER_SCRIPTS)/onos-cli

onos-netcfg:
	$(DOCKER_SCRIPTS)/onos-netcfg netcfg/netcfg.json

onos-build-app:
	cd $(APP_NAME)/ && $(DOCKER_SCRIPTS)/maven clean package

onos-reload-app: 
	$(DOCKER_SCRIPTS)/onos-app reinstall! $(APP_NAME)/target/$(APP_NAME)-1.0-SNAPSHOT.oar

onos-clean-app:
	sudo rm -rf $(APP_NAME)/target

netcfg:
	$(DOCKER_SCRIPTS)/onos-netcfg netcfg/netcfg.json


mininet-onos:
	$(DOCKER_SCRIPTS)/mn-stratum


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
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec h0 \
		python3 traffic/origin_server.py

cdn1:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec h1 && \
		python3 traffic/cdn2.py --id h1 --port 8000

cdn2:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec h2 && \
		python3  traffic/cdn2.py --id h2 --port 8000

cdn3:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec h3 && \
		python3  traffic/cdn2.py --id h3 --port 8000

proxy:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec proxy && \
		python3  traffic/proxy.py --config topo/topo.json 


client1:
	$(DOCKER_SCRIPTS)/utils/mn-stratum/exec h4 && \
		python3  traffic/client2.py 


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

