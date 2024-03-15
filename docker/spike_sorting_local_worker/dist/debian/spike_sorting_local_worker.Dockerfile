ARG PY_VER
ARG WORKER_BASE_HASH
FROM datajoint/djbase:py${PY_VER}-debian-${WORKER_BASE_HASH}

USER root
## system level dependencies
RUN apt-get update
COPY ../../apt_requirements.txt /tmp/apt_requirements.txt
RUN xargs apt-get install -y < /tmp/apt_requirements.txt
RUN xargs apt-get install -y unzip git

# Add anaconda user to the docker group
ARG DOCKER_GID=1001
RUN groupadd -o -g ${DOCKER_GID} docker || groupmod -o -g ${DOCKER_GID} docker
RUN usermod -aG docker anaconda

## NVIDIA driver is managed by nvidia-container-toolkit and nvidia-docker-2
## https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#setting-up-nvidia-container-toolkit

USER anaconda
WORKDIR $HOME

ARG DEPLOY_KEY
COPY --chown=anaconda $DEPLOY_KEY $HOME/.ssh/id_ed25519
RUN chmod u=r,g-rwx,o-rwx $HOME/.ssh/id_ed25519 && \
   ssh-keyscan github.com >> $HOME/.ssh/known_hosts

ENV SSL_CERT_DIR=/etc/ssl/certs
ARG REPO_OWNER
ARG REPO_NAME
ARG REPO_BRANCH
RUN git clone -b ${REPO_BRANCH} git@github.com:${REPO_OWNER}/${REPO_NAME}.git && \
   pip install --upgrade pip && \
   pip install ./${REPO_NAME}
