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
# The values of some image tags are set in Window properties. There is an option
# to display the values overlayed on the images. The values displayed are
# Headline, Caption, Location, Date and Time, and Folder and File name.

import os.path
import sys
import random
import urllib.parse
import time

import xbmc
import xbmcgui
import xbmcaddon

import mypicsdb.MypicsDB  as MypicsDB

ADDON = xbmcaddon.Addon()

SETTINGS_ERROR = ADDON.getLocalizedString(30006)
NO_FILTER_NAME_ERROR = ADDON.getLocalizedString(30007)
BAD_FILTER_NAME_ERROR = ADDON.getLocalizedString(30008)
NO_FILES_MATCH_FILTER = ADDON.getLocalizedString(30009)

def log(msg, level=xbmc.LOGINFO):
        filename = os.path.basename(sys._getframe(1).f_code.co_filename)
        lineno  = str(sys._getframe(1).f_lineno)
        xbmc.log(str("[%s] line %5d in %s >> %s"%(ADDON.getAddonInfo('name'), int(lineno), filename, msg.__str__())), level)

DB_BACKEND = xbmcaddon.Addon('plugin.image.mypicsdb2').getSetting('db_backend').lower()
# The random function is different in mysql and sqlite
DB_RANDOM = {"mysql" :"RAND()","sqlite":"RANDOM()"}
# DateTimes are stored and retreived differently between mysql and sqlite.
IMGDATE =     {"mysql" :"DATE_FORMAT(ImageDateTime,'%Y-%m-%d')", 
               "sqlite":"SUBSTR(ImageDateTime, 0, 11)"}
IMGDATETIME = {"mysql" :"DATE_FORMAT(ImageDateTime,'%Y-%m-%d %T')", 
               "sqlite":"ImageDateTime"}

# Formats that can be displayed in a slideshow
PICTURE_FORMATS = ('jpg', 'jpeg', 'tiff', 'gif', 'png', 'bmp', 'mng', 'ico', 'pcx', 'tga')
SINGLE_PICTURE_QUERY =  " SELECT strPath, strFilename FROM Files "
SINGLE_PICTURE_QUERY += " WHERE strFilename LIKE '%s' " 
SINGLE_PICTURE_QUERY += "    OR strFilename LIKE '%s' "
SINGLE_PICTURE_QUERY += "    OR strFilename LIKE '%s' "
SINGLE_PICTURE_QUERY += "    OR strFilename LIKE '%s' "
SINGLE_PICTURE_QUERY += "    OR strFilename LIKE '%s' "
SINGLE_PICTURE_QUERY += "    OR strFilename LIKE '%s' "
SINGLE_PICTURE_QUERY += "    OR strFilename LIKE '%s' "
SINGLE_PICTURE_QUERY += "    OR strFilename LIKE '%s' "
SINGLE_PICTURE_QUERY += "    OR strFilename LIKE '%s' "
SINGLE_PICTURE_QUERY += "    OR strFilename LIKE '%s' "
SINGLE_PICTURE_QUERY += " ORDER BY " + DB_RANDOM[DB_BACKEND] + " LIMIT 1 " 
SINGLE_PICTURE_QUERY = SINGLE_PICTURE_QUERY % PICTURE_FORMATS
SINGLE_PICTURE_QUERY = SINGLE_PICTURE_QUERY.replace("LIKE '", "LIKE '%")    

# Get the Database from the My Pictures Database addon
MPDB = MypicsDB.MyPictureDB()

class Screensaver(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        pass

    def onInit(self):
        self.db_backend = xbmcaddon.Addon('plugin.image.mypicsdb2').getSetting('db_backend').lower()
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
        self.slideshow_time = ADDON.getSettingInt('time')
        self.slideshow_filter = ADDON.getSettingBool('filter')
        self.slideshow_filtername = ADDON.getSettingString('filtername')
        self.slideshow_showinfo = ADDON.getSettingBool('tags')
        # Set the image controls from the xml we are going to use
        self.image1 = self.getControl(1)
        self.image2 = self.getControl(2)
        # Get MyPicsDB tagids for the information that can be displayed for each slide
        _query = " Select idTagType FROM TagTypes WHERE TagType = 'Headline'; "
        _ids = self._exec_query(_query)
        self.headline_tagid = _ids[0][0]
        _query = " Select idTagType FROM TagTypes WHERE TagType = 'Caption/abstract'; "
        _ids = self._exec_query(_query)
        self.caption_tagid = _ids[0][0]
        _query = " Select idTagType FROM TagTypes WHERE TagType = 'Sub-location'; "
        _ids = self._exec_query(_query)
        self.sublocation_tagid = _ids[0][0]
        _query = " Select idTagType FROM TagTypes WHERE TagType = 'City'; "
        _ids = self._exec_query(_query)
        self.city_tagid= _ids[0][0]
        _query = " Select idTagType FROM TagTypes WHERE TagType = 'Province/state'; "
        _ids = self._exec_query(_query)
        self.state_tagid= _ids[0][0]
        _query = " Select idTagType FROM TagTypes WHERE TagType = 'Country/primary location name'; "
        _ids = self._exec_query(_query)
        self.country_tagid= _ids[0][0]

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
                query = "Select pkFilter FROM FilterWizard"
                query += " WHERE strFilterName = '%s'; " %(self.slideshow_filtername.replace("'","''"))
                filter_ids = self._exec_query(query)
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
            picture = self._get_item()
            img_name = os.path.join(picture[0], picture[1])
            current_image_control.setImage(img_name, False)
            xbmc.sleep(1000)
            self._set_prop('Fade%d' % order[0], '0')
            self._set_prop('Fade%d' % order[1], '1')
            if (self.slideshow_showinfo):
                self._set_info_fields(picture)
            # define next image
            if current_image_control == self.image1:
                current_image_control = self.image2
                order = [2,1]
            else:
                current_image_control = self.image1
                order = [1,2]

            # display the image for the specified amount of time
            count = timetowait - 1000
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
            result_list = self._exec_query(SINGLE_PICTURE_QUERY)
            result = result_list[0]
        return result

    def _set_info_fields(self, picture):
        self._clear_prop('Headline')
        self._clear_prop('Caption')
        self._clear_prop('Sublocation')
        self._clear_prop('City')
        self._clear_prop('State')
        self._clear_prop('Country')
        self._clear_prop('Date')
        self._clear_prop('Time')
        # Get info to set in window properties
        (folder,file) = picture
        self._set_prop('Folder',folder)
        self._set_prop('File',file)
        query = " Select idFile, " + IMGDATETIME[self.db_backend]+ " FROM Files WHERE strPath = '%s' AND strFilename = '%s'; " \
                %(folder.replace("'","''"), file.replace("'","''"))
        file_info  = self._exec_query(query)
        if len(file_info) > 0:
            self._set_prop('Date',time.strftime('%A %B %e, %Y',time.strptime(file_info[0][1], '%Y-%m-%d %H:%M:%S')))
            self._set_prop('Time',time.strftime('%I:%M:%S %p',time.strptime(file_info[0][1], '%Y-%m-%d %H:%M:%S')))
            image_id=file_info[0][0]
            # Get all of the tags that are on this image
            query = " Select idTagContent FROM TagsInFiles WHERE idFile = '%s'; " %(image_id)
            content_ids = self._exec_query(query)
            for content_id in content_ids:
                # Go through each of the tags, and store the ones of interest
                query = " Select idTagtype, TagContent FROM TagContents WHERE idTagContent = '%s'; " %(content_id[0])
                tags =  self._exec_query(query)
                tag_id = tags[0][0]
                tag_value = tags[0][1]
                if tag_id == self.headline_tagid:
                    self._set_prop('Headline',tag_value)
                elif tag_id == self.caption_tagid:
                    self._set_prop('Caption',tag_value)
                elif tag_id == self.sublocation_tagid:
                    self._set_prop('Sublocation',tag_value)
                elif tag_id == self.city_tagid:
                    self._set_prop('City',tag_value)
                elif tag_id == self.state_tagid:
                    self._set_prop('State',tag_value)
                elif tag_id == self.country_tagid:
                    self._set_prop('Country',tag_value)

    # Utility functions
    def _exec_query(self,query):
        return MPDB.cur.request(query)

    def _set_prop(self, name, value):
        self.winid.setProperty('Screensaver.%s' % name, value)

    def _clear_prop(self, name):
        self.winid.clearProperty('Screensaver.%s' % name)

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
