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
  git clone https://git.openwrt.org/project/libubox.git ~/libubox && \
  cd ~/libubox && \
  cmake CMakeLists.txt && \
  make install && \
  cd .. && \
  rm -rf libubox

# Compile uci
RUN \
  git clone https://git.openwrt.org/project/uci.git ~/uci && \
  cd ~/uci && \
  cmake CMakeLists.txt && \
  make install && \
  cd .. && \
  rm -rf uci

# Install packages needed for PyUci
RUN \
  apt-get update && \
  apt-get -y install --no-install-recommends \
    python3-dev python3-venv python3-setuptools python3-pip python3-pytest \
    python3-pytest-cov lcov \
    && \
  apt-get clean

# Install pyuci
RUN \
  git clone https://gitlab.nic.cz/turris/pyuci.git ~/pyuci && \
  cd ~/pyuci && \
  python3 -m venv venv && \
  . venv/bin/activate && \
  python3 -m pip install . && \
  cd .. && \
  rm -rf pyuci

##################################################################################
# Dependencies
RUN \
  apt-get update && \
  apt-get -y install --no-install-recommends \
    python3-pip

# Install venv package
RUN apt-get update && apt-get install -y python3-venv

# Create and activate a virtual environment
RUN python3 -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip && \
    pip install black isort pylint mypy setuptools

# Ensure the virtual environment is used by default
ENV PATH="/opt/venv/bin:$PATH"

COPY ./requirements.txt ./
RUN \
  pip3 install -r requirements.txt && \
  rm -f requirements.txt


RUN apt-get clean

CMD [ "bash" ]
