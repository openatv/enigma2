"""Compile the production metadata change predicate/event dispatch in isolation.
Does not exercise the full GStreamer service lifecycle.
"""
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / "lib/service/servicedab.cpp").read_text()
predicate = re.search(r"const bool radioMetaChanged =.*?;", source, re.S).group()
dispatch = re.search(r"if \(radioMetaChanged \|\| slideChanged.*?m_event\(this, evUpdatedInfo\);", source, re.S).group()
harness = '''
#include <cassert>
#include <cstring>
struct Stats {
 int serviceFound=0, dabplus=0, bitrate=0;
 char serviceLabel[32]={}, ensembleLabel[32]={}, language[32]={}, programType[32]={}, protection[32]={};
};
struct Service {
 Stats m_stats;
 int calls=0;
 enum { evUpdatedInfo=1 };
 void m_event(Service*, int event) { assert(event==evUpdatedInfo); ++calls; }
 void update(const Stats& stats) {
 bool slideChanged=false, logoChanged=false, servicesChanged=false, receiverChanged=false;
''' + predicate + '\n m_stats=stats;\n' + dispatch + '''
 }
};
int main() {
 Service service;
 Stats stats;
 service.update(stats); assert(service.calls==0);
 strcpy(stats.language,"112");
 service.update(stats); assert(service.calls==1);
 service.update(stats); assert(service.calls==1);
 strcpy(stats.language,"9");
 service.update(stats); assert(service.calls==2);
 stats.language[0]=0;
 service.update(stats); assert(service.calls==3);
 strcpy(stats.protection,"EEP 3-A");
 service.update(stats); assert(service.calls==4);
 service.update(stats); assert(service.calls==4);
 strcpy(stats.protection,"EEP 2-A");
 service.update(stats); assert(service.calls==5);
 stats.protection[0]=0;
 service.update(stats); assert(service.calls==6);
}
'''
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)
    (path / "test.cpp").write_text(harness)
    subprocess.run(["g++", "-std=c++14", "-Wall", "-Wextra", str(path / "test.cpp"), "-o", str(path / "test")], check=True)
    subprocess.run([str(path / "test")], check=True)
print("Production event predicate tests passed: late values, changes, unavailable and unchanged suppression")
