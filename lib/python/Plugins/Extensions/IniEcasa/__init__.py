#pragma mark - Config
from Components.config import config, ConfigSubsection, ConfigText, \
		ConfigPassword, ConfigLocations, ConfigSet, ConfigNumber, \
		ConfigSelection

from Tools.Directories import resolveFilename, SCOPE_HDD

config.plugins.ecasa = ConfigSubsection()
config.plugins.ecasa.google_username = ConfigText(default="", fixed_size=False)
config.plugins.ecasa.google_password = ConfigPassword(default="")
config.plugins.ecasa.cachedirs = ConfigLocations(default="/tmp/ecasa")
config.plugins.ecasa.cache = ConfigText(default="/tmp/ecasa")
config.plugins.ecasa.user = ConfigText(default='default')
config.plugins.ecasa.searchhistory = ConfigSet(choices = [])
config.plugins.ecasa.userhistory = ConfigSet(choices = [])
config.plugins.ecasa.searchlimit = ConfigNumber(default=30)
config.plugins.ecasa.cachesize = ConfigNumber(default=30)
config.plugins.ecasa.slideshow_interval = ConfigNumber(default=30)
config.plugins.ecasa.flickr_api_key = ConfigText(default="", fixed_size=False)
config.plugins.ecasa.last_backend = ConfigSelection(default='picasa', choices=['picasa', 'flickr'])
