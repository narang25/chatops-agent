---
title: "Start containers automatically"
failure_type: crash_loop
source_type: external_doc
source_url: https://docs.docker.com/engine/containers/start-containers-automatically/
license: Apache-2.0
status: external
---

## Summary
Docker provides restart policies to control whether your containers start automatically when they exit, or when Docker restarts. Docker recommends that you use restart policies, and avoid using process managers to start containers.

Restart policies are different from the --live-restore flag of the dockerd command. Using --live-restore lets you keep your containers running during a Docker upgrade, though networking and user input are interrupted.

To configure the restart policy for a container, use the --restart flag when using the docker run command. The value of the --restart flag can be any of the following:

The following command starts a Redis container with the unless-stopped restart policy. Docker restarts the container if it exits or if the daemon restarts, but not if you stopped the container yourself.

The following command changes the restart policy for an already running container named redis.

The following command ensures all running containers restart.

## Reference
Full article / official documentation: https://docs.docker.com/engine/containers/start-containers-automatically/
