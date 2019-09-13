#!/bin/bash

# This obviously will require some tweaking. Will roll into build.py later.
set -e

server=my_repo.domain.tld
port=2222
user=pkgrepo
src=~/pkgs/built/.
# You should use rrsync to restrict to a specific directory
dest='Arch/.'

echo "Syncing..."
rsync -a --delete -e "ssh -p ${port}" ${src} ${user}@${server}:${dest}
echo "Done."
