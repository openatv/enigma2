# DAB metadata regression tests

From the repository root, build the real decoder and PAD dependencies:

```sh
g++ -std=c++14 -O1 -g -Wall -Wextra -fsanitize=address,undefined \
  -D__lib_service_dabdebug_h '-DeDABDebug(...)=((void)0)' -I. \
  tests/dab/test_metadata.cpp lib/service/dabdecoder.cpp \
  lib/service/dabpacketdecoder.cpp lib/service/dabpaddecoder.cpp \
  lib/service/dabmotmanager.cpp lib/service/dabpadtools.cpp \
  -o /tmp/test_dab_metadata
ASAN_OPTIONS=detect_leaks=0 /tmp/test_dab_metadata
# Optional replay of the ERT ETI-NI capture (not included in the repository):
ASAN_OPTIONS=detect_leaks=0 /tmp/test_dab_metadata /path/to/ert.eti
```

Only application logging is disabled; the FIC, ETI, audio/PAD and metadata code
is compiled from the production sources. Address/undefined-behaviour checking
remains active. Leak detection is disabled because some container environments
cannot inspect processes; this is not a leak test.

The synthetic ETI frames exercise early/late FIG 0/5, packet/FIDC isolation,
optional FIG 0/17 language fallback, truncated records, future/other-ensemble
metadata, EEP-A, EEP-B and nonconsecutive UEP levels. The optional ERT replay
checks ETSI audio language code 112 (Greek) for all 14 services, EEP 3-A for 0x1206/0x1332 and
EEP 2-A for the other twelve services.

These are host tests. They do not replace an image build or visual/hardware
validation on a receiver.

Tools/DAB.py maps ETSI codes to existing International/ISO639 identifiers; C++ retains the ETSI code.

Python presentation tests: `python tests/dab/test_language.py`.
Skins use the existing `ServiceInfo` converter with `DABLanguage` or `DABProtection`.
The string-valued `sTagLanguageCode` now carries a decimal ETSI code; old RTL
backend names remain readable by the Python helper during staged upgrades.

UI host tests use real CurrentService, ServiceInfo, language data/accessors and
InformationService rendering/callback methods. Native bindings/navigation and
widget construction are substituted. Run `python tests/dab/test_updates.py`
for the production metadata predicate/dispatch extracted from servicedab.cpp.
This isolates change detection, not the complete GStreamer service lifecycle.
