# DAB scan frontend type test

The scan-type test loads the actual converter/source methods with application
imports isolated; it checks unchanged values 0-3, DAB value 4, unknown value -1
and retention of DAB type across frontend-mask updates:

```sh
python3 tests/dab/test_scan_type.py
```

The default ServiceScan skin adds the existing icons/ico_dab-plus.png for
ValueRange 4,4. Custom ServiceScan screens must provide their own widget for
that range. A visual receiver test is still required.
