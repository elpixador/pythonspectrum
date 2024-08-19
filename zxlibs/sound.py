import numpy
import sounddevice as sd

class AudioInterface:
    def __init__(self):
        self.bufferlen = 32
        self.buffaudio = numpy.zeros((self.bufferlen, 1), dtype=numpy.int16)
        self.audiocount = 0
        self.playAudio = True
        self.audioword = 0
        self.stream = sd.RawOutputStream(12025, channels=1, dtype=numpy.int16)
        self.stream.start()
