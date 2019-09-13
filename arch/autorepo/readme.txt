This has a lot of work pending. I need to factor in configuration files, etc.

But it does require the following packages to be installed, and the buildbox (not the repo mirror server itself) needs to be Arch:

- pacman (duh)
- namcap
- devtools (for https://wiki.archlinux.org/index.php/DeveloperWiki:Building_in_a_clean_chroot)

It is designed to be run as a *non-root* user. Use the regen_sudoers.py script to create a sudoers CMND_ALIAS (https://www.sudo.ws/man/1.7.10/sudoers.man.html) to add for your packaging user.
