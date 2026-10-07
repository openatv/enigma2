%{
#include <lib/driver/inputdevicemanager.h>
%}

%ignore eInputDeviceManager::deviceListChanged;
%ignore eInputDeviceManager::deviceStateChanged;
%ignore eInputDeviceManager::unboundRemoteKeyPressed;
%ignore eInputDeviceManager::irKeyCount;
%ignore eInputDeviceManager::dfuEvent;
%ignore eInputDeviceManager::dfuProgress;
%ignore eInputDeviceManager::batteryLow;

%ignore eInputDeviceManager::eInputDeviceManager;
%ignore eInputDeviceManager::~eInputDeviceManager;
%ignore eInputDeviceManager::getAvailableDevicesRaw;
%ignore eInputDeviceManager::getConnectedDevicesRaw;

%include <lib/driver/inputdevicemanager.h>

%extend eInputDeviceManager {
PyObject *getAvailableDevices()
{
	std::vector<eManagedInputDevice*> devices = self->getAvailableDevicesRaw();
	PyObject *list = PyList_New(devices.size());
	for (size_t i = 0; i < devices.size(); ++i)
	{
		PyObject *obj = SWIG_NewPointerObj(SWIG_as_voidptr(devices[i]), SWIGTYPE_p_eManagedInputDevice, 0);
		PyList_SET_ITEM(list, i, obj);
	}
	return list;
}

PyObject *getConnectedDevices()
{
	std::vector<eManagedInputDevice*> devices = self->getConnectedDevicesRaw();
	PyObject *list = PyList_New(devices.size());
	for (size_t i = 0; i < devices.size(); ++i)
	{
		PyObject *obj = SWIG_NewPointerObj(SWIG_as_voidptr(devices[i]), SWIGTYPE_p_eManagedInputDevice, 0);
		PyList_SET_ITEM(list, i, obj);
	}
	return list;
}

PyObject *getDeviceListChanged()
{
	return self->deviceListChanged.get();
}

PyObject *getDeviceStateChanged()
{
	return self->deviceStateChanged.get();
}

PyObject *getUnboundRemoteKeyPressed()
{
	return self->unboundRemoteKeyPressed.get();
}

PyObject *getIrKeyCount()
{
	return self->irKeyCount.get();
}

PyObject *getDfuEvent()
{
	return self->dfuEvent.get();
}

PyObject *getDfuProgress()
{
	return self->dfuProgress.get();
}

PyObject *getBatteryLow()
{
	return self->batteryLow.get();
}
};

%pythoncode %{
# DreamOS exposes eManagedInputDevicePtr. The OpenATV backend returns
# eManagedInputDevice instances directly, so keep the DreamOS type name as
# a compatibility alias for plugin isinstance() checks.
eManagedInputDevicePtr = eManagedInputDevice

eInputDeviceManager.deviceListChanged = property(lambda self: self.getDeviceListChanged())
eInputDeviceManager.deviceStateChanged = property(lambda self: self.getDeviceStateChanged())
eInputDeviceManager.unboundRemoteKeyPressed = property(lambda self: self.getUnboundRemoteKeyPressed())
eInputDeviceManager.irKeyCount = property(lambda self: self.getIrKeyCount())
eInputDeviceManager.dfuEvent = property(lambda self: self.getDfuEvent())
eInputDeviceManager.dfuProgress = property(lambda self: self.getDfuProgress())
eInputDeviceManager.batteryLow = property(lambda self: self.getBatteryLow())
%}
