FROM opennetworking/mn-stratum

# Use archived Buster mirrors
RUN sed -i 's|http://deb.debian.org/debian|http://archive.debian.org/debian|g' /etc/apt/sources.list && \
    sed -i 's|http://security.debian.org/debian-security|http://archive.debian.org/debian-security|g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workdir
COPY requirements37.txt /workdir/requirements37.txt
RUN pip3 install --no-cache-dir -r /workdir/requirements37.txt

RUN apt-get update && \
    apt-get install -y \
        openvswitch-switch \
        iproute2 \
        iputils-ping \
        net-tools && \
    apt-get clean


    
    
COPY video/ /workdir/video/
VOLUME /workdir
    
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
    