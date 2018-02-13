#!/usr/bin/env python3

import grpc
from grpc.tools import protoc
import tempfile

channel = grpc.insecure_channel('sysadministrivia.com:50051')
