---
title: "Dockerfile reference"
failure_type: other
source_type: external_doc
source_url: https://docs.docker.com/reference/dockerfile/
license: Apache-2.0
status: external
---

## Summary
Docker can build images automatically by reading the instructions from a Dockerfile. A Dockerfile is a text document that contains all the commands a user could call on the command line to assemble an image. This page describes the commands you can use in a Dockerfile.

The Dockerfile supports the following instructions:

Here is the format of the Dockerfile:

The instruction is not case-sensitive. However, convention is for them to be UPPERCASE to distinguish them from arguments more easily.

Docker runs instructions in a Dockerfile in order. A Dockerfile must begin with a FROM instruction. This may be after parser directives, comments, and globally scoped ARGs. The FROM instruction specifies the base image from which you are building. FROM may only be preceded by one or more ARG instructions, which declare arguments that are used in FROM lines in the Dockerfile.

BuildKit treats lines that begin with # as a comment, unless the line is a valid parser directive. A # marker anywhere else in a line is treated as an argument. This allows statements like:

## Reference
Full article / official documentation: https://docs.docker.com/reference/dockerfile/
