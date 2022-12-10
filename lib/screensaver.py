# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with Kodi; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html

## Screensaver that displays a slideshow of pictures from the My Pictures Database

# The screensaver uses the picture database created by the plugin.image.mypicsdb2 addon. 
# You can also use Filters created in the plugin.image.mypicsdb2 addon to select which 
# pictures are shown in the slideshow.

import os.path
import sys
import random
import urllib.parse

import xbmc
import xbmcgui
import xbmcaddon

import mypicsdb.MypicsDB  as MypicsDB

ADDON = xbmcaddon.Addon()

SETTINGS_ERROR = ADDON.getLocalizedString(30005)
NO_FILTER_NAME_ERROR = ADDON.getLocalizedString(30006)
BAD_FILTER_NAME_ERROR = ADDON.getLocalizedString(30007)
NO_FILES_MATCH_FILTER = ADDON.getLocalizedString(30008)

def log(msg, level=xbmc.LOGINFO):
        filename = os.path.basename(sys._getframe(1).f_code.co_filename)
        lineno  = str(sys._getframe(1).f_lineno)
        xbmc.log(str("[%s] line %5d in %s >> %s"%(ADDON.getAddonInfo('name'), int(lineno), filename, msg.__str__())), level)

# Formats that can be displayed in a slideshow
PICTURE_FORMATS = ('jpg', 'jpeg', 'tiff', 'gif', 'png', 'bmp', 'mng', 'ico', 'pcx', 'tga')
SINGLE_PICTURE_QUERY =  """ SELECT strPath, strFilename FROM Files """
SINGLE_PICTURE_QUERY += """ WHERE strFilename LIKE '%s' """ 
SINGLE_PICTURE_QUERY += """    OR strFilename LIKE '%s' """
SINGLE_PICTURE_QUERY += """    OR strFilename LIKE '%s' """
SINGLE_PICTURE_QUERY += """    OR strFilename LIKE '%s' """
SINGLE_PICTURE_QUERY += """    OR strFilename LIKE '%s' """
SINGLE_PICTURE_QUERY += """    OR strFilename LIKE '%s' """
SINGLE_PICTURE_QUERY += """    OR strFilename LIKE '%s' """
SINGLE_PICTURE_QUERY += """    OR strFilename LIKE '%s' """
SINGLE_PICTURE_QUERY += """    OR strFilename LIKE '%s' """
SINGLE_PICTURE_QUERY += """    OR strFilename LIKE '%s' """
SINGLE_PICTURE_QUERY += """ ORDER BY RANDOM() LIMIT 1 """ 
SINGLE_PICTURE_QUERY = SINGLE_PICTURE_QUERY % PICTURE_FORMATS
SINGLE_PICTURE_QUERY = SINGLE_PICTURE_QUERY.replace("LIKE '", "LIKE '%")

# Get the Database from the My Pictures Database addon
MPDB = MypicsDB.MyPictureDB()

class Screensaver(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        pass

    def onInit(self):
        # Get the screensaver window id
        self.winid = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        # Init the monitor class to catch onscreensaverdeactivated calls
        self.Monitor = MyMonitor(action = self._exit)
        self.stop = False
        # Get addon settings
        self._get_settings()
        self._get_filtered_pictures()
        # Start the show
        self._start_show()
        
    def _get_settings(self):
        # read addon settings
        self.anim_time = 101000
        self.slideshow_time = ADDON.getSettingInt('time')
        self.slideshow_filter = ADDON.getSettingBool('filter')
        self.slideshow_filtername = ADDON.getSettingString('filtername')
        # Set the image controls from the xml we are going to use
        self.image1 = self.getControl(1)
        self.image2 = self.getControl(2)

    def _get_filtered_pictures(self):
        # If we are going to use a MyPicsDB filter, then get all of the possible pictures we could use to match the filter
        if self.slideshow_filter:
            if self.slideshow_filtername == "":
                # Use filter selected, but no filter name given
                message = 'Notification(' + SETTINGS_ERROR + ', ' + NO_FILTER_NAME_ERROR + ', 15000, DefaultIconError.png)'
                xbmc.executebuiltin(message)
                self.slideshow_filter = False
                log("Filter name was not specified",xbmc.LOGERROR)
            else:
                # Use filter selected, and filter name specified
                # Make sure the specified filter exists
                query = """SELECT pkFilter FROM FilterWizard"""
                query += """ WHERE strFilterName IS '%s'; """ %(self.slideshow_filtername.replace("'","''"))
                filter_ids = self.exec_query(query)
                if len(filter_ids) != 1:
                    # Filter name was not found in the My Pictures Database.
                    message = 'Notification(' + SETTINGS_ERROR + ', ' + BAD_FILTER_NAME_ERROR%(self.slideshow_filtername) + ', 15000, DefaultIconError.png)'
                    xbmc.executebuiltin(message)
                    self.slideshow_filter = False
                    log("Filtername '%s' not found in MyPictures Database" %(self.slideshow_filtername), xbmc.LOGERROR)
                else:
                    # Fliter name found, apply it to get the matching pictures.
                    results = MPDB.filterwizard_get_pics_from_filter(self.slideshow_filtername, 0)
                    # Make sure only displayable pictures are used
                    self.filtered_results = [result for result in results if result[1].lower().endswith(PICTURE_FORMATS)]
                    if len(self.filtered_results) == 0:
                        # No matching pictures found for the filter
                        message = 'Notification(' + SETTINGS_ERROR + ', ' + NO_FILES_MATCH_FILTER%(self.slideshow_filtername) + ', 15000, DefaultIconError.png)'
                        xbmc.executebuiltin(message)
                        self.slideshow_filter = False
                        log("No files match filter '%s'in MyPictures Database" %(self.slideshow_filtername), xbmc.LOGERROR)
                    else:
                        random.shuffle(self.filtered_results)
                        # At the start of the show, use the first random image idFile
                        self.filtered_results_index = 0

    def _start_show(self):
        # start with image 1
        current_image_control = self.image1
        order = [1,2]
        timetowait = self.slideshow_time * 1000
        # loop until onScreensaverDeactivated is called
        while (not self.Monitor.abortRequested()) and (not self.stop):
            # Get the next picture
            img_name = self._get_item()
            current_image_control.setImage(img_name, False)
            self._set_prop('Fade%d' % order[0], '0')
            self._set_prop('Fade%d' % order[1], '1')
            # define next image
            if current_image_control == self.image1:
                current_image_control = self.image2
                order = [2,1]
            else:
                current_image_control = self.image1
                order = [1,2]

            # display the image for the specified amount of time
            count = timetowait
            while (not self.Monitor.abortRequested()) and (not self.stop) and count > 0:
                count -= 1000
                xbmc.sleep(1000)
            # break out of the for loop if onScreensaverDeactivated is called
            if  self.stop or self.Monitor.abortRequested():
                break

    def _get_item(self, update=False):
        if self.slideshow_filter:
            # Using a filter
            # Use the next picture that matched the filter
            result = self.filtered_results[self.filtered_results_index]
            # Next time choose the next matching picture
            self.filtered_results_index += 1
            if self.filtered_results_index == len(self.filtered_results):
                # All of the pictures have been used, so start over with a new list of all of the pictures
                random.shuffle(self.filtered_results)
                self.filtered_results_index = 0
        else:
            # Not using a filter
            result_list = self.exec_query(SINGLE_PICTURE_QUERY)
            result = result_list[0]
        (folder, file) = result
        return os.path.join(folder, file)

    # Utility functions
    def exec_query(self,query):
        return MPDB.cur.request(query)

    def _set_prop(self, name, value):
        self.winid.setProperty('SlideView.%s' % name, value)

    def _clear_prop(self, name):
        self.winid.clearProperty('SlideView.%s' % name)

    def _exit(self):
        # exit when onScreensaverDeactivated gets called
        self.stop = True
        # clear our properties on exit
        self._clear_prop('Fade1')
        self._clear_prop('Fade2')
        MPDB.cur.close()
        self.close()

# Notify when screensaver is to stop
class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        self.action = kwargs['action']

    def onScreensaverDeactivated(self):
        self.action()

    def onDPMSActivated(self):
        self.action()
