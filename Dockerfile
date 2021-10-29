FROM node:16 AS frontend-builder

COPY ./maubot/management/frontend /frontend
RUN cd /frontend && yarn --prod && yarn build

FROM python:3.9-bullseye

RUN apt-get update && apt-get install build-essential libolm-dev -y

COPY requirements.txt /opt/maubot/requirements.txt
COPY optional-requirements.txt /opt/maubot/optional-requirements.txt
WORKDIR /opt/maubot


RUN pip install --no-cache-dir -r requirements.txt -r optional-requirements.txt \
        dateparser langdetect python-gitlab pyquery cchardet semver tzlocal cssselect

# TODO also remove dateparser, langdetect and pyquery when maubot supports installing dependencies

COPY . /opt/maubot
COPY ./docker/mbc.sh /usr/local/bin/mbc
COPY --from=frontend-builder /frontend/build /opt/maubot/frontend
ENV UID=1337 GID=1337 XDG_CONFIG_HOME=/data
VOLUME /data

CMD ["/opt/maubot/docker/run.sh"]
