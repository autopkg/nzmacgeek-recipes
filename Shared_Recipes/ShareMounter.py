#!/usr/bin/python
#
# Copyright 2016 William McGrath
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
"""See docstring for ShareMounter class"""

from __future__ import absolute_import
import sys
import subprocess
import FoundationPlist
import tempfile
import os.path
import os
import pdb
import re

from autopkglib import Processor, ProcessorError

__all__ = ["ShareMounter"]

class ShareMounter(Processor):
	"""Base class for Processors that need to mount file shares."""
	description = __doc__
	input_variables = {
		"file_share": {
			"required": True,
			"description": 
				"Full path to share to mount."
		},
		"credential_file": {
			"required": False,
			"description":
				"Full path to a plist containg the username and password to connect with, if necessary."
		},
		"mount_point": {
			"required": False,
			"description":
				"Path to a potential mount_point for share."
		},
		"unmount": {
			"required": False,
			"description":
				"Specify this parameter if you want to unmount."
		}
	}
	output_variables = {
		"mount_point": {
			"description":
				"Outputs mount point path."
		}
	}
	
	def __init__(self, data=None, infile=None, outfile=None):
		super(ShareMounter, self).__init__(data, infile, outfile)
		
	def is_mount_point_writeable(self, mount_point):
		try:
			tempfile = os.path.join(mount_point, 'tmp')
			open(tempfile, 'w')
		except IOError:
			return False
		else:
			os.remove(tempfile)
			return True
	
	def get_share_credentials(self):
		if 'credential_file' not in self.env:
			return ''
		else:
			try:
				cfile = open(self.env['credential_file'])
				data = cfile.read()
				cfile.close()
				plist = FoundationPlist.readPlistFromString(data)
				username = plist.get('Username')
				password = plist.get('Password')
			except BaseException as err:
				raise ProcessorError(err)
			return "%s:%s@" % (username, password)				
	
	def mount(self, sharepath, mount_point=None):
		if 'fsmounts' not in self.env:
			self.env['fsmounts'] = dict()
		if sharepath in self.env['fsmounts']:
			raise ProcessorError("%s is already mounted." % sharepath)
		
		try:
			if mount_point != None:
				if self.is_mount_point_writeable(mount_point) != True:
					mount_point = None
			if mount_point == None:
				mount_point = tempfile.mkdtemp(prefix='ShareMounter')
		except BaseException as e:
			raise ProcessorError("Could not write to mount point.")	
		
		# do a string substitution on the share string just in case
		creds = self.get_share_credentials()
		thesharepath = re.sub(r'!!CREDENTIALS!!', creds, sharepath)	
		try:
			proc = subprocess.Popen(("/sbin/mount_smbfs",
									 thesharepath,
									 mount_point),
									 stdout=subprocess.PIPE,
									 stderr=subprocess.PIPE,
									 stdin=subprocess.PIPE)
			(stdout, stderr) = proc.communicate()
		except OSError as err:
			raise ProcessorError(
				"mount execution failed with error code %d: %s"
				% (err.errno, err.strerror))
		
		if proc.returncode != 0:
			raise ProcessorError("mounting %s failed: %s (#%d)" % (sharepath, stdout, proc.returncode))
		
		self.env["fsmounts"][sharepath] = mount_point
		self.output("mounted %s at %s" % (sharepath, mount_point))
		self.env["mount_point"] = mount_point
	
	def unmount(self, sharepath):
		if 'fsmounts' in self.env:
			if sharepath not in self.env['fsmounts']:
				raise ProcessorError("%s was not mounted" % sharepath)
		
			try:
				proc = subprocess.Popen(("/sbin/umount",
									self.env["fsmounts"][sharepath]),
									stdout=subprocess.PIPE,
									stderr=subprocess.PIPE)
				(stdout, stderr) = proc.communicate()
			except OSError as err:
				raise ProcessorError(
					"unmount execution failed with error code %d: %s"
					% (err.errno, err.strerror))
		
			if proc.returncode != 0:
				raise ProcessorError("unmounting %s failed: %s" % (sharepath, stdout))
			
			del self.env['fsmounts'][sharepath]
			self.output("unmounted %s" % sharepath)
		else:
			raise ProcessorError("%s was not mounted" % sharepath)
		
	def main(self):
		if 'unmount' in self.env:
			try:
				self.unmount(self.env['file_share'])
			except BaseException as err:
				raise ProcessorError(err)
		else:
			mount_point = None
			if "mountpoint" in self.env:
				mount_point = self.env['mount_point']
				
			try:
				self.mount(self.env['file_share'], mount_point)
			except BaseException as err:
				raise ProcessorError(err)
			
if __name__ == "__main__":
	PROCESSOR = ShareMounter()
	PROCESSOR.execute_shell()

		
	