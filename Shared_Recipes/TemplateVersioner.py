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
"""See docstring for TemplateVersioner class"""

# Disabling warnings for env members and imports that only affect recipe-
# specific processors.
# pylint: disable=e1101,f0401

from autopkglib import Processor, ProcessorError
from datetime import datetime
import os
import hashlib
import fnmatch
import pdb

__all__ = ["TemplateVersioner"]


class TemplateVersioner(Processor):
  """Provides a Version Number for use with the Templates"""
  description = __doc__
  input_variables = {
  	"mount_point": {
  		"description": "File share mount point containing templates.",
  		"required": True
  	},
  	"file_exclusions": {
  		"description": "File name globs to ignore in file search.",
  		"required": False
  	},
  	"save_checksum": {
  		"description": "Update checksum file.",
  		"required": False
  	},
  	"checksum": {
  		"description": "Latest checksum of template directory",
  		"required": False
  	}
  }
  output_variables = {
  	"version": "Output of an appropriate version number for given params.",
  	"stop_processing": "Trigger variable to stop processing recipe.",
  	"checksum": "Latest directory checksum"
  }

  __doc__ = description
  
  def update_checksum_file(self):
  	if 'checksum' not in self.env:
  		raise ProcessorError('checksum missing') 
   	checksum_file = os.path.join(self.env['RECIPE_CACHE_DIR'], 'checksum')
  	cf = open(checksum_file, 'w')
  	cf.write(self.env['checksum'])
  	cf.close()
  	
  def check_for_changes(self):
	m = hashlib.md5()
	changed = False
  	for root, dirs, files in os.walk(self.env['mount_point']):
  		for file_read in files:
  			if "file_exclusions" in self.env:
  				for excl in self.env['file_exclusions']:
  					if fnmatch.fnmatch(file_read, excl):
  						self.output("Excluding %s as it matches a file_exclusion (%s)." % (file_read, excl), verbose_level=2)
  						continue
  			full_path = os.path.join(root, file_read)
  			for line in open(full_path).readlines():
  				m.update(line)
  	newchecksum = m.hexdigest()
  	oldchecksum = ""
  	self.output("Old checksum: %s", oldchecksum)
  	self.output("New checksum: %s", newchecksum)
  	checksum_file = os.path.join(self.env['RECIPE_CACHE_DIR'], 'checksum')
  	if os.path.isfile(checksum_file) == True:
  		oldchecksum_f = open(checksum_file)
  		oldchecksum = oldchecksum_f.read()
  		oldchecksum_f.close()
  		self.env["checksum"] = oldchecksum
  	if oldchecksum != newchecksum:
  		changed = True
  		self.env["checksum"] = newchecksum
  		self.env["stop_processing"] = False
  	return changed
  		
  def main(self):
  	if 'save_checksum' in self.env:
  		self.update_checksum_file()
  	else:
  		if self.check_for_changes() == False:
  			self.env["stop_processing"] = True
  	self.env["version"] = datetime.strftime(datetime.now(), '%y%m%d') + '.0'

if __name__ == "__main__":
  PROCESSOR = TemplateVersioner()
  PROCESSOR.execute_shell()