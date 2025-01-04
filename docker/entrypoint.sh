#!/bin/sh

# Where $ENVSUBS is whatever command you are looking to run
$ENVSUBS < file1 > file2

# Install aditional packages
if [ -n "$ADDITIONAL_INSTALLS" ]; then
  pip install $ADDITIONAL_INSTALLS
fi

# This will exec the CMD from your Dockerfile, i.e. "npm start"
exec "$@"