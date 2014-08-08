# Copyright (c) 2014, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import datetime, logging, time, mimetypes

import boto

LOGGER = logging.getLogger(__name__)


class S3Backend(object):

    def __init__(self, remote_location, dry_run=False):
        self.dry_run = dry_run
        self.default_acl = 'public-read'
        self.conn = boto.connect_s3()
        self.bucket = self.conn.get_bucket(remote_location[5:])

    def list(self):
        """
        Returns a list of all files (recursively) present in a bucket
        with their timestamp.
        """
        return self.bucket.list()

    def _index_by_key(self):
        index = {}
        for key in self.list():
            index[key.name] = key
        return index

    def upload(self, local_files, prefix=''):
        uploads = []
        s3_keys = self._index_by_key()
        for local_meta in local_files:
            if local_meta['Key'] in s3_keys:
                s3_key = s3_keys[local_meta['Key']]
                s3_datetime = datetime.datetime(*time.strptime(
                        s3_key.last_modified, '%a, %d %b %Y %H:%M:%S %Z')[0:6])
                local_datetime = datetime.datetime(*time.strptime(
                        local_meta['LastModified'],
                        '%a, %d %b %Y %H:%M:%S %Z')[0:6])
                if local_datetime < s3_datetime:
                    uploads += [local_meta['Key']]
            else:
                uploads += [local_meta['Key']]
        for filename in uploads:
            headers = {}
            pathname = prefix + filename
            content_type = mimetypes.guess_type(pathname)[0]
            if content_type:
                headers['Content-Type'] = content_type
            if self.dry_run:
                dry_run = "(dry run) "
            else:
                dry_run = ""
            LOGGER.info("%supload %s to %s", dry_run, pathname, filename)
            if not self.dry_run:
                with open(pathname, 'rb') as file_obj:
                    s3_key = boto.s3.key.Key(self.bucket)
                    s3_key.name = filename
                    s3_key.set_contents_from_string(file_obj.read(),
                        headers, replace=True, policy=self.default_acl)
