# -*- coding: UTF-8 -*-
#globalPlugins/winMag.py
#NVDA add-on: Windows Magnifier
#Copyright (C) 2019 Cyrille Bougot
#This file is covered by the GNU General Public License.
#See the file COPYING.txt for more details.

"""TODO list:
- Test Py3 and 2018.3
- Test Win7
- Package as add-on: start with add-on template; remove zzz
- Implement toggleTracking script (partially done)
- Implement pane left/right/up/down when pressing ctrl+alt+arrow if not in table (cf. documentBase.py, winword.py, qt.py...)
- See if possible to implement moveToCaret/Focus/Mouse scripts. See:
* can we fire artificially caret/focus/mouse event
* see https://docs.microsoft.com/en-us/windows/win32/api/magnification/nf-magnification-magsetfullscreentransform

- See if possibl to get programmatically coords of current view to route mouse to view. See:
* https://docs.microsoft.com/fr-fr/windows/win32/api/magnification/nf-magnification-maggetfullscreentransform
* https://social.msdn.microsoft.com/Forums/en-US/8484d886-93e0-4bd7-ac6d-0e019d1bdace/how-do-i-get-the-bounds-of-the-current-windows-magnifier-view-displayed-on-the-screen-and-the-screen?forum=windowsgeneraldevelopmentissues)
- remove log.debug
"""

from __future__ import unicode_literals

import globalPluginHandler
from scriptHandler import script
import ui
from logHandler import log

try:
	import winreg
except ImportError:
	import _winreg as winreg
import time
from functools import wraps

import addonHandler

#zzz addonHandler.initTranslation()

#zzz ADDON_SUMMARY = addonHandler.getCodeAddon ().manifest["summary"]
ADDON_SUMMARY = "zzz"

MAG_REGISTRY_KEY = r'Software\Microsoft\ScreenMagnifier'

#Magnifier view types
MAG_VIEW_DOCKED = 1
MAG_VIEW_FULLSCREEN = 2
MAG_VIEW_LENS = 3

#Default config when names are not present in the key
MAG_DEFAULT_FOLLOW_CARET = 0
MAG_DEFAULT_FOLLOW_FOCUS = 0
MAG_DEFAULT_FOLLOW_MOUSE = 1
MAG_DEFAULT_FULL_SCREEN_TRACKING_MODE = 0
MAG_DEFAULT_INVERT = 1
MAG_DEFAULT_MAGNIFICATION = 200
MAG_DEFAULT_MAGNIFICATION_MODE = MAG_VIEW_FULLSCREEN
MAG_DEFAULT_RUNNING_STATE = 0
MAG_DEFAULT_USE_BITMAP_SMOOTHING = 1

def getMagnifierKeyValue(name, default=None):
	k = winreg.OpenKey(
		winreg.HKEY_CURRENT_USER,
		MAG_REGISTRY_KEY,
		0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY
	)
	try:
		return winreg.QueryValueEx(k, name)[0]
	except WindowsError as e:
		if default is not None:
			return default
		raise e

def setMagnifierKeyValue(name, val):
	k = winreg.OpenKey(
		winreg.HKEY_CURRENT_USER,
		r'Software\Microsoft\ScreenMagnifier',
		0, winreg.KEY_READ | winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
	)
	winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, val)
	
def toggleMagnifierKeyValue(name, default=None):
	val = getMagnifierKeyValue(name, default)
	val = 0 if val == 1 else 1
	setMagnifierKeyValue(name, val)
	return val
	
def isMagnifierRunning():
	return getMagnifierKeyValue('RunningState', default=MAG_DEFAULT_RUNNING_STATE)

def isFullScreenView():
	return getMagnifierKeyValue('MagnificationMode', default=MAG_DEFAULT_MAGNIFICATION_MODE) == MAG_VIEW_FULLSCREEN

def onlyIfMagRunning(s):
	"""This script decorator allows the decorated script to execute only if the Magnifier is active.
	If not a message informs the user that the Magnifier is not running.
	"""
	
	@wraps(s)
	def script_wrapper(self, gesture):
		if not isMagnifierRunning():
			# Translators: The message reported when the user tries to use a Magnifier dedicated command while the Magnifier is not running
			ui.message(_('The Magnifier is not active'))
			return
		s(self, gesture)
	#script_wrapper.__name__ = f.__name__
	return script_wrapper


#Code taken from NVDA's source code NVDAObjects/window/winword.py
def _WaitForValueChangeForAction(gesture, fetcher, timeout=0.2):
	oldVal=fetcher()
	gesture.send()
	startTime=curTime=time.time()
	curVal=fetcher()
	while curVal==oldVal and (curTime-startTime)<timeout:
		log.debug(curVal)
		time.sleep(0.03)
		curVal=fetcher()
		curTime=time.time()
	return curVal

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	scriptCategory = ADDON_SUMMARY
	
	def __init__(self):
		super(GlobalPlugin, self).__init__()
	
	@script(
		gestures = ["kb:windows+numpadPlus", "kb:windows+numLock+numpadPlus", "kb:windows+="]
		)	
	def script_zoomIn(self, gesture):
		if isMagnifierRunning():
			self.modifyZoomLevel(gesture)
		else:
			self.modifyRunningState(gesture)
	
	@script(
		gestures = ["kb:windows+-", "kb:windows+numpadMinus", "kb:windows+numLock+numpadMinu"]
	)	
	def script_zoomOut(self, gesture):
		if isMagnifierRunning():
			self.modifyZoomLevel(gesture)
		else:
			gesture.send()
		
	@script(
		gesture = "kb:windows+escape"
	)
	def script_quitMagnifier(self, gesture):
		if isMagnifierRunning():
			self.modifyRunningState(gesture)
		else:
			gesture.send()
		
	@script(
		gesture = "kb:control+alt+I"
	)
	def script_toggleColorInversion(self, gesture):
		if isMagnifierRunning():
			self.modifyColorInversion(gesture)
		else:
			gesture.send()
	
	@script(
		gestures = ["kb:control+alt+M", "kb:control+alt+D", "kb:control+alt+F", "kb:control+alt+L"])
	def script_changeMagnificationView(self, gesture):
		if isMagnifierRunning():
			self.modifyMagnificationView(gesture)
		else:
			gesture.send()

	@script(
		# Translators: The description for the toggleCaretTracking script
		description = _("Toggle caret tracking"),
		gestures = ["kb:nvda+windows+C"]
	)
	@onlyIfMagRunning
	def script_toggleCaretTracking(self, gesture):
		val = toggleMagnifierKeyValue('FollowCARET', default=MAG_DEFAULT_FOLLOW_CARET)
		if val:
			# Translators: The message reported when the user turns on caret tracking
			ui.message(_('Caret tracking on'))
		else:
			# Translators: The message reported when the user turns off caret tracking
			ui.message(_('Caret tracking off'))
	
	@script(
		# Translators: The description for the toggleFocusTracking script
		description = _("Toggle focus tracking"),
		gestures = ["kb:nvda+windows+F"]
	)
	@onlyIfMagRunning
	def script_toggleFocusTracking(self, gesture):
		val = toggleMagnifierKeyValue('FollowFocus', default=MAG_DEFAULT_FOLLOW_FOCUS)
		if val:
			# Translators: The message reported when the user turns on focus tracking
			ui.message(_('Focus tracking on'))
		else:
			# Translators: The message reported when the user turns off focus tracking
			ui.message(_('Focus tracking off'))

	@script(
		# Translators: The description for the toggleMouseTracking script
		description = _("Toggle mouse tracking"),
		gestures = ["kb:nvda+windows+M"]
	)
	@onlyIfMagRunning
	def script_toggleMouseTracking(self, gesture):
		val = toggleMagnifierKeyValue('FollowMouse', default=MAG_DEFAULT_FOLLOW_MOUSE)
		if val:
			# Translators: The message reported when the user turns on mouse tracking
			ui.message(_('Mouse tracking on'))
		else:
			# Translators: The message reported when the user turns off focus tracking
			ui.message(_('Mouse tracking off'))
	@script(
		# Translators: The description for the toggleTracking script
		description = _("Toggle tracking"),
		gestures = ["kb:nvda+windows+T"]
	)
	@onlyIfMagRunning
	def script_toggleTracking(self, gesture):
		names = ['FollowCaret', 'FollowFocus', 'FollowMouse']
		defaults=[MAG_DEFAULT_FOLLOW_CARET, MAG_DEFAULT_FOLLOW_FOCUS, MAG_DEFAULT_FOLLOW_MOUSE]
		vals = [getMagnifierKeyValue(n, d) for (n,d) in zip(names, defaults)]
		if all(v == 0 for v in vals):
			vals = [1 for v in vals]
		else:
			vals = [0 for v in vals]
		for (n,v) in zip(names, vals):
			setMagnifierKeyValue(n, v)
		if not all(v == 0 for v in vals):
			# Translators: The message reported when the user turns on tracking
			ui.message(_('Tracking on'))
		else:
			# Translators: The message reported when the user turns off tracking
			ui.message(_('Tracking off'))
	
	@script(
		# Translators: The description for the toggleSmoothing script
		description = _("Toggle smoothing"),
			gestures = ["kb:nvda+windows+S"]
	)
	@onlyIfMagRunning
	def script_toggleSmoothing(self, gesture):
		val = toggleMagnifierKeyValue('UseBitmapSmoothing', default=MAG_DEFAULT_USE_BITMAP_SMOOTHING)
		if val:
			# Translators: The message reported when the user turns on smoothing
			ui.message(_('Smoothing on'))
		else:
			# Translators: The message reported when the user turns off smoothing
			ui.message(_('Smoothing off'))
	
	@script(
		# Translators: The description for the toggleMouseCursorTrackingMode script
		description = _("Toggle mouse tracking mode"),
			gestures = ["kb:nvda+windows+R"]
	)
	@onlyIfMagRunning
	def script_toggleMouseCursorTrackingMode(self, gesture):
		if not isFullScreenView():
			# Translators: A message reporting mouse cursor tracking mode (cf. option in Magnifier settings)
			ui.message(_('Mouse tracking mode applies only to full screen view.'))
			return
		# zzz Starting with Windows 10 build 17643, you can now choose to keep the mouse cursor centered on the screen or within the edges of the screen while using Magnifier in full screen view. 
		val = toggleMagnifierKeyValue('FullScreenTrackingMode', default=MAG_DEFAULT_FULL_SCREEN_TRACKING_MODE)
		if val:
			# Translators: A message reporting mouse cursor tracking mode (cf. option in Magnifier settings)
			ui.message(_('Centered on the screen'))
		else:
			# Translators: A message reporting mouse cursor tracking mode (cf. option in Magnifier settings)
			ui.message(_('Within the edge of the screen'))

	def modifyRunningState(self, gesture):
		fetcher = lambda: getMagnifierKeyValue('RunningState', default=MAG_DEFAULT_RUNNING_STATE)
		val = _WaitForValueChangeForAction(gesture, fetcher, timeout=2)
		if val == 1:
			# Translators: The message reported when the user turns on the Magnifier
			ui.message(_('Magnifier on'))
		elif val == 0:
			# Translators: The message reported when the user turns off the Magnifier
			ui.message(_('Magnifier off'))
		else:
			raise ValueError('Unexpected RunningState value: {}'.format(val))
			
	def modifyZoomLevel(self, gesture):
		fetcher = lambda: getMagnifierKeyValue('Magnification', default=MAG_DEFAULT_MAGNIFICATION)
		val = _WaitForValueChangeForAction(gesture, fetcher)
		# Translators: A zoom level reported when the user changes the zoom level
		ui.message(_('{}%'.format(val)))
		
	def modifyColorInversion(self, gesture):
		fetcher = lambda: getMagnifierKeyValue('Invert', default=MAG_DEFAULT_INVERT)
		val = _WaitForValueChangeForAction(gesture, fetcher, timeout=0.5)
		if val == 1:
			# Translators: The message reported when the user turns on color inversion
			ui.message(_('Color inversion on'))
		elif val == 0:
			# Translators: The message reported when the user turns off color inversion
			ui.message(_('Color inversion off'))
		else:
			raise ValueError('Unexpected Invert value: {}'.format(val))
			
	def modifyMagnificationView(self, gesture):
		fetcher = lambda: getMagnifierKeyValue('MagnificationMode', default=MAG_DEFAULT_MAGNIFICATION_MODE)
		val = _WaitForValueChangeForAction(gesture, fetcher)
		if val == MAG_VIEW_DOCKED:
			# Translators: A view type reported when the user changes the Magnifier view. See the view menu items in the Magnifier's toolbar.
			ui.message(_('Docked'))
		elif val == MAG_VIEW_FULLSCREEN:
			# Translators: A view type reported when the user changes the Magnifier view. See the view menu items in the Magnifier's toolbar.
			ui.message(_('Full screen'))
		elif val == MAG_VIEW_LENS:
			# Translators: A view type reported when the user changes the Magnifier view. See the view menu items in the Magnifier's toolbar.
			ui.message(_('Lens'))
		else:
			raise ValueError('Unexpected MagnificationMode value: {}'.format(val))
