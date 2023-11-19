import threading
import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk
import tkinter.ttk
from threading import Thread

import requests
from tkinter import Listbox, Canvas, PhotoImage
from pytube import Search, YouTube, StreamQuery, Stream, request as pyrequest
from PIL import ImageTk, Image
import ffmpeg
from async_lib import AsyncDownloader, AsyncConverter, AsyncSearcher, AsyncThumbnailLoader
import os

import constants as conf

#pyrequest.default_range_size = 9437184  # 9MB chunk size
#pyrequest.default_range_size = 137184  # 137KB chunk size
#pyrequest.default_range_size = 7168  # 7KB chunk size
pyrequest.default_range_size = 4096  # 4KB chunk size

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        try:
            if not os.path.exists(conf.METADATA_PATH):
                os.mkdir(conf.METADATA_PATH)
            else:
                print("La carpeta 'metadata' ya existe!")

            if not os.path.exists(conf.CACHE_PATH):
                os.mkdir(conf.CACHE_PATH)
            else:
                print("La carpeta 'cache' ya existe!")

            if not os.path.exists(conf.OUTPUT_PATH):
                os.mkdir(conf.OUTPUT_PATH)
            else:
                print("La carpeta 'songs' ya existe!")
        except Exception:
            pass

        #setting title
        #s = ttk.Style()
        #s.theme_use('clam')
        self.title("YouTune - Music Downloader")

        #setting window size
        width=800
        height=600
        screenwidth = self.winfo_screenwidth()
        screenheight = self.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        self.geometry(alignstr)
        self.resizable(width=False, height=False)

        self.songs = []

        self.SearchEdit=tk.Entry(self)
        self.SearchEdit["borderwidth"] = "1px"
        self.font = tkFont.Font(family='Arial',size=13)
        self.SearchEdit["font"] = self.font
        self.SearchEdit["fg"] = "#333333"
        self.SearchEdit["justify"] = "left"
        self.SearchEdit.place(x=110, y=10, width=335, height=36)

        self.SearchLabel=tk.Label(self)
        self.SearchLabel["font"] = self.font
        self.SearchLabel["fg"] = "#333333"
        self.SearchLabel["justify"] = "right"
        self.SearchLabel["anchor"] = "e"
        self.SearchLabel["text"] = "Busqueda:"
        self.SearchLabel.place(x=20, y=10, width=88, height=36)

        self.MessageLabel = tk.Label(self)
        self.MessageLabel["font"] = self.font
        self.MessageLabel["fg"] = "#333333"
        self.MessageLabel["justify"] = "left"
        self.MessageLabel["anchor"] = "w"
        self.MessageLabel["text"] = "Esperando"
        self.MessageLabel.place(x=460, y=250, width=150, height=36)

        self.ProgressLabel = tk.Label(self)
        self.ProgressLabel["font"] = self.font
        self.ProgressLabel["fg"] = "#333333"
        self.ProgressLabel["justify"] = "left"
        self.ProgressLabel["text"] = "0%"
        self.ProgressLabel["anchor"] = "w"
        self.ProgressLabel.place(x=460, y=285, width=150, height=36)

        self.InfoLabel = tk.Label(self)
        self.InfoLabel["font"] = self.font
        self.InfoLabel["fg"] = "#333333"
        self.InfoLabel["justify"] = "left"
        self.InfoLabel["anchor"] = "nw"
        self.InfoLabel["text"] = "Titulo:"
        self.InfoLabel.place(x=20, y=284, width=width-200, height=36)

        self.SearchButton=tk.Button(self)
        self.SearchButton["bg"] = "#f0f0f0"
        self.SearchButton["font"] = self.font
        self.SearchButton["fg"] = "#000000"
        self.SearchButton["justify"] = "right"
        self.SearchButton["text"] = "Buscar"
        self.SearchButton.place(x=460, y=10, width=140, height=36)
        self.SearchButton["command"] = self.onSearchClickEvent

        self.ListScrollbar = tk.Scrollbar(
            self,
            orient=tk.VERTICAL,
        )
        self.ListScrollbar.place(x=430, y=60, width=20, height=220)

        self.ResultsListBox= ttk.Treeview(self, column=("c1", "c2"), selectmode="browse", show='headings', yscrollcommand=self.ListScrollbar.set)
        self.ResultsListBox.place(x=20, y=60, width=410, height=220)
        self.ResultsListBox.column("# 1", anchor=tk.W)
        self.ResultsListBox.heading("# 1", text="Titulo")
        self.ResultsListBox.column("# 2", anchor=tk.CENTER)
        self.ResultsListBox.heading("# 2", text="Duracion")

        self.ListScrollbar.config(command=self.ResultsListBox.yview)

        #self.ResultsListBox.bind('<<ListboxSelect>>', lambda evt: self.onSelectItemEvent())

        self.DownloadButton=tk.Button(self)
        self.DownloadButton["bg"] = "#f0f0f0"
        self.DownloadButton["font"] = self.font
        self.DownloadButton["fg"] = "#000000"
        self.DownloadButton["justify"] = "center"
        self.DownloadButton["text"] = "Descargar"
        self.DownloadButton.place(x=460, y=60, width=140, height=36)
        self.DownloadButton["command"] = self.onDownloadClickEvent

        self.ThumbnailWidth, self.ThumbnailHeight = 140, 140

        self.ThumbnailCanvas = Canvas(
            self,
            bg = "#FFFFFF",
            height = self.ThumbnailWidth,
            width = self.ThumbnailHeight,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        self.ThumbnailCanvas.place(x=460, y=106)

        self.ThumbnailImage = ImageTk.PhotoImage(self.rescale("./image.png"))
        self.ThumbnailImageId = self.ThumbnailCanvas.create_image(self.ThumbnailWidth/2,self.ThumbnailHeight/2, anchor="center",image=self.ThumbnailImage)

    def onSearchClickEvent(self):
        text = self.SearchEdit.get()
        self.ResultsListBox.delete()
        self.songs.clear()
        if len(text) <= 0: return
        self.SearchButton['state'] = tk.DISABLED
        search_process = AsyncSearcher(str(text), progress_callback=self.onSearchProgress)
        search_process.start()
        self.searchMonitor(search_process)

    def onSearchProgress(self, song: YouTube):
        self.songs.append(song)
        minutos = int(song.length//60)
        segundos = song.length - (minutos*60)
        prefix = ""
        if segundos < 10:
            prefix = "0"
        self.ResultsListBox.insert('', 'end', text=song.title, values=(song.title, str(minutos)+":"+prefix+str(segundos)))

    def searchMonitor(self, thread: AsyncSearcher):
        if thread.is_alive():
            self.after(100, lambda : self.searchMonitor(thread))
            self.SearchButton['text'] = thread.message
        else:
            self.SearchButton['text'] = "Buscar"
            self.SearchButton['state'] = tk.NORMAL
        #print(thread.message)
    def onDownloadClickEvent(self):
        self.MessageLabel["text"] = "Preparando"
        self.DownloadButton['state'] = tk.DISABLED
        index = self.ResultsListBox.selection()[0]
        song: YouTube = self.songs[index]
        filename = str(song.video_id) + ".mp3"

        download_process = AsyncDownloader(song, callback=self.onDownloadComplete)
        download_process.start()
        self.downloadMonitor(download_process)

    def onDownloadComplete(self, source: str, title: str):
        convert_process = AsyncConverter(source, title, complete_callback=self.onConvertComplete)
        convert_process.start()
        self.convertMonitor(convert_process)

    def onConvertComplete(self, path: str):
        try:
            os.remove(path)
        except Exception:
            pass
    def downloadMonitor(self, thread: AsyncDownloader):
        if thread.is_alive():
            self.after(100, lambda : self.downloadMonitor(thread))
        else:
            #print(thread.message)
            self.DownloadButton['state'] = tk.NORMAL
        self.MessageLabel["text"] = thread.message
        self.ProgressLabel["text"] = str(thread.percent) + "%"

    def convertMonitor(self, thread: AsyncConverter):
        if thread.is_alive():
            self.after(100, lambda : self.convertMonitor(thread))
        else:
            #print(thread.message)
            self.DownloadButton['state'] = tk.NORMAL
        self.MessageLabel["text"] = thread.message
        self.ProgressLabel["text"] = str(thread.percent) + "KB"

    def onSelectItemEvent(self):
        try:
            index = self.ResultsListBox.selection()[0]
        except Exception:
            return
        song: YouTube = self.songs[index]
        self.InfoLabel["text"] = "Titulo: " + song.title

        url = song.thumbnail_url
        filename = conf.METADATA_PATH + str(song.video_id) + ".jpg"
        if os.path.exists(filename):
            self.ThumbnailImage = ImageTk.PhotoImage(self.rescale(filename))
            self.ThumbnailCanvas.itemconfig(self.ThumbnailImageId, image=self.ThumbnailImage)
        else:
            thumbnailprocess = AsyncThumbnailLoader(url, filename, complete_callback=self.onThumbLoadComplete)
            thumbnailprocess.start()

    def onThumbLoadComplete(self, filename: str):
        self.ThumbnailImage = ImageTk.PhotoImage(self.rescale(filename))
        self.ThumbnailCanvas.itemconfig(self.ThumbnailImageId, image=self.ThumbnailImage)

    def rescale(self, filename):
        image = Image.open(filename)
        factor = round(image.width / image.height, 6)
        height = round(self.ThumbnailWidth / factor, 6)
        return image.resize((int(self.ThumbnailWidth), int(height)), Image.ANTIALIAS)

if __name__ == "__main__":
    app = App()
    app.mainloop()
