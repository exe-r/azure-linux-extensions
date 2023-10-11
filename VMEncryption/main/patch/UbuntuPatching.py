#!/usr/bin/python
#
# Copyright 2015 Microsoft Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requires Python 2.4+


import os
import sys

from .AbstractPatching import AbstractPatching
from Common import CommonVariables
from CommandExecutor import CommandExecutor


class UbuntuPatching(AbstractPatching):
    def __init__(self, logger, distro_info):
        super(UbuntuPatching, self).__init__(distro_info)
        self.logger = logger
        self.command_executor = CommandExecutor(logger)
        self.base64_path = '/usr/bin/base64'
        self.bash_path = '/bin/bash'
        self.blkid_path = '/sbin/blkid'
        self.cat_path = '/bin/cat'
        self.cryptsetup_path = '/sbin/cryptsetup'
        self.dd_path = '/bin/dd'
        self.e2fsck_path = '/sbin/e2fsck'
        self.echo_path = '/bin/echo'
        self.lsblk_path = '/bin/lsblk'
        self.lsscsi_path = '/usr/bin/lsscsi'
        self.mkdir_path = '/bin/mkdir'
        self.mount_path = '/bin/mount'
        self.openssl_path = '/usr/bin/openssl'
        self.resize2fs_path = '/sbin/resize2fs'
        self.umount_path = '/bin/umount'
        self.touch_path = '/usr/bin/touch'
        self.min_version_online_encryption='22.04'
        #support_online_encryption is false in base class. 
        #self.support_online_encryption=self.validate_online_encryption_support()

    def packages_installed(self, packages):
        ''' return true if all packages in list are already installed '''
        installed = True
        for package in packages:
            cmd = "dpkg-query -s {package} | grep -q 'install ok installed'"
            if not self.command_executor.ExecuteInBash(cmd, False, None, None, True):
                installed = False
                self.logger.log("{1} package not yet installed".format(package))
        return installed

    def install_azguestattestation(self):
        '''installtion for azguestattestation1 package.'''
        cmd = 'dpkg -s azguestattestation1'
        ret = self.command_executor.Execute(cmd,timeout=30)
        if ret == CommonVariables.process_success:
            self.logger.log("azguestattestation1 package is already available!")
            return True
        cmd = 'wget https://packages.microsoft.com/repos/azurecore/pool/main/a/azguestattestation1/azguestattestation1_1.0.5_amd64.deb'
        #download the package
        ret = self.command_executor.Execute(cmd,timeout=30)
        if ret == CommonVariables.process_success:
            #install package
            cmd = 'dpkg -i azguestattestation1_1.0.5_amd64.deb'
            ret = self.command_executor.Execute(cmd,timeout=30)
            if ret == CommonVariables.process_success:
                self.logger.log("azguestattestation1 package installation is successful!")
                return True
        return False


    def install_cryptsetup(self):
        packages = ['cryptsetup-bin']

        if self.packages_installed(packages):
            return
        else:
            cmd = " ".join(['apt-get', 'install', '-y', '--no-upgrade'] + packages)
            return_code = self.command_executor.Execute(cmd, timeout=30)
            if return_code == -9:
                msg = "Command: apt-get install timed out. Make sure apt-get is configured correctly and there are no network problems."
                raise Exception(msg)

            # If install fails, try running apt-get update and then try install again
            if return_code != 0:
                self.logger.log('cryptsetup installation failed. Retrying installation after running update')
                return_code = self.command_executor.Execute('apt-get -o Acquire::ForceIPv4=true -y update', timeout=30)
                # Fail early if apt-get update times out.
                if return_code == -9:
                    msg = "Command: apt-get -o Acquire::ForceIPv4=true -y update timed out. Make sure apt-get is configured correctly."
                    raise Exception(msg)
                cmd = " ".join(['apt-get', 'install', '-y'] + packages)
                return_code = self.command_executor.Execute(cmd, timeout=30)
                if return_code == -9:
                    msg = "Command: apt-get install timed out. Make sure apt-get is configured correctly and there are no network problems."
                    raise Exception(msg)
                return return_code

    def install_extras(self):
        # select the appropriate version specific parted package
        if (sys.version_info >= (3,)):
            parted = 'python3-parted'
        else:
            parted = 'python-parted'

        # construct package installation list
        packages = ['at',
                    'cryptsetup-bin',
                    'grub-pc-bin',
                    'lsscsi',
                    parted,
                    'python-six',
                    'procps',
                    'psmisc',
                    'nvme-cli']

        if self.packages_installed(packages):
            return
        else:
            cmd = " ".join(['apt-get', 'update'])
            self.command_executor.Execute(cmd)

            cmd = " ".join(['apt-get', 'install', '-y'] + packages)
            self.command_executor.Execute(cmd)

    def update_prereq(self):
        self.logger.log("Trying to update Ubuntu osencrypt entry.")
        filtered_crypttab_lines = []
        initramfs_repack_needed = False
        if not os.path.exists('/etc/crypttab'):
            return
        with open('/etc/crypttab', 'r') as f:
            for line in f.readlines():
                crypttab_parts = line.strip().split()

                if len(crypttab_parts) < 3:
                    filtered_crypttab_lines.append(line)
                    continue

                if crypttab_parts[0].startswith("#"):
                    filtered_crypttab_lines.append(line)
                    continue

                if crypttab_parts[0] == 'osencrypt' and (crypttab_parts[1] == '/dev/sda1' or crypttab_parts[1].startswith(CommonVariables.disk_by_id_root)) and 'keyscript=/usr/sbin/azure_crypt_key.sh' in line:
                    self.logger.log("Found osencrypt entry to update.")
                    stable_os_disk_path = self._get_stable_os_disk_path()
                    if stable_os_disk_path is not None:
                        filtered_crypttab_lines.append(CommonVariables.osencrypt_crypttab_line_ubuntu.format(stable_os_disk_path))
                        initramfs_repack_needed = True
                        continue
                    else:
                        self.logger.log("Cannot find expected link to root partition.")

                filtered_crypttab_lines.append(line)

        if initramfs_repack_needed:
            with open('/etc/crypttab', 'w') as f:
                f.writelines(filtered_crypttab_lines)
            self.command_executor.Execute('update-initramfs -u -k all', True)
            self.logger.log("Successfully updated osencrypt entry.")
        else:
            self.logger.log('osencrypt entry not present or already updated or expected root partition link does not exists.')

    def _get_stable_os_disk_path(self):
        gen1_disk = os.path.join(CommonVariables.azure_symlinks_dir, "root-part1")
        gen2_disk = os.path.join(CommonVariables.azure_symlinks_dir, "scsi0/lun0-part1")
        if os.path.exists(gen1_disk):
            return gen1_disk
        elif os.path.exists(gen2_disk):
            return gen2_disk
        else:
            return None
