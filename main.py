import threading
import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk
import tkinter.ttk
from threading import Thread

import pytube.exceptions
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

        self.font = tkFont.Font(family='Arial', size=13)

        self.SearchLabel=tk.Label(self)
        self.SearchLabel["font"] = self.font
        self.SearchLabel["fg"] = "#333333"
        self.SearchLabel["justify"] = "right"
        self.SearchLabel["anchor"] = "e"
        self.SearchLabel["text"] = "Busqueda:"
        self.SearchLabel.place(x=20, y=10, width=90, height=36)

        self.SearchEdit=tk.Entry(self)
        self.SearchEdit["borderwidth"] = "0px"
        self.SearchEdit["font"] = self.font
        self.SearchEdit["fg"] = "#333333"
        self.SearchEdit["justify"] = "left"
        self.SearchEdit.place(x=120, y=14, width=500, height=26)
        self.SearchEdit.bind("<Return>", lambda evt: self.onSearchClickEvent())

        self.SearchButton = tk.Button(self)
        self.SearchButton["bg"] = "#f0f0f0"
        self.SearchButton["font"] = self.font
        self.SearchButton["fg"] = "#000000"
        self.SearchButton["justify"] = "right"
        self.SearchButton["text"] = "Buscar"
        self.SearchButton.place(x=640, y=10, width=140, height=30)
        self.SearchButton["command"] = self.onSearchClickEvent

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
        self.ProgressLabel.place(x=460, y=605, width=150, height=36)

        self.InfoLabel = tk.Label(self)
        self.InfoLabel["font"] = self.font
        self.InfoLabel["fg"] = "#333333"
        self.InfoLabel["justify"] = "left"
        self.InfoLabel["anchor"] = "nw"
        self.InfoLabel["text"] = "Titulo:"
        self.InfoLabel.place(x=20, y=564, width=width-200, height=36)

        self.ListScrollbar = tk.Scrollbar(
            self,
            orient=tk.VERTICAL,
        )
        self.ListScrollbar.place(x=760, y=60, width=20, height=220)

        self.ResultsListTree= ttk.Treeview(self, columns=("c1", "c2", "c3", "c4"), selectmode="browse", show='headings', yscrollcommand=self.ListScrollbar.set, )
        self.ResultsListTree.column("# 1", anchor=tk.W)
        self.ResultsListTree.heading("# 1", text="Titulo")
        self.ResultsListTree.column("# 2", anchor=tk.CENTER, width=80)
        self.ResultsListTree.heading("# 2", text="Duracion")
        self.ResultsListTree.column("# 3", anchor=tk.W, width=100)
        self.ResultsListTree.heading("# 3", text="Autor")
        self.ResultsListTree.column("# 4", anchor=tk.W)
        self.ResultsListTree.heading("# 4", text="Fecha creacion")
        self.ResultsListTree.place(x=20, y=60, width=740, height=220)
        self.ResultsListTree.bind("<<TreeviewSelect>>", lambda evt: self.onSelectItemEvent())

        self.ListScrollbar.config(command=self.ResultsListTree.yview)

        #self.ResultsListBox.bind('<<ListboxSelect>>', lambda evt: self.onSelectItemEvent())

        self.DownloadButton=tk.Button(self)
        self.DownloadButton["bg"] = "#f0f0f0"
        self.DownloadButton["font"] = self.font
        self.DownloadButton["fg"] = "#000000"
        self.DownloadButton["justify"] = "center"
        self.DownloadButton["text"] = "Descargar"
        self.DownloadButton.place(x=460, y=300, width=140, height=36)
        self.DownloadButton["command"] = self.onDownloadClickEvent

        self.ThumbnailWidth, self.ThumbnailHeight = 140, 140
        self.ThumbnailImage = ImageTk.PhotoImage(self.rescale("./image.png"))
        self.ThumbnailHeight = self.ThumbnailImage.height()
        print(self.ThumbnailHeight)

        self.ThumbnailCanvas = Canvas(
            self,
            bg = "#FFFFFF",
            height = self.ThumbnailWidth,
            width = self.ThumbnailHeight,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )
        self.ThumbnailCanvas.place(x=20, y=300)

        self.ThumbnailImageId = self.ThumbnailCanvas.create_image(self.ThumbnailWidth/2,self.ThumbnailHeight/2, anchor="center",image=self.ThumbnailImage)

    def onSearchClickEvent(self):
        text = self.SearchEdit.get()
        # Clear TreeView
        for item in self.ResultsListTree.get_children():
            self.ResultsListTree.delete(item)
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
        horas = 0
        if minutos > 59:
            horas = int(minutos // 60)
            minutos = minutos - (horas*60)
        s_prefix = ""
        m_prefix = ""
        h_prefix = ""
        if segundos < 10:
            s_prefix = "0"
        if minutos < 10:
            m_prefix = "0"
        if horas < 10:
            h_prefix = "0"

        self.ResultsListTree.insert(
            '',
            'end',
            iid=len(self.songs)-1,
            text=song.title,
            values=(
                song.title,
                h_prefix + str(horas) + ":" + m_prefix + str(minutos) + ":" + s_prefix + str(segundos),
                song.author,
                song.publish_date.date()
            )
        )

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
        try:
            index = int(self.ResultsListTree.selection()[0])
            song: YouTube = self.songs[index]
            download_process = AsyncDownloader(song, callback=self.onDownloadComplete)
            download_process.start()
            self.downloadMonitor(download_process)
        except Exception as e:
            print(e)
            self.DownloadButton['state'] = tk.NORMAL

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
            #print(self.ResultsListTree.selection()[0])
            index = int(self.ResultsListTree.selection()[0])
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
        except Exception as e:
            print(e)

    def onThumbLoadComplete(self, filename: str):
        self.ThumbnailImage = ImageTk.PhotoImage(self.rescale(filename))
        self.ThumbnailCanvas.itemconfig(self.ThumbnailImageId, image=self.ThumbnailImage)
        self.ThumbnailCanvas.config(height=self.ThumbnailImage.height())

    def rescale(self, filename):
        image = Image.open(filename)
        if image.width >= image.height:
            factor = round(image.width / image.height, 6)
            height = round(self.ThumbnailWidth / factor, 6)
            width = self.ThumbnailWidth
        else:
            factor = round(image.height / image.width, 6)
            height = self.ThumbnailHeight
            width = round(self.ThumbnailHeight / factor, 6)

        return image.resize((int(width), int(height)), Image.ANTIALIAS)

if __name__ == "__main__":
    app = App()
    app.mainloop()
