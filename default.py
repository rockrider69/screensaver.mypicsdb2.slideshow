import xbmcaddon

from lib import screensaver

ADDON = xbmcaddon.Addon()
CWD = ADDON.getAddonInfo('path')
ADDONVERSION = ADDON.getAddonInfo('version')

if __name__ == '__main__':
    screensaver.log('script version %s started' % ADDONVERSION)
    screensaver_window = screensaver.Screensaver('screensaver.mypicsdb2.slideshow.xml', CWD, 'default')
    screensaver_window.doModal()
    del screensaver_window
screensaver.log('script stopped')
