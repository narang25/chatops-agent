---
title: "ImagePullBackOff: Docker Hub Anonymous Pull Rate Limit Exceeded"
failure_type: "other"
source_type: "external_doc"
source_url: "https://docs.docker.com/docker-hub/download-rate-limit/"
license: "Apache-2.0"
status: "summary"
---

## Symptoms
Pods fail to start and stay in `ImagePullBackOff` or `ErrImagePull`. Pod events show `toomanyrequests: You have reached your pull rate limit. You may increase the limit by authenticating and upgrading: https://www.docker.com/increase-rate-limit`.

## Likely cause
Anonymous docker pulls from shared NAT gateway IP exceeded Docker Hub limit (100 pulls per 6 hours per IP address).

## How to confirm
Check pod events:
`kubectl describe pod <pod-name> | grep -i toomanyrequests`
Verify image repository is public Docker Hub (e.g. `image: redis:alpine` or `image: nginx:latest`).

## Fix
1. Create a Kubernetes docker-registry secret with authenticated Docker credentials:
`kubectl create secret docker-registry regcred --docker-server=https://index.docker.io/v1/ --docker-username=<user> --docker-password=<token>`
2. Patch the default service account or pod spec with `imagePullSecrets: [{"name": "regcred"}]`.
3. Better: Mirror base images to internal private registry (ECR, GCR, Harbor).
