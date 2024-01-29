# Agents GCP

This directory contains the source code for the agents deployment.

## Building

Note that we explicitly took out `defog` from requirements.txt because we wanted to track that separately from the rest of the docker commands and speed up the build process. You would need to run `pip install defog` if you're building this server locally, or want to pin the version of defog that you're using.

This also means that if you do update defog-python, you would need to update `dockerfile.agents-python-server` to run pip install on the right version after uploading the new package to PyPi. This is to ensure that the built container has the right (and latest) version of defog-python in it.
