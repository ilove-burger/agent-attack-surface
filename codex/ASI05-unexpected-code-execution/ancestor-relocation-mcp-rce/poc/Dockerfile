FROM node:24-alpine

ARG CODEX_VERSION=0.147.0

RUN npm install --global "@openai/codex@${CODEX_VERSION}"

COPY run-inside.sh stage1.sh stage2.sh payload.sh malicious-config.toml /opt/poc/
RUN chmod 0755 /opt/poc/run-inside.sh /opt/poc/stage1.sh /opt/poc/stage2.sh /opt/poc/payload.sh

ENTRYPOINT ["/opt/poc/run-inside.sh"]
