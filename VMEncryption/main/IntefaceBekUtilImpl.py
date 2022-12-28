#!/usr/bin/env python
#
# Azure Disk Encryption For Linux extension
#
# Copyright 2016 Microsoft Corporation
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
import os
from Common import TestHooks
import base64

class BekMissingException(Exception):
    """
    add retry-logic to the network api call.
    """
    def __init__(self, value):
       self.value = value

    def __str__(self):
       return(repr(self.value))

class IntefaceBekUtilImpl(object):
    '''
    This is an interface used for funcitonality implementation for BEK util class
    '''
    wrong_fs_msg = "BEK does not have vfat filesystem."
    not_mounted_msg = "BEK is not mounted."
    partition_missing_msg = "BEK disk does not expected partition."
    bek_missing_msg = "BEK disk is not attached."

    def __init__(self) -> None:
        pass

    def generate_passphrase(self):
        if TestHooks.use_hard_code_passphrase:
            return TestHooks.hard_code_passphrase
        else:
            with open("/dev/urandom", "rb") as _random_source:
                bytes = _random_source.read(127)
                passphrase_generated = base64.b64encode(bytes)
            return passphrase_generated    

    def store_bek_passphrase(self, encryption_config, passphrase):
        pass

    def get_bek_passphrase_file(self, encryption_config):
        pass

    def mount_bek_volume(self):
        pass

    def is_bek_volume_mounted_and_formatted(self):
        pass
    
    def is_bek_disk_attached_and_partitioned(self):
        pass

    def umount_azure_passhprase(self, encryption_config, force=False):
        pass

    def delete_bek_passphrase_file(self, encryption_config):
        bek_filename = encryption_config.get_bek_filename()
        bek_file = self.get_bek_passphrase_file(encryption_config)
        if not bek_file:
            return
        bek_dir = os.path.dirname(bek_file)
        for file in os.listdir(bek_dir):
            if bek_filename in file:
                os.remove(os.path.join(bek_dir, file))
