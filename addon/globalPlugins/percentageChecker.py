# -*- coding: UTF-8 -*-

# Percentage checker
#Copyright (C) 2012-2019 Original idea and code by Oriol Gómez <ogomez.s92@gmail.com>, improvements and maintenance by Łukasz Golonka <lukasz.golonka@mailbox.org>
# Released under GPL 2

import globalPluginHandler
from tones import beep
import controlTypes
import api
import textInfos
import speech
from ui import message
import addonHandler
addonHandler.initTranslation()
import scriptHandler
import wx
import gui
from globalCommands import SCRCAT_SYSTEMCARET
import sys
import review

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	usePositionInfo = True

	@scriptHandler.script(
		# Translators: Describes keyboard command which, depending of how many times is pressed, either reports current percentage in speech or displays a dialog allowing to jump to the particular percentage in the text. 
		description=_("Press this command once to have percentage in the text or on the list reported in speech. Press it twice to display a dialog allowing you to jump to the given percentage in the currently focused text field"),
		gesture = "kb:NVDA+shift+p",
		category = SCRCAT_SYSTEMCARET,
	)
	def script_reportOrJumpTo_speech(self, gesture):
		if scriptHandler.getLastScriptRepeatCount() <= 1:
			self.reportOrJumpTo(showJumpToDialog = bool(scriptHandler.getLastScriptRepeatCount()==1))
		return

	@scriptHandler.script(
		# Translators: Describes keyboard command which, depending of how many times is pressed, either reports current percentage as a beep or displays a dialog allowing to jump to the particular percentage in the text. 
		description=_("Press this command once to have percentage in the text or on the list reported as a beep. Press it twice to display a dialog allowing you to jump to the given percentage in the currently focused text field"),
		gesture = "kb:NVDA+Alt+p",
		category = SCRCAT_SYSTEMCARET,
	)
	def script_reportOrJumpTo_beep(self, gesture):
		if scriptHandler.getLastScriptRepeatCount() <= 1:
			self.reportOrJumpTo(showJumpToDialog = bool(scriptHandler.getLastScriptRepeatCount()==1))
		return

	@scriptHandler.script(
		# Translators: Describes keyboard command which displays a dialog allowing to jump to the particular line in the text. 
		description=_("displays a dialog allowing you to jump to the given line number in the currently focused text field"),
		gesture = "kb:NVDA+shift+j",
		category = SCRCAT_SYSTEMCARET,
	)
	def script_jumpToLine (self, gesture):
		current, total = self._prepare(api.getFocusObject())
		if not any((current, total)):
			return
		lineCount = sum(1 for t in total.getTextInChunks("line"))+1
		fullText = total.copy()
		total.setEndPoint(current, "endToStart")
		lineCountBeforeCaret = sum(1 for t in total.getTextInChunks("line"))+1
		jumpToLineDialog = wx.TextEntryDialog(
			gui.mainFrame,
			#Translators: A message in the dialog allowing to jump to the given line number.
			_("You are here: {0} You can't go further than: {1}").format(lineCountBeforeCaret, lineCount),
			# Translators: Title of the dialog
			_("Jump to line")
		)
		def callback(result):
			if result == wx.ID_OK:
				lineToJumpTo = jumpToLineDialog.GetValue()
				if not (lineToJumpTo.isdigit() and 1 <= int(lineToJumpTo) <= lineCount):
					wx.CallAfter(
						gui.messageBox,
						# Translators: Shown when user enters wrong value in the jump to line dialog.
						_("Wrong value."),
						# Translators: Title of the error dialog
						_("Error"), 
						wx.OK|wx.ICON_ERROR
					)
					return
				wx.CallLater(100, self._jumpTo, posToJump = (int(lineToJumpTo)-1), info = fullText, movingUnit = textInfos.UNIT_LINE)
		gui.runScriptModalDialog(jumpToLineDialog, callback)
		return

	def reportOrJumpTo(self, showJumpToDialog):
		obj=api.getFocusObject()
		callerName = sys._getframe(1).f_code.co_name
		if obj.role == controlTypes.ROLE_LISTITEM:
			if showJumpToDialog:
				# Jumping when focused on a list is not supported.
				return
			if hasattr(obj, 'positionInfo') and obj.positionInfo and self.usePositionInfo == True:
				# Using positionInfo is very fast, so prefer this.
				currPos = float(obj.positionInfo['indexInGroup'])
				totalCount = float(obj.positionInfo['similarItemsInGroup'])
			elif hasattr(obj, "IAccessibleChildID") and obj.IAccessibleChildID >0 and obj.parent and obj.parent.childCount:
				currPos = float(obj.IAccessibleChildID)
				totalCount = float(obj.parent.childCount)
			else:
				# This was present in the original code. Even though it is slow as hell it might be needed in some obscure cases when positionInfo is not implemented.
				objList = obj.parent.children
				# Get rit of all non-listItems objects such as headers, scrollbars etc.
				if objList[-1].role in (controlTypes.ROLE_HEADER, controlTypes.ROLE_LIST):
					objList.remove(objList[-1])
				for  listItem in objList:
					if listItem.role == controlTypes.ROLE_LISTITEM:
						break
					else:
						objList.remove(listItem)
				totalCount = float(len(objList))
				currPos = float(objList.index(obj))
				if currPos == 0:
					currPos += 1
			if callerName == 'script_reportOrJumpTo_speech':
				# Translators: Reported when user asks about position in a list.
				# The full message is as follows:
				# 25 percent, item 1 of 4
				message(_("{0} percent, item {1} of {2}").format(int(currPos/totalCount*100), int(currPos), int(totalCount)))
			if callerName =='script_reportOrJumpTo_beep':
				beep(currPos/totalCount*3000, 100)
			return
		current, total = self._prepare(obj)
		if not any((current, total)):
			return
		totalCharsCount = float(len(total.text))
		if showJumpToDialog:
			jumpToPercentDialog = wx.TextEntryDialog(
				gui.mainFrame,
				#Translators: A message in the dialog allowing to jump to the given percentage.
				_("Enter a percentage to jump to"),
				# Translators: Title of the dialog
				_("Jump to percent")
			)
			def callback(result):
				if result == wx.ID_OK:
					percentToJumpTo = jumpToPercentDialog.GetValue()
					if not (percentToJumpTo.isdigit() and 0 <= int(percentToJumpTo) <= 100):
						wx.CallAfter(
							gui.messageBox,
							# Translators: Shown when user enters wrong value in the dialog.
							_("Wrong value. You can enter a percentage between 0 and 100."),
							# Translators: Title of the error dialog
							_("Error"), 
							wx.OK|wx.ICON_ERROR
						)
						return
					wx.CallLater(100, self._jumpTo, posToJump=float(percentToJumpTo)*(totalCharsCount-1)/100, info = total, movingUnit = textInfos.UNIT_CHARACTER)
			gui.runScriptModalDialog(jumpToPercentDialog, callback)
			return
		totalWordsCount = len(total.text.split())
		total.setEndPoint(current, "endToStart")
		wordCountBeforeCaret = len(total.text.split())
		charsCountBeforeCaret = float(len(total.text))
		if callerName == 'script_reportOrJumpTo_speech':
			# Translators: Presented to the user when command to report percentage in the current text is pressed.
			# Full message is as follows:
			# 80 percent word 486 of 580
			message(_("{0} percent word {2} of {1}").format(int(charsCountBeforeCaret/totalCharsCount*100), totalWordsCount, wordCountBeforeCaret))
		if callerName == 'script_reportOrJumpTo_beep':
			beep(charsCountBeforeCaret/totalCharsCount*3000, 100)
		return

	def _prepare(self, obj):
		treeInterceptor = obj.treeInterceptor
		if hasattr(treeInterceptor, 'TextInfo') and not treeInterceptor.passThrough:
			obj = treeInterceptor
		current = total = None
		try:
			total = obj.makeTextInfo(textInfos.POSITION_ALL)
		except (NotImplementedError, RuntimeError):
			return current, total
		try:
			current = obj.makeTextInfo(textInfos.POSITION_CARET)
		except (NotImplementedError, RuntimeError):
			# Translators: Announced when there is no caret in the currently focused control.
			message(_("Caret not found"))
			return None, None
		if total.text == '':
			# Translators: Reported when the field with caret is empty
			message(_("No text"))
			return None, None
		return current, total

	def _jumpTo(self, posToJump, info, movingUnit):
		if info.obj is None:
			# For whatever reason when textInfo is passed to this function via wx.CallLater its obj attribute is set to None in some cases.
			# As I do not understand why use this work around.
			info.obj = api.getFocusObject()
		try:
			speech.cancelSpeech()
			info.move(movingUnit, int(posToJump), "start")
			info.updateCaret()
			info.expand(textInfos.UNIT_LINE)
			review.handleCaretMove(info)
			speech.speakTextInfo(info, unit=textInfos.UNIT_LINE, reason=controlTypes.REASON_CARET)
		except NotImplementedError:
			pass
