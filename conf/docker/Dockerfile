FROM ubuntu:22.04

# Zainstaluj podstawowe narzędzia wymagane przez Yocto
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
    gawk wget git diffstat unzip texinfo gcc build-essential chrpath socat \
    cpio python3 python3-pip python3-pexpect xz-utils debianutils iputils-ping \
    python3-git python3-jinja2 libegl1-mesa libsdl1.2-dev xterm \
    file lz4 zstd \
    locales sudo vim curl \
    && rm -rf /var/lib/apt/lists/*

# Ustaw locale, bo Yocto tego wymaga
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Dodaj użytkownika 'builder' żeby nie pracować jako root
RUN useradd -ms /bin/bash builder && echo "builder ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
USER builder
WORKDIR /home/builder

