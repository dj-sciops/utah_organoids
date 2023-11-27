ARG PY_VER
ARG WORKER_BASE_HASH
FROM datajoint/djbase:py${PY_VER}-debian-${WORKER_BASE_HASH}

ARG DEPLOY_KEY
COPY --chown=anaconda $DEPLOY_KEY $HOME/.ssh/id_ed25519
RUN chmod u=r,g-rwx,o-rwx $HOME/.ssh/id_ed25519 && \
    printf "ssh\ngit\ns3fs" >> /tmp/apt_requirements.txt && \
    /entrypoint.sh echo "installed"

ARG REPO_OWNER
ARG REPO_NAME
ARG REPO_BRANCH
WORKDIR $HOME
RUN ssh-keyscan github.com >> $HOME/.ssh/known_hosts && \
    git clone -b ${REPO_BRANCH} git@github.com:${REPO_OWNER}/${REPO_NAME}.git && \
    pip install ./${REPO_NAME}
