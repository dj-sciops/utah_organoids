ARG PY_VER
ARG WORKER_BASE_HASH
ARG SORTER_IMAGE
FROM datajoint/djbase:py${PY_VER}-debian-${WORKER_BASE_HASH} as djbase

ARG DEPLOY_KEY
COPY --chown=anaconda $DEPLOY_KEY $HOME/.ssh/id_ed25519
RUN chmod u=r,g-rwx,o-rwx $HOME/.ssh/id_ed25519 && \
   printf "ssh\ngit" >> /tmp/apt_requirements.txt && \
   /entrypoint.sh echo "installed"

ARG REPO_OWNER
ARG REPO_NAME
ARG REPO_BRANCH
WORKDIR $HOME
RUN ssh-keyscan github.com >> $HOME/.ssh/known_hosts && \
   git clone -b ${REPO_BRANCH} git@github.com:${REPO_OWNER}/${REPO_NAME}.git 

FROM spikeinterface/${SORTER_IMAGE}
COPY --from=djbase /home/anaconda/${REPO_NAME} /home/anaconda/${REPO_NAME}
COPY ../../apt_requirements.txt /tmp/apt_requirements.txt
RUN pip install ./${REPO_NAME} && apt-get update && xargs apt-get install -y < /tmp/apt_requirements.txt