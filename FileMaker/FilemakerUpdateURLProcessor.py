#!/usr/local/autopkg/python
# FilemakerUpdateURLProcessor.py
# Fetches information about the latest FileMaker Pro updater.
#
# Copyright 2016 William McGrath
# w.mcgrath@auckland.ac.nz
#
# Licensed under the Apache License, version 2.0 (the "License"). You
# may not use this file except in compliance with the
# License.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""See docstring for FilemakerUpdateURLProcessor class"""

from __future__ import absolute_import

import json
import os
import re
from operator import itemgetter

from autopkglib import Processor, ProcessorError, URLGetter

try:
    from urllib.parse import urlsplit  # Python 3
except:
    from urlparse import urlsplit  # Python 2


__all__ = ["FilemakerUpdateURLProcessor"]

# This was determined by reviewing the sources of the updates site at
# http://www.filemaker.com/support/downloads/
UPDATE_FEED = "http://www.filemaker.com/support/updaters/updater_json.txt?id=1231231231"


class FilemakerUpdateURLProcessor(URLGetter):
    """Provides a download URL for the most recent version of FileMaker Pro"""

    description = __doc__
    input_variables = {
        "major_version": {
            "required": True,
            "description": "The major version for which updater should be downloaded",
        },
        "do_full_installer": {
            "required": False,
            "description": "If this is set to true, the processor will look for a FULL install URL instead.",
        },
    }
    output_variables = {
        "url": {"description": "Outputs this updaters url."},
        "version": {"description": "Outputs the version to expect."},
        "package_name": {"description": "Outputs the name of the patch"},
        "package_file": {"description": "Outputs the name of the package file"},
    }

    def extractMacUpdates(self, obj):
        updates = []
        for pkg in obj:
            if pkg["platform"] == "Mac":
                updates.append(pkg)
        return updates

    def extractMajorUpdates(self, obj):
        updates = []
        for pkg in obj:
            if pkg["version"][0 : len(self.env.get("major_version"))] == self.env.get(
                "major_version"
            ):
                updates.append(pkg)
        return updates

    def filterOutServerUpdates(self, obj):
        updates = []
        for pkg in obj:
            if re.search(r"Server", pkg["product"]) is None:
                updates.append(pkg)
        return updates

    def compare_vers(self, v1, v2):
        (major1, minor1, patch1, build1) = v1
        (major2, minor2, patch2, build2) = v2
        if major1 > major2:
            return v1
        if minor1 > minor2:
            return v1
        if patch1 > patch2:
            return v1
        if build1 > build1:
            return v1
        return v1

    def findLatestUpdate(self, obj):
        # an enum-like hash to enable the variant of FileMaker versioning to be taken
        # into account when versioning
        patch_levels = {"a": 1, "b": 2, "c": 3, "d": 4}

        updates = []
        versions = []
        for pkg in obj:
            version = pkg["version"].split(".")
            version_str = pkg["version"]
            major = version[0]
            minor = version[1]
            patch = "0"
            if len(version) > 2:
                patch = version[2]
            build = "0"
            # look for a letter in the patchlevel
            mo = re.search(r"([0-9]*)([A-Za-z]*)", patch)
            if mo is not None:
                (patch, build) = mo.groups()
                if build == "":
                    build = 0
                else:
                    build = patch_levels[build]
            mo = re.search(r"([0-9]*)v([0-9]*)", minor)
            if mo is not None:
                (minor, build) = mo.groups()
            versions.append((major, minor, patch, build, version_str))
        sorted_versions = sorted(versions, key=itemgetter(0, 1, 2, 3), reverse=True)
        version_str = versions[0][4]
        for pkg in obj:
            if pkg["version"] == version_str:
                return pkg
        return None

    def getLatestFilemakerInstaller(self):
        version_str = self.env.get("major_version")
        try:
            data = self.download(UPDATE_FEED)
        except Exception as e:
            raise ProcessorError("Can't get to Filemaker Updater feed: %s" % e)

        metadata = json.loads(data)
        # extract all the Mac updates
        mac_updates = self.extractMacUpdates(metadata)
        mac_updates = self.filterOutServerUpdates(mac_updates)
        mac_updates = self.extractMajorUpdates(mac_updates)
        update = self.findLatestUpdate(mac_updates)
        return update

    def version_matcher(self, url):
        fname = os.path.basename(urlsplit(url).path)
        version_match = re.search(r"([0-9]{2}.[0-9]{0,2}.[0-9]{0,2}.[0-9]{0,4})", fname)
        if version_match is None:
            raise ProcessorError(
                "Something went wrong matching FMP update to full version."
            )
        else:
            return version_match.group(1)

    def main(self):
        try:
            url = ""
            update = self.getLatestFilemakerInstaller()
            should_be_full = self.env.get("do_full_installer")
            url = ""
            if should_be_full == 1:
                update["version"] = self.version_matcher(update["url"])
                # extract the version from the URL string - this is a weird setup...
                url = (
                    "http://fmdl.filemaker.com/maint/107-85rel/fmp_%s.dmg"
                    % update["version"]
                )
            else:
                update["version"] = self.version_matcher(update["url"])
                url = update["url"]

            self.output("URL found '%s'" % url, verbose_level=2)
            self.env["version"] = update["version"]
            self.env["url"] = url
            self.env["package_name"] = update["name"]
            self.env["package_file"] = os.path.basename(urlsplit(url).path)
        except Exception as err:
            # handle unexpected errors here
            raise ProcessorError(err)


if __name__ == "__main__":
    PROCESSOR = FilemakerUpdateURLProcessor()
    PROCESSOR.execute_shell()
