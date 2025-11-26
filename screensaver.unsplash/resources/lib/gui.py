#   Copyright (C) 2025 Lunatixz, embql
#
#
# This file is part of Unsplash Photo ScreenSaver.
#
# Unsplash Photo ScreenSaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Unsplash Photo ScreenSaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Unsplash Photo ScreenSaver.  If not, see <http://www.gnu.org/licenses/>.

import json, os, random, datetime, itertools, requests, logging

from six.moves import urllib # type: ignore
from kodi_six import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode # type: ignore

# Plugin Info
ADDON_ID = 'screensaver.unsplash'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON = REAL_SETTINGS.getAddonInfo('icon')
FANART = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE = REAL_SETTINGS.getLocalizedString
SHOW_NOTIFICATION = REAL_SETTINGS.getSettingBool("ShowNotification")
FETCH_SIZE = int(REAL_SETTINGS.getSetting("FetchSize") or 30)
KODI_MONITOR = xbmc.Monitor()

API_KEY = REAL_SETTINGS.getSetting("APIKey")
USER = REAL_SETTINGS.getSetting("User").replace('@','')
COLLECTION = REAL_SETTINGS.getSetting("Collection")
# Read keywords from settings
ENABLE_KEYS = REAL_SETTINGS.getSetting("Enable_Keys") == 'true'
KEYWORDS = "" if not ENABLE_KEYS else urllib.parse.quote(REAL_SETTINGS.getSetting("Keywords"))
KEYWORDS_LIST = [kw.strip() for kw in KEYWORDS.split(",") if kw.strip()]

keywords_index = 0

def build_image_url():
    global keywords_index
    if KEYWORDS_LIST:
        current_keyword = urllib.parse.quote(KEYWORDS_LIST[keywords_index])
        photo_type = int(REAL_SETTINGS.getSetting("PhotoType"))

        # Random endpoints
        if photo_type in [2, 3]:
            url = f"https://api.unsplash.com/photos/random?query={current_keyword}&client_id={API_KEY}"
        # Search endpoint
        elif photo_type == 7:
            url = f"https://api.unsplash.com/search/photos?query={current_keyword}&page=1&per_page={FETCH_SIZE}&client_id={API_KEY}"
        else:
            url = IMAGE_URL
    else:
        url = IMAGE_URL
    return url

def next_keyword():
    global keywords_index
    if KEYWORDS_LIST:
        keywords_index = (keywords_index + 1) % len(KEYWORDS_LIST)


BASE_URL = 'https://api.unsplash.com'
RES = ['1280x720','1920x1080','3840x2160'][int(REAL_SETTINGS.getSetting("Resolution"))]
RES_PARAMS = ['w=1280&h=720','w=1920&h=1080','w=3840&h=2160'][int(REAL_SETTINGS.getSetting("Resolution"))]

TYPE_PARAMS = [
    'photos?{resp}',
    'collections/{cid}/photos?{resp}',
    'photos/random?{keyword}{resp}',
    'photos/random?featured&{keyword}{resp}',
    'users/{user}/photos?{resp}',
    'users/{user}/likes?{resp}',
    'collections/{cid}/photos?{resp}',
    'search/photos?query={cat}&{resp}'
]

URL_PARAMS = ('%s/%s' % (BASE_URL, TYPE_PARAMS)).format(
    res=RES,
    keyword=KEYWORDS,
    user=USER,
    cid=COLLECTION,
    cat=CATEGORY_SETTING,
    resp=RES_PARAMS
)

IMAGE_URL = f"{URL_PARAMS}&client_id={API_KEY}"

TIMER = [30,60,120,240][int(REAL_SETTINGS.getSetting("RotateTime"))]
IMG_CONTROLS = [30000,30001]
CYC_CONTROL = itertools.cycle(IMG_CONTROLS).__next__

class GUI(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        self.isExiting = False

    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)

    def notificationDialog(self, message, header=ADDON_NAME, sound=False, time=4000, icon=ICON):
        try:
            xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except Exception as e:
            self.log("notificationDialog Failed! " + str(e), xbmc.LOGERROR)
        xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
        return True

    def onInit(self):
        self.winid = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        self.winid.setProperty('unsplash_animation', 'okay' if REAL_SETTINGS.getSetting("Animate") == 'true' else 'nope')
        self.winid.setProperty('unsplash_time', 'okay' if REAL_SETTINGS.getSetting("Time") == 'true' else 'nope')
        self.winid.setProperty('unsplash_overlay', 'okay' if REAL_SETTINGS.getSetting("Overlay") == 'true' else 'nope')
        # Initialize pagination
        self.page = 1
        if CATEGORIES:
            self.images = self.openURL(build_image_url(), 1)
            next_category()
        else:
            self.images = self.openURL(IMAGE_URL, self.page)
            self.page += 1
        self.startRotation()

    def setImage(self, id, images):
        if not hasattr(self, 'image_iter') or self.image_iter is None:
            random.shuffle(images)
            self.image_iter = iter(images)
        try:
            current_image = next(self.image_iter)
        except StopIteration:
            # Cycle ended -> get new images
            if CATEGORIES:
                self.images = self.openURL(build_image_url(), 1)
                next_category()
            else:
                self.images = self.openURL(IMAGE_URL, self.page)
                self.page += 1
            if self.images:
                random.shuffle(self.images)
                self.image_iter = iter(self.images)
                current_image = next(self.image_iter)
            else:
                self.log("No new images available", xbmc.LOGERROR)
                return
        # Metadata
        if isinstance(current_image, dict):
            url = current_image['url']
            author = current_image.get('author', '')
            location = current_image.get('location', '')
            desc = current_image.get('desc', '')
        else:
            url = current_image
            author, location, desc = '', '', ''
        if url and url.startswith("http"):
            self.getControl(id).setImage(url)
        notification_parts = []
        if location: notification_parts.append(location)
        elif desc: notification_parts.append(desc)
        if author: notification_parts.append(author)
        if notification_parts and SHOW_NOTIFICATION:
            overlay_text = " – ".join(notification_parts)
            try:
                xbmcgui.Dialog().notification(
                    ADDON_NAME,
                    overlay_text,
                    ICON,
                    5000,
                    False
                    )
            except Exception as e:
                self.log(f"Notification failed: {str(e)}", xbmc.LOGERROR)

    def startRotation(self):
        self.currentID = IMG_CONTROLS[0]
        self.nextID = IMG_CONTROLS[1]
        if not self.images:
            self.log("No images available to display.", xbmc.LOGERROR)
            return
        while not KODI_MONITOR.abortRequested():
            if self.images:
                self.setImage(self.currentID, self.images)
            self.getControl(self.nextID).setVisible(False)
            self.getControl(self.currentID).setVisible(True)
            self.nextID = self.currentID
            self.currentID = CYC_CONTROL()
            if KODI_MONITOR.waitForAbort(TIMER) or self.isExiting:
                break

    def onAction(self, action):
        self.log("onAction")
        self.isExiting = True
        self.close()

    def openURL(self, url, page=1):
        try:
            # Detect endpoint type
            if "photos/random" in url:
                # Always request a batch of n random images
                paginated_url = f"{url}&count={FETCH_SIZE}"
            elif "search/photos" in url:
                # Search endpoint uses page/per_page instead of count
                paginated_url = f"{url}&page={page}&per_page={FETCH_SIZE}"
            else:
                # Other endpoints (collections, user, likes, etc.)
                paginated_url = f"{url}&page={page}&per_page={FETCH_SIZE}"

            self.log(f"Fetching URL: {paginated_url}")
            request = urllib.request.Request(paginated_url)
            request.add_header("Authorization", f"Client-ID {API_KEY}")
            request.add_header("User-Agent", "Mozilla/5.0")
            response = urllib.request.urlopen(request, timeout=15)
            data = json.load(response)

            image_data = []
            # Single photo object
            if isinstance(data, dict) and "urls" in data:
                image_data.append({
                    "url": data["urls"]["full"],
                    "author": data.get("user", {}).get("name", ""),
                    "location": data.get("location", {}).get("title", ""),
                    "desc": data.get("alt_description", "")
                })
            # Array of photo objects
            elif isinstance(data, list):
                for item in data:
                    if "urls" in item:
                        image_data.append({
                            "url": item["urls"]["full"],
                            "author": item.get("user", {}).get("name", ""),
                            "location": item.get("location", {}).get("title", ""),
                            "desc": item.get("alt_description", "")
                        })
            # Search endpoint returns results array
            elif "results" in data:
                for item in data["results"]:
                    if "urls" in item:
                        image_data.append({
                            "url": item["urls"]["full"],
                            "author": item.get("user", {}).get("name", ""),
                            "location": item.get("location", {}).get("title", ""),
                            "desc": item.get("alt_description", "")
                        })

            self.log(f"Retrieved {len(image_data)} images")
            return image_data

        except Exception as e:
            self.log(f"openURL Failed on page {page}! Error: {str(e)}", xbmc.LOGERROR)
            return []
