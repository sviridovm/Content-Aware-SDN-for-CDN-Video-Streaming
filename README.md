# Video Streaming APP

First Build the necessary docker image
docker build -t mn-stratum-python .

For the base version run:


```bash

make mininet-simple

make cdn1
python3 traffic/simple_cdn.py

make cdn2
python3 traffic/simple_cdn.py

make cdn3
python3 traffic/simple_cdn.py

make proxy
python3 traffic/proxy.py

make origin
python3 traffic/origin_server.py

make client1
python3 traffic/simple_client.py

```

Request stuff from client1. Files are in the video directory


For the Content Aware SDN version run:


```bash
make mininet

make cdn1
python3 traffic/icn_cdn.py

make cdn2
python3 traffic/icn_cdn.py

make cdn3
python3 traffic/icn_cdn.py

make origin
python3 traffic/icn_origin.py

make client1
python3 traffic/icn_client.py

```
