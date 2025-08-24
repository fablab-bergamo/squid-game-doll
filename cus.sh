#!/bin/bash

set -ex

# cuSPARSELt license: https://docs.nvidia.com/cuda/cusparselt/license.html

CUSPARSELT_URL="https://developer.download.nvidia.com/compute/cusparselt/redist/libcusparse_lt/linux-aarch64"
CUSPARSELT_VERSION="0.7.1.0"
CUSPARSELT_NAME="libcusparse_lt-linux-aarch64-${CUSPARSELT_VERSION}-archive"

# Create and enter temp working directory
mkdir -p tmp_cusparselt && cd tmp_cusparselt

# Download the archive
curl --retry 3 -OLs "${CUSPARSELT_URL}/${CUSPARSELT_NAME}.tar.xz"

# Extract the archive
tar xf "${CUSPARSELT_NAME}.tar.xz"

# Install headers and libraries
cp -a "${CUSPARSELT_NAME}/include/"* /usr/local/cuda/include/
cp -a "${CUSPARSELT_NAME}/lib/"* /usr/local/cuda/lib64/

# Clean up
cd ..
rm -rf tmp_cusparselt

# Update linker cache
ldconfig