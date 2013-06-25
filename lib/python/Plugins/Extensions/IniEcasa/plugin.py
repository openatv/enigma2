from __future__ import print_function

#pragma mark - Plugin

def main(session, *args, **kwargs):
	import EcasaGui
	session.open(EcasaGui.EcasaOverview)

def Plugins(**kwargs):
	from Plugins.Plugin import PluginDescriptor
	return [
		#PluginDescriptor(
		#	name="Flickr",
		#	description=_("Flickr client"),
		#	where=PluginDescriptor.WHERE_PLUGINMENU,
		#	fnc=main,
		#	needsRestart=False,
		#),
	]

if __name__ == '__main__':
	import sys
	import PicasaApi
	if len(sys.argv) > 2:
		un = sys.argv[1]
		pw = sys.argv[2]
	else:
		un = pw = None
		print("Not using authentication...")
	api = PicasaApi.PicasaApi(un, pw)
	try:
		l = api.getAlbums()
	except Exception as e:
		# NOTE: assumes 403 and that the following calls would also not succeed
		print("Encountered exception:", e)
	else:
		print("List of Albums:", l)
		if l:
			l = api.getAlbum(l[0][2])
			print("Pictures in first album:", l)
			print("Thumbnail of first picture could be found under:", l[0].media.thumbnail[0].url)
			print("Picture should be:", l[0].media.content[0].url)
	l = api.getFeatured()
	print("Featured Pictures:", l)
