# Building on top of Ubuntu 14.04. The best distro around.
FROM gobble/python:2.7-devel

RUN yum install -y docker

COPY . /opt/
WORKDIR /opt/

# ENTRYPOINT ["/opt/ecs-deploy"]
