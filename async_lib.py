import os
import threading
from subprocess import Popen
import ffmpeg
import requests
from ffmpeg import Stream
from pytube import Stream, YouTube, Search
import constants as conf

class BaseAsync(threading.Thread):
	def __init__(self):
		super().__init__()
		self.message = ""

	def run(self):
		self.message = "Preparando..."

class AsyncDownloader(BaseAsync):
	def __init__(self, song: YouTube, callback: callable = None):
		super().__init__()
		self.complete_callback = callback
		self.percent = 0
		self.song = song
		self.song.register_on_progress_callback(self.onDownloadProgress)
		self.song.register_on_complete_callback(self.onDownloadComplete)
		self.filename = str(song.video_id) + conf.DEFAULT_AUDIO_EXT
		self.audio: Stream = None

	def onDownloadProgress(self, stream: Stream, chunk: bytes, bytes_remaining):
		total_size = stream.filesize
		bytes_downloaded = total_size - bytes_remaining
		percent = bytes_downloaded / total_size * 100
		self.percent = int(percent)

	def setOnDownloadComplete(self, callback):
		self.complete_callback = callback

	def onDownloadComplete(self, stream, status):
		if not self.complete_callback is None:
			self.complete_callback(self.filename, self.song.title)

	def run(self):
		super().run()
		self.audio: Stream = self.song.streams.filter(only_audio=True).first()
		self.message = "Descargando"
		self.audio.download(conf.CACHE_PATH, self.filename)
		self.message = "Listo"


class AsyncConverter(BaseAsync):
	def __init__(self, filename: str, title: str, progress_callback: callable = None, complete_callback: callable = None, chunk_size: int = conf.DEFAULT_CHUNK_SIZE):
		super().__init__()
		self.filename = filename
		self.song_title = title
		self.chunk_size = chunk_size
		self.progress_callback = progress_callback
		self.complete_callback = complete_callback
		self.percent = 0

	def run(self):
		super().run()
		self.convertAudio()

	def setOnProgressCallback(self, callback: callable = None):
		self.progress_callback = callback

	def setOnCompleteCallback(self, callback: callable = None):
		self.complete_callback = callback

	def onProgressHandler(self):
		if not self.progress_callback is None:
			self.progress_callback()

	def onCompleteHandler(self, input_path: str):
		if not self.complete_callback is None:
			self.complete_callback(input_path)

	def convertAudio(self):
		filename, title = self.filename, self.song_title
		output_path = conf.OUTPUT_PATH + (title[0:50] if len(title) > 51 else title) + ".mp3"
		input_path = conf.CACHE_PATH + filename
		song_size = os.stat(input_path).st_size
		stream = ffmpeg.input(input_path)
		audio_stream = stream.audio

		self.message = "Convirtiendo..."
		output_stream = ffmpeg.output(audio_stream, output_path)
		process: Popen = (output_stream
		                  .global_args("-progress", "pipe:")
		                  .overwrite_output()
		                  .global_args('-y', '-loglevel', 'panic')
		                  .run_async(pipe_stdout=True, pipe_stderr=True))

		while True:
			line = process.stdout.readline()
			if not line:
				break
			if str(line).find("size") >= 0:
				key = str(line).split("=")[0][2:]
				value = str(line).split("=")[1][:-3]
				total_size = int(value)
				#print("[PROCESS]", key, round(total_size/10000, 3), "kb")
				self.percent = round(total_size/10000, 3)
				self.onProgressHandler()

		process.wait()
		self.message = "Listo"
		self.onCompleteHandler(input_path)


class AsyncSearcher(BaseAsync):
	def __init__(self, query: str, pages: int = conf.DEFAULT_PAGES_COUNT, progress_callback: callable = None, complete_callback: callable = None):
		super().__init__()
		self.query = query
		self.songs = []
		self.pages = pages
		self.progress_callback = progress_callback
		self.complete_callback = complete_callback

	def setOnProgressCallback(self, callback: callable = None):
		self.progress_callback = callback

	def onProgressHandler(self, song: YouTube):
		if not self.progress_callback is None:
			self.progress_callback(song)

	def setOnCompleteCallback(self, callback: callable = None):
		self.complete_callback = callback

	def onCompleteHandler(self):
		if not self.complete_callback is None:
			self.complete_callback()

	def run(self):
		#Searching...
		self.message = "Buscando..."

		while len(self.songs) < (self.pages*conf.DEFAULT_SONGS_PER_PAGE):
			self.search()

		self.message = str(len(self.songs)) + " resultados"
		self.onCompleteHandler()

	def search(self):
		search = Search(self.query)
		for e in search.results:
			#import pytube
			#try:
			#	live = e.streams.first().is_live
			#except pytube.exceptions.LiveStreamError:
			#	continue
			self.songs.append(e)
			self.onProgressHandler(e)
			url = e.thumbnail_url
			filename = conf.METADATA_PATH + str(e.video_id) + ".jpg"
			thumbnail_process = AsyncThumbnailLoader(url, filename)
			thumbnail_process.start()
		self.query = str(search.get_next_results())

	def next(self, pages: int = conf.DEFAULT_PAGES_COUNT):
		self.pages = pages
		self.songs.clear()


class AsyncThumbnailLoader(BaseAsync):
	def __init__(self, url: str, outputpath: str, complete_callback: callable = None):
		super().__init__()
		self.url = url
		self.outputpath = outputpath
		self.complete_callback = complete_callback

	def setOnLoadComplete(self, callback: callable = None):
		self.complete_callback = callback

	def onLoadCompleteHandler(self):
		#print(self.outputpath, "downloaded")
		if not self.complete_callback is None:
			self.complete_callback(self.outputpath)

	def run(self):
		#Downloading Thumbnail
		self.message = "Descargando..."
		response = requests.get(self.url)
		if response.status_code == 200:
			with open(self.outputpath, 'wb') as handler:
				handler.write(response.content)
			self.onLoadCompleteHandler()
		del response
		self.message = "Listo"

