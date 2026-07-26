"""HomerView's page in NVDA's Settings dialog, and its item in the NVDA menu.

An experienced NVDA user explores a new add-on in two places before touching
the keyboard: the NVDA menu, to see what the add-on offers, and Preferences,
Settings, to see what it lets them change. An add-on that appears in neither
looks like it has no interface at all, however many commands it has bound.

The settings themselves live in HomerView.inix, which a person can also edit by
hand. This panel is a second way to reach the same file rather than a separate
store, so a value changed here is a value changed there, and neither view can
disagree with the other.
"""

import wx

import addonHandler
import gui
from gui.settingsDialogs import SettingsPanel

from . import settings
from .logger import homerLog

addonHandler.initTranslation()

# Each entry: the key in the settings file, the label, and what it means. The
# explanation is a screen reader user's substitute for the sentence a sighted
# user reads beside a check box, so it is written as one.
lFlags = [
    ("reopenLastPage",
     # Translators: Label of a HomerView setting.
     _("&Reopen the page the browser last had open"),
     # Translators: Help text for a HomerView setting.
     _("When off, HomerView opens its start page instead."),
     True),
    ("preferTemporaryPage",
     # Translators: Label of a HomerView setting.
     _("Show reports as a &page in the browser"),
     # Translators: Help text for a HomerView setting.
     _("When off, reports appear in NVDA's message window, which cannot be saved or searched."),
     True),
    ("speakCommandLabels",
     # Translators: Label of a HomerView setting.
     _("Speak a &label before a reported value"),
     # Translators: Help text for a HomerView setting.
     _("Says Address before the web address, as JAWS does. NVDA speaks the value alone."),
     False),
]


class HomerViewSettingsPanel(SettingsPanel):
    # Translators: The label for the HomerView category in NVDA's settings.
    title = _("HomerView")

    def makeSettings(self, sizer):
        helper = gui.guiHelper.BoxSizerHelper(self, sizer=sizer)
        self.dCheckBoxes = {}
        for sKey, sLabel, sHelp, bDefault in lFlags:
            checkBox = helper.addItem(wx.CheckBox(self, label=sLabel))
            checkBox.SetValue(settings.getFlag(sKey, bDefault))
            # The help text is set as the accessible description so a screen
            # reader announces it with the control, which is the only way a
            # user who cannot see the panel will hear it.
            try:
                checkBox.SetToolTip(sHelp)
                checkBox.GetAccessible().SetDescription(sHelp)
            except Exception:
                pass
            self.dCheckBoxes[sKey] = checkBox

        # Where things are is a question users ask, and a settings panel is
        # where they look for the answer.
        from . import paths

        # Translators: Label of the read-only list of folders HomerView uses.
        helper.addItem(wx.StaticText(self, label=_("HomerView writes to these folders:")))
        sFolders = "\n".join([
            _("Settings: {path}").format(path=settings.getSettingsPath()),
            _("Log and history: {path}").format(path=paths.getDataFolder()),
            _("Generated pages: {path}").format(path=paths.getTempFolder()),
            _("Downloads: {path}").format(path=paths.getDownloadsFolder()),
        ])
        textFolders = helper.addItem(
            wx.TextCtrl(self, value=sFolders, size=(520, 90),
                        style=wx.TE_MULTILINE | wx.TE_READONLY))
        # Translators: Accessible name of the read-only folder list.
        textFolders.SetName(_("Folders HomerView writes to"))

    def onSave(self):
        for sKey, checkBox in self.dCheckBoxes.items():
            settings.setValue("Preferences", sKey, "True" if checkBox.GetValue() else "False")
        homerLog.info("Settings saved from the NVDA settings panel")
