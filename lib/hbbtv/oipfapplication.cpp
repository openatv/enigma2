#include <lib/hbbtv/oipfapplication.h>

#include <map>
#include <stdio.h>

static std::map<std::string, eOipfApplication> s_oipfApplications;

// The default constructor creates an invalid application object.
eOipfApplication::eOipfApplication()
	: m_valid(false),
	  m_organisationId(0),
	  m_applicationId(0),
	  m_applicationProfile(0),
	  m_applicationControlCode(CONTROL_CODE_DISABLED),
	  m_serviceBoundFlag(0),
	  m_visibility(VISIBILITY_NOT_VISIBLE_ALL),
	  m_applicationPriority(0),
	  m_usageType(0)
{
}

eOipfApplication::eOipfApplication(const std::string &id, const std::string &name, const std::string &urlBase, const std::string &initialPath, int controlCode, int usageType, int profileCode, uint32_t organisationId, uint16_t applicationId)
	: m_valid(true),
	  m_organisationId(organisationId),
	  m_applicationId(applicationId),
	  m_applicationProfile(profileCode),
	  m_applicationControlCode(controlCode < 0 ? -controlCode : controlCode),
	  m_serviceBoundFlag(1),
	  m_visibility(VISIBILITY_VISIBLE_ALL),
	  m_applicationPriority(0),
	  m_usageType(usageType),
	  m_id(id),
	  m_applicationName(name),
	  m_initialPath(initialPath),
	  m_urlBase(urlBase)
{
}

eOipfApplication::~eOipfApplication()
{
}

eOipfApplication eOipfApplication::getById(const std::string &id)
{
	std::map<std::string, eOipfApplication>::const_iterator it = s_oipfApplications.find(id);
	if (it != s_oipfApplications.end())
		return it->second;
	return eOipfApplication();
}

void eOipfApplication::clearRegistry()
{
	s_oipfApplications.clear();
}

void eOipfApplication::registerApplication(const eOipfApplication &application)
{
	if (!application.isValid())
		return;

	char decimalId[48];
	char hexId[48];
	snprintf(decimalId, sizeof(decimalId), "%u:%u", (unsigned int)application.getOrganisationId(), (unsigned int)application.getApplicationId());
	snprintf(hexId, sizeof(hexId), "%08x:%04x", (unsigned int)application.getOrganisationId(), (unsigned int)application.getApplicationId());
	const std::string aliases[] = {application.getId(), std::to_string(application.getApplicationId()), decimalId, hexId};
	for (const std::string &alias : aliases)
	{
		auto entry = s_oipfApplications.emplace(alias, application);
		// Keep legacy IDs only while they identify exactly one application.
		// An invalid entry remains ambiguous until the next AIT clears the registry.
		if (!entry.second && entry.first->second.getId() != application.getId())
			entry.first->second = eOipfApplication();
	}
}

const std::string eOipfApplication::getUrl() const
{
	if (m_initialPath.empty())
		return m_urlBase;
	if (m_urlBase.empty())
		return m_initialPath;
	if (m_urlBase[m_urlBase.size() - 1] == '/' || m_initialPath[0] == '/')
		return m_urlBase + m_initialPath;
	return m_urlBase + "/" + m_initialPath;
}
