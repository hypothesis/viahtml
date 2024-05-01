FROM python:3.11.8-alpine3.19
LABEL maintainer="Hypothes.is Project and contributors"

# Install nginx & supervisor
RUN apk add --no-cache nginx supervisor build-base libffi-dev openssl-dev

# Create the hypothesis user, group, home directory and package directory.
RUN addgroup -S hypothesis && adduser -S -G hypothesis -h /var/lib/hypothesis hypothesis
WORKDIR /var/lib/hypothesis

# Ensure nginx state and log directories writeable by unprivileged user.
RUN chown -R hypothesis:hypothesis /etc/nginx/conf.d /var/log/nginx /var/lib/nginx

# Copy minimal data to allow installation of python dependencies.
COPY ./requirements/requirements.txt ./

# Install build deps, build, and then clean up.
RUN apk add --no-cache --virtual build-deps \
  && pip install --no-cache-dir -U pip \
  && pip install --no-cache-dir -r requirements.txt \
  && apk del build-deps

COPY ./conf/nginx/nginx.conf /etc/nginx/nginx.conf
COPY ./conf/nginx/viahtml /etc/nginx/viahtml
COPY . .

# Minic the `make build` behavior in tox to build the static assets
RUN python bin/build_static.py
RUN python -m whitenoise.compress --no-brotli static

USER hypothesis

CMD /usr/bin/supervisord -c /var/lib/hypothesis/conf/supervisord.conf
