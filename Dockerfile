# Building on top of Ubuntu 14.04. The best distro around.
FROM gobble/python:2.7-devel


COPY ./ecs-deploy /opt/ecs-deploy
WORKDIR /opt/ecs-deploy/

# ENTRYPOINT ["/opt/ecs-deploy"]
