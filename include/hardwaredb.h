#ifndef __hardwaredb_h
#define __hardwaredb_h
#include <string>
#include <unordered_map>

static std::unordered_map<std::string,std::string> HardwareDB {

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
#elif HWDM900
	{"/devices/platform/brcmstb-ahci.0/ata1/", "SATA"},
	{"/devices/rdb.4/f03e0000.sdhci/mmc_host/mmc0/", "eMMC"},
	{"/devices/rdb.4/f03e0200.sdhci/mmc_host/mmc1/", "SD"},
	{"/devices/rdb.4/f0470600.ohci_v2/usb6/6-0:1.0/port1/", "Front USB"},
	{"/devices/rdb.4/f0470300.ehci_v2/usb3/3-0:1.0/port1/", "Front USB"},
	{"/devices/rdb.4/f0471000.xhci_v2/usb2/2-0:1.0/port1/", "Front USB"},
	{"/devices/rdb.4/f0470400.ohci_v2/usb5/5-0:1.0/port1/", "Back USB"},
	{"/devices/rdb.4/f0470500.ehci_v2/usb4/4-0:1.0/port1/", "Back USB"},
	{"/devices/rdb.4/f0471000.xhci_v2/usb2/2-0:1.0/port2/", "Back USB"}
#elif HWDM920
	{"/devices/platform/brcmstb-ahci.0/ata1/", "SATA"},
	{"/devices/rdb.4/f03e0000.sdhci/mmc_host/mmc0/", "eMMC"},
	{"/devices/rdb.4/f03e0200.sdhci/mmc_host/mmc1/", "SD"},
	{"/devices/rdb.4/f0470600.ohci_v2/usb6/6-0:1.0/port1/", "Front USB"},
	{"/devices/rdb.4/f0470300.ehci_v2/usb3/3-0:1.0/port1/", "Front USB"},
	{"/devices/rdb.4/f0471000.xhci_v2/usb2/2-0:1.0/port1/", "Front USB"},
	{"/devices/rdb.4/f0470400.ohci_v2/usb5/5-0:1.0/port1/", "Back USB"},
	{"/devices/rdb.4/f0470500.ehci_v2/usb4/4-0:1.0/port1/", "Back USB"},
	{"/devices/rdb.4/f0471000.xhci_v2/usb2/2-0:1.0/port2/", "Back USB"}
#elif HWDM800SE
	{"/devices/pci0000:01/0000:01:00.0/host0/target0:0:0/0:0:0:0", "SATA"},
	{"/devices/pci0000:01/0000:01:00.0/host1/target1:0:0/1:0:0:0", "eSATA"}
	{"/devices/platform/brcm-ehci.0/usb1/1-2/1-2:1.0", "Upper USB"},
	{"/devices/platform/brcm-ehci.0/usb1/1-1/1-1:1.0", "Lower USB"}
#elif HWDM500HD
	{"/devices/pci0000:01/0000:01:00.0/host1/target1:0:0/1:0:0:0", "eSATA"},
	{"/devices/pci0000:01/0000:01:00.0/host0/target0:0:0/0:0:0:0", "eSATA"}
#elif HWDM800SEV2
	{"/devices/pci0000:01/0000:01:00.0/host0/target0:0:0/0:0:0:0", "SATA"},
	{"/devices/pci0000:01/0000:01:00.0/host1/target1:0:0/1:0:0:0", "eSATA"}
	{"/devices/platform/brcm-ehci.0/usb1/1-2/1-2:1.0", "Upper USB"},
	{"/devices/platform/brcm-ehci.0/usb1/1-1/1-1:1.0", "Lower USB"}
#elif HWDM500HDV2
	{"/devices/pci0000:01/0000:01:00.0/host1/target1:0:0/1:0:0:0", "eSATA"},
	{"/devices/pci0000:01/0000:01:00.0/host0/target0:0:0/0:0:0:0", "eSATA"}
#else
#endif

};

#endif
