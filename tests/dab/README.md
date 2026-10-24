# DAB PTY host checks

Run from the Enigma2 checkout:

```sh
python3 tests/dab/test_pty_ui.py
g++ -std=c++17 -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer \
  -D__lib_service_dabdebug_h '-DeDABDebug(...)=((void)0)' -I. \
  tests/dab/test_pty.cpp lib/service/dabdecoder.cpp \
  lib/service/dabpaddecoder.cpp lib/service/dabpadtools.cpp \
  lib/service/dabmotmanager.cpp lib/service/dabpacketdecoder.cpp \
  -o /tmp/test-dab-pty
/tmp/test-dab-pty
```

Only receiver logging is disabled; the production FIC, ETI, PAD and packet
decoder implementations are compiled. The UI tests import the real ServiceInfo,
Converter, Element cache and DAB formatting helper with receiver-only imports
stubbed. They cover late PTY/table arrival, changes, unavailable/reserved values,
service end, non-DAB services, translation on access and independence from genre.

Optional ERT replay: `/tmp/test-dab-pty /path/to/ert.eti`.
The capture is not distributed with these tests. Its SHA-256 is
`923acf1bf43dabf0e284624726db81e93bab98b12159291d478179ea36874814`.
Expected: 7,487 ETI-NI frames per service, 14 PTYs, table 1, Greek language and
zero CRC errors. Receiver/image-build tests remain separate from host checks.

The new metadata fields are numeric `sDABPTY` (FIG 0/17) and `sDABPTYTable`
(FIG 0/9 International Table Identifier). Both use -1 for unavailable.
`ServiceInfo` accepts `DABPTY`; Tools.DAB translates codes from tables 12/13.
No category is displayed for absent/unknown tables, PTY zero or reserved codes.
`sTagGenre` and the `DABGenre` converter retain their existing behavior.
