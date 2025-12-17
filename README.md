# Video Streaming APP

## Setup

Build the necessary docker image, this may take a few minutes

``` bash
docker build -t mn-stratum-python .
```

To emulate a tradional software proxy without intelligent SDN routing:

``` bash

make mininet-simple

make simple-cdn1
make simple-cdn2
make simple-cdn3

make proxy

make simple-origin

make simple-client1

```

Request stuff from client1. Files are in the video directory

For the Content Aware SDN version run:

```bash
make mininet

make cdn1

make cdn2

make cdn3

make origin

make controller grpc_port=50001 name=s1

make controller grpc_port=50002 name=s2

make client1

```

Have Fun!
