# Building on top of Ubuntu 14.04. The best distro around.
FROM vinodsharma/python:2.7-devel


COPY . /opt/
# COPY . .
WORKDIR /opt/

# ENTRYPOINT ["/opt/ecs-deploy"]
