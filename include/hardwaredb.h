/*
Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License

Copyright (c) 2023-2025 OpenATV, jbleyel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
1. Non-Commercial Use: You may not use the Software or any derivative works
   for commercial purposes without obtaining explicit permission from the
   copyright holder.
2. Share Alike: If you distribute or publicly perform the Software or any
   derivative works, you must do so under the same license terms, and you
   must make the source code of any derivative works available to the
   public.
3. Attribution: You must give appropriate credit to the original author(s)
   of the Software by including a prominent notice in your derivative works.
THE SOFTWARE IS PROVIDED "AS IS," WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE,
ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more details about the CC BY-NC-SA 4.0 License, please visit:
https://creativecommons.org/licenses/by-nc-sa/4.0/
*/

#ifndef __hardwaredb_h
#define __hardwaredb_h
#include <string>
#include <unordered_map>

static std::unordered_map<std::string, std::string> HardwareDB{

#ifdef HWDREAMONE
	{"/devices/platform/ff500000.dwc3/xhci-hcd.0.auto/usb1", "USB 2.0 (Back, inner)"},
	{"/devices/platform/ff500000.dwc3/xhci-hcd.0.auto/usb2", "USB 3.0 (Back, outer)"}
#elif HWDREAMTWO
	{"/devices/platform/ff500000.dwc3/xhci-hcd.0.auto/usb1", "USB 2.0 (Back, inner)"},
	{"/devices/platform/ff500000.dwc3/xhci-hcd.0.auto/usb2", "USB 3.0 (Back, outer)"}
#elif HWDM8000
	{"/devices/pci0000:01/0000:01:00.0/host1/target1:0:0/1:0:0:0", "SATA"},
	{"/devices/platform/brcm-ehci.0/usb1/1-1/1-1.1/1-1.1:1.0", "Front USB"},
	{"/devices/platform/brcm-ehci.0/usb1/1-1/1-1.1/1-1.1.", "Front USB"},
	{"/devices/platform/brcm-ehci.0/usb1/1-1/1-1.2/1-1.2:1.0", "Back, upper USB"},
	{"/devices/platform/brcm-ehci.0/usb1/1-1/1-1.2/1-1.2.", "Back, upper USB"},
	{"/devices/platform/brcm-ehci.0/usb1/1-1/1-1.3/1-1.3:1.0", "Back, lower USB"},
	{"/devices/platform/brcm-ehci.0/usb1/1-1/1-1.3/1-1.3.", "Back, lower USB"},
	{"/devices/platform/brcm-ehci-1.1/usb2/2-1/2-1:1.0/", "Internal USB"},
	{"/devices/platform/brcm-ohci-1.1/usb4/4-1/4-1:1.0/", "Internal USB"},
	{"/devices/platform/brcm-ehci.0/usb1/1-1/1-1.4/1-1.4.", "Internal USB"}
#elif HWDM7020HD
	{"/devices/pci0000:01/0000:01:00.0/host0/target0:0:0/0:0:0:0", "SATA"},
	{"/devices/pci0000:01/0000:01:00.0/host1/target1:0:0/1:0:0:0", "eSATA"},
	{"/devices/platform/brcm-ehci-1.1/usb2/2-1/2-1:1.0", "Front USB"},
	{"/devices/platform/brcm-ehci-1.1/usb2/2-1/2-1.", "Front USB"},
	{"/devices/platform/brcm-ehci.0/usb1/1-2/1-2:1.0", "Back, upper USB"},
	{"/devices/platform/brcm-ehci.0/usb1/1-2/1-2.", "Back, upper USB"},
	{"/devices/platform/brcm-ehci.0/usb1/1-1/1-1:1.0", "Back, lower USB"},
	{"/devices/platform/brcm-ehci.0/usb1/1-1/1-1.", "Back, lower USB"}
#elif HWDM7080
	{"/devices/pci0000:00/0000:00:00.0/usb9/9-1/", "Back USB 3.0"},
	{"/devices/pci0000:00/0000:00:00.0/usb9/9-2/", "Front USB 3.0"},
	{"/devices/platform/ehci-brcm.0/", "Back, lower USB"},
	{"/devices/platform/ehci-brcm.1/", "Back, upper USB"},
	{"/devices/platform/ehci-brcm.2/", "Internal USB"},
	{"/devices/platform/ehci-brcm.3/", "Internal USB"},
	{"/devices/platform/ohci-brcm.0/", "Back, lower USB"},
	{"/devices/platform/ohci-brcm.1/", "Back, upper USB"},
	{"/devices/platform/ohci-brcm.2/", "Internal USB"},
	{"/devices/platform/ohci-brcm.3/", "Internal USB"},
	{"/devices/platform/sdhci-brcmstb.0/", "eMMC"},
	{"/devices/platform/sdhci-brcmstb.1/", "SD"},
	{"/devices/platform/strict-ahci.0/ata1/", "SATA FRONT"},
	{"/devices/platform/strict-ahci.0/ata2/", "SATA BACK"}
#elif HWDM820
	{"/devices/platform/ehci-brcm.0/", "Back, lower USB"},
	{"/devices/platform/ehci-brcm.1/", "Back, upper USB"},
	{"/devices/platform/ehci-brcm.2/", "Internal USB"},
	{"/devices/platform/ehci-brcm.3/", "Internal USB"},
	{"/devices/platform/ohci-brcm.0/", "Back, lower USB"},
	{"/devices/platform/ohci-brcm.1/", "Back, upper USB"},
	{"/devices/platform/ohci-brcm.2/", "Internal USB"},
	{"/devices/platform/ohci-brcm.3/", "Internal USB"},
	{"/devices/platform/sdhci-brcmstb.0/", "eMMC"},
	{"/devices/platform/sdhci-brcmstb.1/", "SD"},
	{"/devices/platform/strict-ahci.0/ata1/", "SATA FRONT"},
	{"/devices/platform/strict-ahci.0/ata2/", "SATA BACK"}
#elif HWDM520
	{"/devices/platform/ehci-brcm.0/usb1/1-2/", "Back, outer USB"},
	{"/devices/platform/ohci-brcm.0/usb2/2-2/", "Back, outer USB"},
	{"/devices/platform/ehci-brcm.0/usb1/1-1/", "Back, inner USB"},
	{"/devices/platform/ohci-brcm.0/usb2/2-1/", "Back, inner USB"}
#elif HWDM900 // CHECKED
	{"/devices/platform/brcmstb-ahci.0/ata1/", "SATA"},
	{"/devices/rdb.4/f03e0000.sdhci/mmc_host/mmc0/", "eMMC"},
	{"/devices/rdb.4/f03e0200.sdhci/mmc_host/mmc1/", "SD"},
	{"/devices/rdb.4/f0470600.ohci_v2/usb6/6-0:1.0", "Front USB"},
	{"/devices/rdb.4/f0470300.ehci_v2/usb3/3-0:1.0", "Front USB"},
	{"/devices/rdb.4/f0471000.xhci_v2/usb2/2-0:1.0", "Front USB"},
	{"/devices/rdb.4/f0470300.ehci_v2/usb3/3-1/3-1:1.0", "Front USB"},
	{"/devices/rdb.4/f0470400.ohci_v2/usb5/5-0:1.0", "Back USB"},
	{"/devices/rdb.4/f0470500.ehci_v2/usb4/4-0:1.0", "Back USB"},
	{"/devices/rdb.4/f0470500.ehci_v2/usb4/4-1/4-1:1.0", "Back USB"},
	{"/devices/rdb.4/f0471000.xhci_v2/usb2/2-0:1.0", "Back USB"}
#elif HWDM920 // CHECKED
	{"/devices/platform/brcmstb-ahci.0/ata1/", "SATA"},
	{"/devices/rdb.4/f03e0000.sdhci/mmc_host/mmc0/", "eMMC"},
	{"/devices/rdb.4/f03e0200.sdhci/mmc_host/mmc1/", "SD"},
	{"/devices/rdb.4/f0470600.ohci_v2/usb6/6-0:1.0/port1/", "Front USB"},
	{"/devices/rdb.4/f0470300.ehci_v2/usb3/3-0:1.0/port1/", "Front USB"},
	{"/devices/rdb.4/f0471000.xhci_v2/usb2/2-0:1.0/port1/", "Front USB"},
	{"/devices/rdb.4/f0470300.ehci_v2/usb3/3-1/3-1:1.0", "Front USB"},
	{"/devices/rdb.4/f0470400.ohci_v2/usb5/5-0:1.0/port1/", "Back USB"},
	{"/devices/rdb.4/f0470500.ehci_v2/usb4/4-0:1.0/port1/", "Back USB"},
	{"/devices/rdb.4/f0470500.ehci_v2/usb4/4-1/4-1:1.0", "Back USB"},
	{"/devices/rdb.4/f0471000.xhci_v2/usb2/2-0:1.0/port2/", "Back USB"}
#elif HWDM800SE
	{"/devices/pci0000:01/0000:01:00.0/host0/target0:0:0/0:0:0:0", "SATA"},
	{"/devices/pci0000:01/0000:01:00.0/host1/target1:0:0/1:0:0:0", "eSATA"},
	{"/devices/platform/brcm-ehci.0/usb1/1-2/1-2:1.0", "Upper USB"},
	{"/devices/platform/brcm-ehci.0/usb1/1-1/1-1:1.0", "Lower USB"}
#elif HWDM500HD
	{"/devices/pci0000:01/0000:01:00.0/host1/target1:0:0/1:0:0:0", "eSATA"},
	{"/devices/pci0000:01/0000:01:00.0/host0/target0:0:0/0:0:0:0", "eSATA"}
#elif HWDM800SEV2
	{"/devices/pci0000:01/0000:01:00.0/host0/target0:0:0/0:0:0:0", "SATA"},
	{"/devices/pci0000:01/0000:01:00.0/host1/target1:0:0/1:0:0:0", "eSATA"},
	{"/devices/platform/brcm-ehci.0/usb1/1-2/1-2:1.0", "Upper USB"},
	{"/devices/platform/brcm-ehci.0/usb1/1-1/1-1:1.0", "Lower USB"}
#elif HWDM500HDV2
	{"/devices/pci0000:01/0000:01:00.0/host1/target1:0:0/1:0:0:0", "eSATA"},
	{"/devices/pci0000:01/0000:01:00.0/host0/target0:0:0/0:0:0:0", "eSATA"}
#elif HWDUAL
	{"/devices/platform/soc/f98a0000.xhci/usb3/3-1/3-1:1.0", "Back USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1:1.0", "Front USB"}
#elif HWET7X00		// CHECKED
	{"/devices/platform/ehci-brcm.0/usb1/1-1/1-1:1.0", "Back USB"},
	{"/devices/platform/ehci-brcm.0/usb1/1-2/1-2:1.0", "Front USB"}
#elif HWGBIP4K		// CHECKED
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1.3/1-1.3", "Micro SD"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1.2/1-1.2", "Back, right USB"},
	{"/devices/platform/soc/f98a0000.xhci/usb4/4-1/4-1", "Back, left USB"}
#elif HWGBQUAD4K	// CHECKED
	{"/devices/platform/rdb/f045a000.sata/", "SATA"},
	{"/devices/platform/rdb/f03e0000.sdhci/mmc_host/", "SD"},
	{"/devices/platform/rdb/f0470300.ehci_v2/usb3/3-1/3-1:1.0", "Front USB"},
	{"/devices/platform/rdb/f0470500.ehci_v2/usb4/4-1/4-1.4/4-1.4:1.0", "Back, left USB"},
	{"/devices/platform/rdb/f0470500.ehci_v2/usb4/4-1/4-1.3/4-1.3:1.0", "Back, right USB"},
	{"/devices/platform/rdb/f0471000.xhci_v2/usb2/2-2/2-2.4/2-2.4:1.0", "Back, left USB"},
	{"/devices/platform/rdb/f0471000.xhci_v2/usb2/2-2/2-2.3/2-2.3:1.0", "Back, right USB"},
	{"/devices/platform/rdb/f0470500.ehci_v2/usb4/4-1/4-1.2/4-1.2:1.0", "Back, lower USB"},
	{"/devices/platform/rdb/f0470500.ehci_v2/usb4/4-1/4-1.1/4-1.1:1.0", "Back, upper USB"},
#elif HWGBQUAD4KPRO // CHECKED
	{"/devices/platform/rdb/f045a000.sata/", "SATA"},
	{"/devices/platform/rdb/f03e0000.sdhci/mmc_host/", "SD"},
	{"/devices/platform/rdb/f0470500.ehci_v2/usb4/4-1/4-1.1", "Front USB"},
	{"/devices/platform/rdb/f0471000.xhci_v2/usb2/2-2/2-2.1", "Front USB"},
	{"/devices/platform/rdb/f0470500.ehci_v2/usb4/4-1/4-1.4", "Back, right USB"},
	{"/devices/platform/rdb/f0471000.xhci_v2/usb2/2-2/2-2.4", "Back, right USB"},
	{"/devices/platform/rdb/f0470300.ehci_v2/usb3/3-1/3-1", "Back, left USB"},
	{"/devices/platform/rdb/f0471000.xhci_v2/usb2/2-1/2-1", "Back, left USB"},
	{"/devices/platform/rdb/f0470500.ehci_v2/usb4/4-1/4-1.3", "Back USB-C"},
	{"/devices/platform/rdb/f0471000.xhci_v2/usb2/2-2/2-2.3", "Back USB-C"}
#elif HWGBTRIO4K	// CHECKED
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1.3/1-1.3:1.0", "Micro SD"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1.2/1-1.2:1.0", "Back, right USB"},
	{"/devices/platform/soc/f98a0000.xhci/usb3/3-1/3-1:1.0", "Back, left USB"},
	{"/devices/platform/soc/f98a0000.xhci/usb4/4-1/4-1:1.0", "Back, left USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-2/1-2:1.0", "Front USB"}
#elif HWGBTRIO4KPRO // CHECKED
	{"/devices/platform/soc/f9890000.ehci/usb1/1-2/1-2", "Micro SD"},
	{"/devices/platform/soc/f98a0000.xhci/usb4/4-1/4-1", "Back, left USB"},
	{"/devices/platform/soc/f98a0000.xhci/usb3/3-1/3-1", "Back, left USB"},
	{"/devices/platform/soc/f9880000.ohci/usb2/2-1/2-1", "Back, right USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1", "Back, right USB"}
#elif HWGBUE4K
	{"/devices/platform/rdb/f045a000.sata/ata2/", "SATA"},
	{"/devices/platform/rdb/f0470300.ehci_v2/usb3/3-1/3-1.1/3-1.1:", "Front USB"},
	{"/devices/platform/rdb/f0470500.ehci_v2/usb4/", "Back, left USB"},
	{"/devices/platform/rdb/f0471000.xhci_v2/usb2/2-2/2-2:1.0", "Back, left USB"},
	{"/devices/platform/rdb/f0470300.ehci_v2/usb3/3-1/3-1.2/3-1.2:", "Back, upper USB"},
	{"/devices/platform/rdb/f0470300.ehci_v2/usb3/3-1/3-1.3/3-1.3:", "Back, lower USB"}
#elif HWH7
	{"/devices/platform/rdb/f045a000.sata/ata1/", "SATA"},
	{"/devices/platform/f0470500.ehci/usb2/", "Back USB 3.0"},
	{"/devices/platform/f0470300.ehci/usb1/1-1/1-1.2/", "Back, lower USB"},
	{"/devices/platform/f0470300.ehci/usb1/1-1/1-1.1/", "Back, upper USB"}
#elif HWH9			// CHECKED
	{"/devices/platform/soc/f9820000.himciv200.SD/mmc_host/mmc0/mmc0:0007", "Micro SD"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1:1.0", "Back USB"}
#elif HWH9COMBO		// CHECKED
	{"/devices/platform/soc/f9820000.himciv200.SD/mmc_host/mmc1/mmc1:0007", "Micro SD"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1:1.0", "Back USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-2/1-2.4/1-2.4:1.0", "Front USB"}
#elif HWH9COMBOSE	// CHECKED
	{"/devices/platform/soc/f9900000.hiahci/ata1/host0/target0:0:0/0:0:0:0", "SATA"},
	{"/devices/platform/soc/f9820000.himciv200.SD/mmc_host/mmc1/mmc1", "Micro SD"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1:1.0", "Back USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-2/1-2.4/1-2.4:1.0", "Front USB"}
#elif HWH9SE		// CHECKED
	{"/devices/platform/soc/f9820000.himciv200.SD/mmc_host/mmc1/mmc1", "Micro SD"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1:1.0", "Back USB"}
#elif HWH10			// CHECKED
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1", "Back, left USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-2", "Back, right USB"},
	{"/devices/platform/soc/f9900000.hiahci/ata1/", "SATA"}
#elif HWH11			// CHECKED
	{"/devices/platform/soc/f9820000.himciv200.SD/mmc_host/mmc1/mmc1:1234", "Micro SD"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1:1.0", "Back USB"}
#elif HWH17			// CHECKED
	{"/devices/platform/f0470300.ehci/usb1/", "Front USB"},
	{"/devices/platform/f0471000.xhci/usb6/", "Back USB"},
	{"/devices/platform/f0471000.ohci/usb4/", "Back USB"},
	{"/devices/platform/f0470500.ehci/usb2/", "Back USB"}
#elif HWHD51		// CHECKED
	{"/devices/platform/rdb/f045a000.sata/ata1/", "SATA"},
	{"/devices/platform/f0470300.ehci/usb1/1-1/1-1.2", "Front USB"},
	{"/devices/platform/f0470300.ehci/usb1/1-1/1-1.3", "Back, left USB"},
	{"/devices/platform/f0471000.xhci/usb6/6-2/6-2", "Back, right USB"},
	{"/devices/platform/f0470500.ehci/usb2/2-1/2-1", "Back, right USB"}
#elif HWHD61		// CHECKED
	{"/devices/platform/soc/f9820000.himciv200.SD/mmc_host/mmc1", "Micro SD"},
	{"/devices/platform/soc/f98a0000.xhci/usb3/3-1/3-1", "Front USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1", "Back USB"},
	{"/devices/platform/soc/f9900000.hiahci/ata1/", "SATA"}
#elif HWMULTIBOXPRO // CHECKED
	{"/devices/platform/soc/f98a0000.xhci/usb3", "Back, left USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1", "Back, right USB"},
	{"/devices/platform/soc/f9820000.himciv200.SD/mmc_host/mmc1", "Micro SD"}

#elif HWOSNINO // CHECKED
	{"/devices/platform/ehci-brcm.0/usb1/1-2", "Right, front USB"},
	{"/devices/platform/ehci-brcm.0/usb1/1-1", "Right, back USB"}
#elif HWOSMIO4KPLUS
	{"/devices/platform/rdb/f0b00300.ehci_v2/usb1/1-1/1-1:1.0", "Back USB"},
	{"/devices/platform/rdb/f0b00500.ehci_v2/usb2/2-1/2-1:1.0", "Left USB"}
#elif HWPULSE4K
	{"/devices/platform/soc/f9820000.himciv200.SD/mmc_host/mmc1", "Micro SD"},
	{"/devices/platform/soc/f9900000.hiahci/ata1/host0/target0:0:0/0:0:0:0", "SATA"},
	{"/devices/platform/soc/f98a0000.xhci/usb3/", "Front USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/", "Back USB"}
#elif HWPULSE4KMINI // CHECKED
	{"/devices/platform/soc/f9820000.himciv200.SD/mmc_host/mmc1/", "Micro SD"},
	{"/devices/platform/soc/f9890000.ehci/usb1/", "Back, upper USB"},
	{"/devices/platform/soc/f98a0000.xhci/usb4/", "Back, lower USB"},
	{"/devices/platform/soc/f98a0000.xhci/usb3/", "Back, lower USB"}
#elif HWSF8008M
	{"/devices/platform/soc/f98a0000.xhci/usb3/3-1/3-1:1.0", "Right USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1:1.0", "Right USB"}
#elif HWSF8008
	{"/devices/platform/soc/f98a0000.xhci/usb3/3-1/3-1:1.0", "Right USB"},
	{"/devices/platform/soc/f98a0000.xhci/usb4/4-1/4-1", "Right USB"},
	{"/devices/platform/soc/f98a0000.xhci/usb3/3-1/3-1", "Right USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1.2", "Back USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1.3", "Micro SD"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1.4", "Internal SSD"}
#elif HWSFX6008 // CHECKED
	{"/devices/platform/soc/f98a0000.xhci/usb3/3-1/3-1", "Left USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1", "Back USB"}
#elif HWSX88V2	// CHECKED
	{"/devices/platform/soc/f98a0000.xhci/usb3/3-1/3-1", "Right USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-2/1-2", "Left USB"}
#elif HWSX988	// CHECKED
	{"/devices/platform/soc/f9890000.ehci/usb1/1-2/1-2:1.0", "Right, front USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1:1.0", "Right, back USB"}
#elif HWUSTYM4KPRO
	{"/devices/platform/soc/f98a0000.xhci/usb3/3-1/3-1:1.0", "Right USB"},
	{"/devices/platform/soc/f98a0000.xhci/usb4/4-1/4-1", "Right USB"},
	{"/devices/platform/soc/f98a0000.xhci/usb4/3-1/3-1", "Right USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1.2", "Back USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-1/1-1.3", "Micro SD"}
#elif HWU5		   // eg. Dinobot4k
	{"/devices/platform/soc/f98a0000.xhci/usb3/", "Back USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-2/1-2.3/", "Left, back USB"},
	{"/devices/platform/soc/f9890000.ehci/usb1/1-2/1-2.4/", "Left, front USB"}
#elif HWVUDUO2	   // CHECKED
	{"/devices/platform/strict-ahci.0/ata2/", "SATA"},
	{"/devices/platform/strict-ahci.0/ata1/", "eSATA"},
	{"/devices/platform/ehci-brcm.2/usb3/", "Front USB"},
	{"/devices/platform/ehci-brcm.0/usb1/", "Back, lower USB"},
	{"/devices/platform/ehci-brcm.1/usb2/", "Back, upper USB"}
#elif HWVUDUO4K	   // CHECKED
	{"/devices/platform/rdb/8b0a000.sata/", "SATA"},
	{"/devices/platform/rdb/8b39000.xhci_v2/usb1/1-2/", "Front USB"},
	{"/devices/platform/rdb/8b39000.xhci_v2/usb2/2-2/", "Back, upper USB"},
	{"/devices/platform/rdb/8b39000.xhci_v2/usb2/2-1/", "Back, lower USB"},
	{"/devices/platform/rdb/8b39000.xhci_v2/usb1/1-1/1-1.2/1-1.2:1.0", "Back, upper USB"},
	{"/devices/platform/rdb/8b39000.xhci_v2/usb1/1-1/1-1.1/1-1.1:1.0", "Back, lower USB"}
#elif HWVUDUO4KSE  // CHECKED
	{"/devices/platform/rdb/f045a000.sata/", "SATA"},
	{"/devices/platform/rdb/f0480500.ehci_v2/usb6/", "Front USB"},
	{"/devices/platform/rdb/f0470300.ehci_v2/usb3/3-1/3-1:1.0", "Back, lower USB"},
	{"/devices/platform/rdb/f0470500.ehci_v2/usb4/4-1/4-1:1.0", "Back, upper USB"},
	{"/devices/platform/rdb/f0471000.xhci_v2/usb2/2-2/", "Back, upper USB"},
	{"/devices/platform/rdb/f0471000.xhci_v2/usb2/2-1/", "Back, lower USB"}
#elif HWVUSOLO4K   // CHECKED
	{"/devices/platform/strict-ahci.0/ata1/", "SATA"},
	{"/devices/f0490600.ohci/usb10/", "Front USB"},
	{"/devices/f0480400.ohci/usb7/", "Back, lower USB"},
	{"/devices/f0480600.ohci/usb8/", "Back, upper USB"},
	{"/devices/f0490500.ehci/usb6/6-1/6-1", "Front USB"},
	{"/devices/f0481000.xhci/usb2/2-1/2-1", "Back, lower USB"},
	{"/devices/f0481000.xhci/usb2/2-2/2-2", "Back, upper USB"},
	{"/devices/f0480500.ehci/usb4/4-1/4-1", "Back, upper USB"},
	{"/devices/f0480300.ehci/usb3/3-1/3-1", "Back, lower USB"}
#elif HWVUUNO4K	   // NOT CHECKED
	{"/devices/platform/rdb/f045a000.sata/ata1", "SATA"},
	{"/devices/platform/rdb/f0470300.ehci_v2/usb3/3-1/3-1", "Back, lower USB"},
	{"/devices/platform/rdb/f0471000.xhci_v2/usb2/2-1/2-1", "Back, lower USB"},
	{"/devices/platform/rdb/f0470500.ehci_v2/usb4/4-1/4-1", "Back, upper USB"},
	{"/devices/platform/rdb/f0471000.xhci_v2/usb2/2-2/2-2", "Back, upper USB"}
#elif HWVUUNO4KSE  // CHECKED
	{"/devices/platform/rdb/f045a000.sata/ata1", "SATA"},
	{"/devices/platform/rdb/f0470300.ehci_v2/usb3/3-1/3-1", "Back, lower USB"},
	{"/devices/platform/rdb/f0471000.xhci_v2/usb2/2-1/2-1", "Back, lower USB"},
	{"/devices/platform/rdb/f0470500.ehci_v2/usb4/4-1/4-1", "Back, upper USB"},
	{"/devices/platform/rdb/f0471000.xhci_v2/usb2/2-2/2-2", "Back, upper USB"}
#elif HWVUULTIMO4K // CHECKED
	{"/devices/platform/brcmstb-ahci.0/ata1", "SATA"},
	{"/devices/rdb.1/f0471000.xhci_v2/usb2/2-1/2-1:1.0", "Back, lower USB"},
	{"/devices/rdb.1/f0471000.xhci_v2/usb2/2-2/2-2:1.0", "Back, upper USB"},
	{"/devices/rdb.1/f0470500.ehci_v2/usb4/4-1/4-1:1.0", "Back, upper USB"},
	{"/devices/rdb.1/f0470300.ehci_v2/usb3/3-1/3-1:1.0", "Back, lower USB"},
	{"/devices/rdb.1/f0480500.ehci_v2/usb6/6-1/6-1:1.0", "Front USB"}
#elif HWVUZERO4K   // CHECKED
	{"/devices/platform/rdb/f0b00300.ehci_v2/usb1/1-1/1-1:1.0", "Back USB"},
	{"/devices/platform/rdb/f0b00300.ehci_v2/usb1/1-1/1-2:1.0", "Back USB"}	
#else

#endif

};

#endif
