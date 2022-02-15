FROM debian:stable

ENV HOME=/root

# Update and upgrade system
RUN \
  apt-get update && \
  apt-get -y upgrade

## PyUci #########################################################################
# Install packages needed for PyUci dependencies
RUN \
  apt-get update && \
  apt-get -y install --no-install-recommends \
    lua5.1 liblua5.1-0-dev libjson-c-dev ca-certificates \
    git cmake make pkg-config gcc

# Compile libubox
RUN \
  git clone git://git.openwrt.org/project/libubox.git ~/libubox && \
  cd ~/libubox && \
  cmake CMakeLists.txt && \
  make install && \
  cd .. && \
  rm -rf libubox

# Compile uci
RUN \
  git clone git://git.openwrt.org/project/uci.git ~/uci && \
  cd ~/uci && \
  cmake cmake CMakeLists.txt && \
  make install && \
  cd .. && \
  rm -rf uci

# Install packages needed for PyUci
RUN \
  apt-get update && \
  apt-get -y install --no-install-recommends \
    python3-dev python3-setuptools python3-pip python3-pytest \
    python3-pytest-cov lcov \
    && \
  apt-get clean

# Install pyuci
RUN \
  git clone https://gitlab.nic.cz/turris/pyuci.git ~/pyuci && \
  cd ~/pyuci && \
  python3 setup.py install && \
  cd .. && \
  rm -rf pyuci

##################################################################################
# Dependencies
RUN \
  apt-get update && \
  apt-get -y install --no-install-recommends \
    python3-pip

RUN \
  pip3 install \
    black \
    isort \
    pylint \
    mypy

COPY ./requirements.txt ./
RUN \
  pip3 install -r requirements.txt && \
  rm -f requirements.txt


RUN apt-get clean

CMD [ "bash" ]
