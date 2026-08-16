
# ===========================================================================
# ServiceAction – Python wrapper around eServiceActionClient (C++)
#
# Keeps the same public API as before but delegates all I/O to the C++
# singleton which uses eSocketNotifier (non-blocking, no Twisted thread).
#
# Protocol sent to socketdaemon:
#   "ACTION <id> <TYPE> [<data>]\n"
# Response:
#   "DONE <id> <exitcode>\n"  or  "ERROR <id> <exitcode>\n"
#
# callback(exitCode: int) is called exactly once (on reply or timeout).
# exitCode == 0  → success,  exitCode != 0  → failure/timeout.
# ===========================================================================
from enigma import eServiceActionClient as _C


class ServiceAction:
    """Thin Python wrapper around eServiceActionClient.

    Usage is identical to the old Twisted-based version – the callback
    receives one int: the daemon's shell exit code (0 = success).

    Instance methods (restart/start/stop) use self.serviceName.
    Class methods (ifup, ifdown, …) create and return a new instance.
    """

    _cbs: dict[int, object] = {}
    _hooked: bool = False

    def __init__(self, serviceName: str):
        self.serviceName = serviceName
        ServiceAction._ensure_hooked()

    @classmethod
    def _ensure_hooked(cls) -> None:
        if not cls._hooked:
            _C.getInstance().actionResult.get().append(cls._on_result)
            cls._hooked = True

    @classmethod
    def _on_result(cls, reqId: int, exitCode: int) -> None:
        print(f"[ServiceAction] DEBUG _on_result: reqId={reqId} exitCode={exitCode} hasCallback={reqId in cls._cbs}")
        cb = cls._cbs.pop(reqId, None)
        if cb and callable(cb):
            cb(exitCode)

    @classmethod
    def _dispatch(cls, action: str, data: str, callback, timeout: int) -> int:
        cls._ensure_hooked()
        reqId = int(_C.getInstance().sendAction(action, data, timeout))
        print(f"[ServiceAction] DEBUG _dispatch: action={action} data={data!r} reqId={reqId} timeout={timeout}")
        if callback and callable(callback):
            cls._cbs[reqId] = callback
        return reqId

    # ---- instance methods ------------------------------------------------

    def restart(self, callback, timeout: int = 15000) -> None:
        """RESTART,<serviceName> → callback(exitCode)"""
        ServiceAction._dispatch("RESTART", self.serviceName, callback, timeout)

    def start(self, callback, timeout: int = 15000) -> None:
        """START,<serviceName> → callback(exitCode)"""
        ServiceAction._dispatch("START", self.serviceName, callback, timeout)

    def stop(self, callback, timeout: int = 15000) -> None:
        """STOP,<serviceName> → callback(exitCode)"""
        ServiceAction._dispatch("STOP", self.serviceName, callback, timeout)

    # ---- class-method factories ------------------------------------------

    @classmethod
    def netrestart(cls, callback, iface: str = "", timeout: int = 15000) -> "ServiceAction":
        """NETRESTART or NETRESTART,<iface> → callback(exitCode)"""
        data = iface if (iface and iface != "all") else ""
        cls._dispatch("NETRESTART", data, callback, timeout)
        obj = cls.__new__(cls)
        obj.serviceName = data
        return obj

    @classmethod
    def ifup(cls, iface: str, callback, timeout: int = 15000) -> "ServiceAction":
        """IFUP,<iface> → /sbin/ifup <iface> → callback(exitCode)"""
        cls._dispatch("IFUP", iface, callback, timeout)
        return cls(iface)

    @classmethod
    def ifdown(cls, ifaces: "str | list[str]", callback, timeout: int = 15000) -> "ServiceAction":
        """IFDOWN,<iface[,iface…]> → /sbin/ifdown for each → callback(exitCode)"""
        data = ",".join(ifaces) if isinstance(ifaces, list) else ifaces
        cls._dispatch("IFDOWN", data, callback, timeout)
        return cls(data)

    @classmethod
    def wlanActivate(cls, iface: str, callback, networkId: "int | None" = None, timeout: int = 30000) -> "ServiceAction":
        """WLANUP,<iface>[,<networkId>] → wlanactivator start <iface> [<networkId>] → callback(exitCode)

        networkId pins wpa_supplicant to exactly that one saved network
        instead of letting it auto-pick/roam among every enabled network in
        wpa_supplicant.conf."""
        data = f"{iface},{networkId}" if networkId is not None else iface
        cls._dispatch("WLANUP", data, callback, timeout)
        return cls(iface)

    @classmethod
    def wlanDeactivate(cls, iface: str, callback, timeout: int = 15000) -> "ServiceAction":
        """WLANDOWN,<iface> → wlanactivator stop <iface> → callback(exitCode)"""
        cls._dispatch("WLANDOWN", iface, callback, timeout)
        return cls(iface)

    @classmethod
    def switchSoftcam(cls, camName: str, callback, timeout: int = 15000) -> "ServiceAction":
        """SWITCH_SOFTCAM,<camName> → callback(exitCode)"""
        cls._dispatch("SWITCH_SOFTCAM", camName, callback, timeout)
        return cls(camName)

    @classmethod
    def switchCardserver(cls, serverName: str, callback, timeout: int = 15000) -> "ServiceAction":
        """SWITCH_CARDSERVER,<serverName> → callback(exitCode)"""
        cls._dispatch("SWITCH_CARDSERVER", serverName, callback, timeout)
        return cls(serverName)

    @classmethod
    def ping(cls, iface: str, host: str, callback, timeout: int = 3000) -> "ServiceAction":
        """PING,<iface>,<host> → one ICMP echo bound to iface → callback(exitCode)"""
        cls._dispatch("PING", f"{iface},{host}", callback, timeout)
        obj = cls.__new__(cls)
        obj.serviceName = host
        return obj

    @classmethod
    def resolve(cls, host: str, callback, timeout: int = 3000) -> "ServiceAction":
        """RESOLVE,<host> → resolve host via getaddrinfo → callback(exitCode)"""
        cls._dispatch("RESOLVE", host, callback, timeout)
        obj = cls.__new__(cls)
        obj.serviceName = host
        return obj

    @classmethod
    def netscan(cls, cidr: str, ports: "list[int]", callback, timeout: int = 10000) -> "ServiceAction":
        """NETSCAN,<cidr>,<port>[,<port>…] → active TCP connect-scan of <cidr>
        (max /24), writes /var/run/netscan → callback(exitCode)."""
        data = cidr + "".join(f",{port}" for port in ports)
        cls._dispatch("NETSCAN", data, callback, timeout)
        obj = cls.__new__(cls)
        obj.serviceName = cidr
        return obj
