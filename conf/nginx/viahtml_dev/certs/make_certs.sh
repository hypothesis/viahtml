#!/bin/sh

# This generates a key pair with a very long expiry (2032) so we don't have
# to really automate this in anyway
yes '' | openssl req -x509 -nodes -days 4096 -newkey rsa:2048 -keyout localhost.key -out localhost.crt -config localhost.conf