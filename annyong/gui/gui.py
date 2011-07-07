import wx

class GUI(wx.Frame):
    def __init__(self, nes):
        super(GUI, self).__init__(
            parent=None,
            style=wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX,
            size=(256, 240),
        )

        self.nes = nes
        self.SetMenuBar(self._make_menubar())

    def _make_menubar(self):
        file = wx.Menu()
        file.Append(-1, '&Load rom')
        file.Append(-1, '&Reset NES')
        file.Append(-1, '&Quit Annyong')

        ppu = wx.Menu()
        ppu.Append(-1, 'Debug &nametable')
        ppu.Append(-1, 'Debug &pattern table')

        menubar = wx.MenuBar()
        menubar.Append(file, '&File')
        menubar.Append(ppu, '&PPU')
        return menubar

def main(nes):
    app = wx.App()
    gui = GUI(nes)
    gui.Show()
    app.MainLoop()

if __name__ == '__main__':
    from annyong.nes import NES
    main(NES())
