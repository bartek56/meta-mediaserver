FROM ubuntu:26.04

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    gawk wget git diffstat unzip texinfo gcc build-essential chrpath socat \
    cpio python3 python3-pip python3-pexpect xz-utils debianutils iputils-ping \
    python3-git python3-jinja2 libegl1 libsdl2-dev xterm \
    file lz4 zstd \
    locales sudo vim curl \
    && rm -rf /var/lib/apt/lists/*

RUN locale-gen en_US.UTF-8

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

RUN if id ubuntu >/dev/null 2>&1; then \
        usermod --login builder ubuntu && \
        groupmod --new-name builder ubuntu && \
        usermod --home /home/builder --move-home builder; \
    else \
        groupadd --gid 1000 builder && \
        useradd --uid 1000 --gid 1000 -ms /bin/bash builder; \
    fi && \
    echo "builder ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

COPY entrypoint.sh /usr/local/bin/yocto-entrypoint
RUN chmod 0755 /usr/local/bin/yocto-entrypoint

USER builder

WORKDIR /home/builder
ENTRYPOINT ["/usr/local/bin/yocto-entrypoint"]
