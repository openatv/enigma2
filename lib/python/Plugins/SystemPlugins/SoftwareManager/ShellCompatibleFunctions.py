#!/usr/bin/python
# -*- coding: utf-8 -*-

import subprocess,shutil,os

# MANDATORY_RIGHTS contains commands to ensure correct rights for certain files
MANDATORY_RIGHTS = "chown -R root:root /home/root /etc/auto.network /etc/default/dropbear /etc/dropbear ; chmod 600 /etc/auto.network /etc/dropbear/* /home/root/.ssh/* ; chmod 700 /home/root /home/root/.ssh"

# BLACKLISTED lists all files/folders that MUST NOT be backed up or restored in order for the image to work properly
BLACKLISTED = ['home/root/.cache', 'etc/passwd', 'etc/shadow', 'etc/group', 'etc/samba/distro', 'etc/samba/smb.conf', 'home/root/FastRestore.log']

IMAGE_INSTALL = ['openatv-base', 'enigma2-plugin-settings-defaultsat', 'run-postinsts']

PACKAGES = '/var/lib/opkg/lists'
INSTALLEDPACKAGES = '/var/lib/opkg/status'

def backupUserDB():
	oldpasswd=()
	oldshadow=()
	oldgroups=()
	neededgroups=[]
	tmppasswd=[]
	tmpgroups=[]

	with open('/etc/passwd') as f:
		oldpasswd = f.readlines()
		oldpasswd = [x.strip() for x in oldpasswd]

	with open('/etc/shadow') as f:
		oldshadow = f.readlines()
		oldshadow = [x.strip() for x in oldshadow]

	with open('/etc/group') as f:
		oldgroups = f.readlines()
		oldgroups = [x.strip() for x in oldgroups]

	for x in oldpasswd:
		name, passwd, uid, gid, gecos, home, shell = x.split(':')

		# Skip system users except "root" and "kids", also skip "nobody"
		if (int(uid) < 1000 and name != "root" and name != "kids") or name == "nobody":
			continue

		# We have a user worth saving, search his password hash in /etc/shadow
		for y in oldshadow:
			sname, spasswd, bullshit = y.split(':', 2)
			if name == sname:
				# Store hash in password field
				passwd=spasswd

		# ... also search his group ...
		for z in oldgroups:
			gname, gpasswd, ggid, bullshit = z.split(':', 3)
			if gid == ggid:
				# ... mark this group as (potentially) needed, but never save "root", "kids" or "nogroup" groups
				if (gname not in neededgroups) and (gname != "root") and (gname != "kids") and (gname != "nogroup"):
					neededgroups.append(gname)

				# ... add group's name after numeric gid and store his line in backup ...
				newpwd = ":".join( ( name, passwd, uid, gid, gname, gecos, home, shell ) )
				tmppasswd.append(newpwd)

	# Copy only needed groups into backup ...
	for x in oldgroups:
		name, rest = x.split(':', 1)

		if name in neededgroups:
			tmpgroups.append(x)

	# Write out backup files ...
	passwdtxt = open('/tmp/passwd.txt', 'w')
	for item in tmppasswd:
		passwdtxt.write("%s\n" % item)
	passwdtxt.close()

	groupstxt = open('/tmp/groups.txt', 'w')
	for item in tmpgroups:
		groupstxt.write("%s\n" % item)
	groupstxt.close()

def restoreUserDB():
	if not (os.path.isfile('/tmp/passwd.txt') and os.path.isfile('/tmp/groups.txt')):
		return

	oldpasswd=[]
	oldgroups=[]
	newpasswd=[]
	newgroups=[]
	takenuids=[]
	takengids=[]
	successusers=[]

	with open('/tmp/passwd.txt') as f:
		oldpasswd = f.readlines()
		oldpasswd = [x.strip() for x in oldpasswd]

	with open('/tmp/groups.txt') as f:
		oldgroups = f.readlines()
		oldgroups = [x.strip() for x in oldgroups]

	with open('/etc/passwd') as f:
		newpasswd = f.readlines()
		newpasswd = [x.strip() for x in newpasswd]
		name, passwd, uid, gid, gecos, home, shell = x.split(':')
		takenuids.append(uid)

	with open('/etc/group') as f:
		newgroups = f.readlines()
		newgroups = [x.strip() for x in newgroups]
		name, passwd, gid, rest = x.split(':', 3)
		takengids.append(gid)

	for x in oldpasswd:
		usersuccess = False
		groupsuccess = False
		oldname, oldpasswd, olduid, oldgid, oldgname, oldgecos, oldhome, oldshell = x.split(':')

		for y in newpasswd:
			if y.startswith(oldname + ":"):
				# The the user still exists, just re-import his password later.
				usersuccess = True
				groupsuccess = True
				break

		if not usersuccess:
			# The the user does not exist anymore, we have to re-create ....

			# ... but at least try to find his group (by group name) ...
			groupsuccess = False
			for y in newgroups:
				gname, gpasswd, gid, grest = y.split(':', 3)
				if oldgname == gname:
					groupsuccess = True
					break

			# ... if the group was also not found, we have to re-create that first ...
			if not groupsuccess:
				cmd = ["/bin/busybox", "addgroup"]
				if oldgid not in takengids:
					cmd.append("-g" + oldgid)
				cmd.append(oldgname)

				try:
					subprocess.check_call(cmd)
					groupsuccess = True
				except:
					groupsuccess = False

			# Re-create the user if the group still exists or was successfully re-created ...
			if groupsuccess:
				cmd = ["/bin/busybox", "adduser", "-H", "-D","-G",oldgname]
				if oldhome != "":
					cmd.append("-h" + oldhome)
				if oldgecos != "":
					cmd.append("-g" + oldgecos)
				if oldshell != "":
					cmd.append("-s" + oldshell)
				if olduid not in takenuids:
					cmd.append("-u" + olduid)
				cmd.append(oldname)

				try:
					subprocess.check_call(cmd)
					usersuccess = True
				except:
					usersuccess = False

		if usersuccess:
			successusers.append([oldname, oldpasswd])

	shadow=[]
	with open('/etc/shadow') as f:
		shadow = f.readlines()
		shadow = [x.strip() for x in shadow]

	newshadowfile = open('/tmp/shadow.new', 'w')
	for x in shadow:
		name, passwd, rest = x.split(':', 2)
		for y in successusers:
			if y[0] == name:
				passwd = y[1]
				break
		newshadowfile.write("%s:%s:%s\n" % (name, passwd, rest))
	newshadowfile.close()
	shutil.move("/tmp/shadow.new", "/etc/shadow")

def listpkg(type="installed"):
	pkgs = []
	ret = []
	for line in open(INSTALLEDPACKAGES, 'r'):
		if line.startswith('Package:'):
			package = line.split(":",1)[1].strip()
			version = ''
			status = ''
			autoinstalled = False
			continue
		if package is None:
			continue
		if line.startswith('Version:'):
			version = line.split(":",1)[1].strip()
		if line.startswith('Auto-Installed:'):
			auto = line.split(":",1)[1].strip()
			if auto == "yes":
				autoinstalled = True
		elif len(line) <= 1:
			pkgs.append({
				"package": package,
				"version": version,
				"status": status,
				"autoinstalled": autoinstalled
			})
			package = None

	for package in pkgs:
		if type == "installed":
			ret.append(package['package'])
		elif type == "auto":
			if package['autoinstalled']:
				ret.append(package['package'])
		elif type == "user":
			if not package['autoinstalled']:
				if not package['package'] in IMAGE_INSTALL:
					ret.append(package['package'])

	return sorted(ret)
