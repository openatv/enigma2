from Screens.Screen import Screen
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigText
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.ActionMap import ActionMap

# for localized messages
from . import _

       
class LastFMConfigScreen(ConfigListScreen,Screen):

    config.plugins.LastFM = ConfigSubsection()
    config.plugins.LastFM.name = ConfigText(default = _("Last.FM"))

    def __init__(self, session, args = 0):
        self.session = session
        Screen.__init__(self, session)
        self.skinName = ["Setup"]
        self.list = [
			getConfigListEntry(_("Show in (needs GUI restart)"), config.plugins.LastFM.menu),
			getConfigListEntry(_("Name (needs GUI restart)"), config.plugins.LastFM.name),
			getConfigListEntry(_("Description"), config.plugins.LastFM.description),
			getConfigListEntry(_("Last.FM Username"), config.plugins.LastFM.username),
			getConfigListEntry(_("Password"), config.plugins.LastFM.password),
			getConfigListEntry(_("Send now playing Audio Tracks"), config.plugins.LastFM.sendSubmissions),
			getConfigListEntry(_("Use LastFM Proxy"), config.plugins.LastFM.useproxy),
			getConfigListEntry(_("LastFM Proxy port"), config.plugins.LastFM.proxyport),
			getConfigListEntry(_("Recommendation level"), config.plugins.LastFM.recommendedlevel),
			getConfigListEntry(_("Show Coverart"), config.plugins.LastFM.showcoverart),
			getConfigListEntry(_("Timeout Statustext (seconds)"), config.plugins.LastFM.timeoutstatustext),
			getConfigListEntry(_("Timeout to select a Tab (seconds)"), config.plugins.LastFM.timeouttabselect),
			getConfigListEntry(_("Interval to refresh Metadata (seconds)"), config.plugins.LastFM.metadatarefreshinterval),
			getConfigListEntry(_("Use Screensaver"), config.plugins.LastFM.sreensaver.use),
			getConfigListEntry(_("Wait before Screensaver (seconds)"), config.plugins.LastFM.sreensaver.wait),
			getConfigListEntry(_("Show Coverart in Screensaver"), config.plugins.LastFM.sreensaver.showcoverart),
			getConfigListEntry(_("Show Coverart Animation in Screensaver"), config.plugins.LastFM.sreensaver.coverartanimation),
			getConfigListEntry(_("Speed for Coverart Animation"), config.plugins.LastFM.sreensaver.coverartspeed),
			getConfigListEntry(_("Interval for Coverart Animation"), config.plugins.LastFM.sreensaver.coverartinterval),
				]
        ConfigListScreen.__init__(self, self.list)
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("OK"))
        self["setupActions"] = ActionMap(["SetupActions"],
        {
            "green": self.save,
            "red": self.cancel,
            "save": self.save,
            "cancel": self.cancel,
            "ok": self.save,
        }, -2)

    def save(self):
        print "saving"

        
        for x in self["config"].list:
            x[1].save()
        self.close(True)

    def cancel(self):
        print "cancel"
        for x in self["config"].list:
            x[1].cancel()
        self.close(False)
