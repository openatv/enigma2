# Copyright (C) 2022-2025 jbleyel
# This file is part of openATV enigma2 <https://github.com/openatv/enigma2>.
#
# EITFile.py is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# dogtag is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EITFile.py.  If not, see <http://www.gnu.org/licenses/>.

# Changelog:
# 1.0 Initial version
# 1.1 Improve chunk calculation

__version__ = "1.1"

from datetime import datetime

EIT_SHORT_EVENT_DESCRIPTOR = 0x4d
EIT_EXTENDED_EVENT_DESCRIPOR = 0x4e


class Bytes:

    def __init__(self):
        self.b = bytearray()

    def len(self):
        return len(self.b)

    def append(self, b):
        self.b.append(b)

    def appends(self, bs):
        self.b.extend(bs)

    def save(self, fileName):
        try:
            with open(fileName, "wb") as f:
                f.write(self.b)
        except OSError as error:
            print("[EITFile] Error: save '%s' / %s", (fileName, str(error)))


class Descriptor:
    def __init__(self, lang: str):
        self.lang = lang
        self.size = 0
        self.data = Bytes()
        self.data.append(self.getTag())

    def getTag(self):  # overwrite in child class
        pass

    def getBytes(self):
        return self.data.b

    def addData(self, data):
        self.data.append(data)

    def addBytes(self, obj: Bytes):
        self.data.b.extend(obj.b)

    def addlang(self):
        self.data.appends(self.lang.encode())

    def calcSize(self):
        self.size = self.data.len()


class DescriptorShort(Descriptor):
    def __init__(self, lang: str, title: str, short: str):
        Descriptor.__init__(self, lang)
        tbytes = Bytes()
        tlen = len(title)
        tbytes.append(tlen + 1)
        tbytes.append(0x15)  # UTF8
        if tlen > 0:
            tbytes.appends(title)

        sbytes = Bytes()
        slen = len(short)
        sbytes.append(slen + 1)
        sbytes.append(0x15)  # UTF8
        if slen > 0:
            sbytes.appends(short)

        self.addData(3 + sbytes.len() + tbytes.len())
        self.addlang()
        self.addBytes(tbytes)
        self.addBytes(sbytes)
        self.calcSize()

    def getTag(self):
        return EIT_SHORT_EVENT_DESCRIPTOR


class DescriptorExtended(Descriptor):
    def __init__(self, lang: str, text: str):
        Descriptor.__init__(self, lang)
        ebytes = Bytes()
        elen = len(text)
        ebytes.append(elen + 1)
        ebytes.append(0x15)  # UTF8
        ebytes.appends(text)
        self.addData(7 + elen)
        self.addData(0)
        self.addlang()
        self.addData(0)
        self.addBytes(ebytes)
        self.calcSize()

    def getTag(self):
        return EIT_EXTENDED_EVENT_DESCRIPOR


class Header():
    def __init__(self, event_id: int, start: datetime, event_duration: int, free_CA_mode: bool, running_status: int, descriptors_loop_length: int):
        def dec2bcd(dec: int):
            tens, units = divmod(dec, 10)
            return (tens << 4) + units

        def getDate(start: datetime):
            m = start.month
            y = start.year - 1900
            offset = 1 if m == 2 else 0
            year = int((y - offset) * 365.25)
            month = int(((m + 1) + (offset * 12)) * 30.6001)
            return round(14956 + start.day + month + year)

        self.data = Bytes()
        self.data.append(event_id >> 8)
        self.data.append(event_id & 0xFF)

        date = getDate(start)
        self.data.append(date >> 8)
        self.data.append(date & 0xFF)

        self.data.append(dec2bcd(start.hour))
        self.data.append(dec2bcd(start.minute))
        self.data.append(dec2bcd(start.second))

        m, s = divmod(event_duration, 60)
        h, m = divmod(m, 60)
        self.data.append(dec2bcd(h))
        self.data.append(dec2bcd(m))
        self.data.append(dec2bcd(s))

        p = running_status << 5
        p += (0x10 if free_CA_mode else 0)
        p += (descriptors_loop_length >> 8)
        self.data.append(p)
        self.data.append(descriptors_loop_length & 0xFF)

    def getBytes(self):
        return self.data.b


class EITFile():
    def __init__(self, filename: str, lang: str, event_id: int, start: datetime, event_duration: int, title: str, short: str, extended: str):
        self.Data = Bytes()
        self.filename = filename
        if title:
            title = title.encode()
            short = short.encode()
            if (len(title) + len(short)) < 248:
                descriptors = []
                shortDescriptor = DescriptorShort(lang, title, short)
                descriptors.append(shortDescriptor)
                if extended:
                    extended = extended.encode()
                    maxlen = 248
                    chunks = [extended[i:i + maxlen] for i in range(0, len(extended), maxlen)]
                    for chunk in chunks:
                        extendedDescriptor = DescriptorExtended(lang, chunk)
                        descriptors.append(extendedDescriptor)

                l = 0
                for descriptor in descriptors:
                    l += descriptor.size

                header = Header(event_id, start, event_duration, False, 0, l)

                self.Data.b.extend(header.getBytes())

                for descriptor in descriptors:
                    self.Data.b.extend(descriptor.getBytes())
            else:
                print("[EITFile] Error: length of title and short description is too long")
        else:
            print("[EITFile] Error: Empty title is not valid")

    def save(self):
        self.Data.save(self.filename)

    def dump(self):
        for idx, b in enumerate(self.Data.b):
            print("%d - %s" % (idx, b))


# eitFile = EITFile("1.eit", "deu", 1, datetime.now(), 100, "Title", "Short", "Extended")
# eitFile.save()
