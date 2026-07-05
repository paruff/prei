# syntax=docker/dockerfile:1.7
#
# Devcontainer base image with pre-flight fixes for devcontainer features.
#
# The base image (mcr.microsoft.com/devcontainers/python) bundles a Yarn APT
# repository whose GPG key expired. When devcontainer features (e.g. docker-in-docker)
# run `apt-get update`, the stale Yarn repo causes a fatal GPG error that prevents
# the feature from installing.
#
# This Dockerfile strips the Yarn repo before features are applied.

ARG PYTHON_VERSION=3.12
FROM mcr.microsoft.com/devcontainers/python:1-${PYTHON_VERSION}-bookworm

# Remove the stale Yarn APT repository that breaks apt-get update.
# The Yarn repo GPG key (NO_PUBKEY 62D54FD4003F6525) is expired/untrusted
# and causes any apt-get update to exit with code 100 — which blocks
# devcontainer features (docker-in-docker, common-utils) from installing.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends libcairo2-dev build-essential pkg-config \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Devcontainer features require root to install (they create the vscode user).
# The devcontainer runtime handles dropping privileges after setup.
USER root
