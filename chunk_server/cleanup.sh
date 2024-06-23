#!/bin/sh
find /tmp/chunks -name 'pending_*' -mmin +10 -type f -delete
