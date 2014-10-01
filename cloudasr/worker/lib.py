import audioop
import wave
import zmq
import time
from kaldi.utils import lattice_to_nbest, wst2dict
from kaldi.decoders import PyOnlineLatgenRecogniser
from StringIO import StringIO


def create_worker(model, frontend_address, public_address, master_address):
    poller = create_poller(frontend_address)
    heartbeat = create_heartbeat(model, public_address, master_address)
    asr = ASR()
    audio = AudioUtils()
    run_forever = lambda: True

    return Worker(poller, heartbeat, asr, audio, run_forever)

def create_poller(frontend_address):
    from cloudasr import Poller
    context = zmq.Context()
    frontend_socket = context.socket(zmq.REP)
    frontend_socket.bind(frontend_address)

    sockets = {
        "frontend": {"socket": frontend_socket, "receive": frontend_socket.recv},
    }
    time_func = time.time

    return Poller(sockets, time_func)

def create_heartbeat(model, address, master_address):
    context = zmq.Context()
    master_socket = context.socket(zmq.PUSH)
    master_socket.connect(master_address)

    return Heartbeat(model, address, master_socket)


class Worker:

    def __init__(self, poller, heartbeat, asr, audio, should_continue):
        self.poller = poller
        self.heartbeat = heartbeat
        self.asr = asr
        self.audio = audio
        self.should_continue = should_continue

    def run(self):
        while self.should_continue():
            messages, time = self.poller.poll(1000)
            self.heartbeat.send()

            if "frontend" in messages:
                self.handle_request(messages["frontend"])

    def handle_request(self, message):
        pcm = self.get_pcm_from_message(message)
        self.asr.recognize_chunk(pcm)
        final_hypothesis = self.asr.get_final_hypothesis()
        response = self.create_response(final_hypothesis)
        self.poller.send("frontend", response)

    def get_pcm_from_message(self, message):
        return self.audio.load_wav_from_string_as_pcm(message)

    def create_response(self, final_hypothesis):
        return {
            "result": [
                {
                    "alternative": [{"confidence": c, "transcript": t} for (c, t) in final_hypothesis],
                    "final": True,
                },
            ],
            "result_index": 0,
        }


class Heartbeat:

    def __init__(self, model, address, socket):
        self.model = model
        self.address = address
        self.socket = socket

    def send(self):
        message = {
            "address": self.address,
            "model": self.model
        }

        self.socket.send_json(message)




class ASR:

    def __init__(self):
        import os
        basedir = os.path.dirname(os.path.realpath(__file__))

        self.recogniser = PyOnlineLatgenRecogniser()
        argv = ['--config=%s/models/mfcc.conf' % basedir,
                '--verbose=0', '--max-mem=10000000000', '--lat-lm-scale=15', '--beam=12.0',
                '--lattice-beam=6.0', '--max-active=5000',
                '%s/models/tri2b_bmmi.mdl' % basedir,
                '%s/models/HCLG_tri2b_bmmi.fst' % basedir,
                '1:2:3:4:5:6:7:8:9:10:11:12:13:14:15:16:17:18:19:20:21:22:23:24:25',
                '%s//models/tri2b_bmmi.mat' % basedir]
        self.recogniser.setup(argv)
        self.wst = wst2dict('%s/models/words.txt' % basedir)

    def recognize_chunk(self, chunk):
        decoded_frames = 0
        self.recogniser.frame_in(chunk)
        dec_t = self.recogniser.decode(max_frames=10)
        while dec_t > 0:
            decoded_frames += dec_t
            dec_t = self.recogniser.decode(max_frames=10)

        return self.recogniser.get_best_path()

    def get_final_hypothesis(self):
        self.recogniser.prune_final()
        utt_lik, lat = self.recogniser.get_lattice()
        self.recogniser.reset()

        return [(prob, self.path_to_text(path)) for (prob, path) in lattice_to_nbest(lat, n=10)]

    def path_to_text(self, path):
        return u' '.join([unicode(self.wst[w]) for w in path])


class AudioUtils:

    default_sample_width = 2
    default_sample_rate = 16000

    def load_wav_from_string_as_pcm(self, string):
        return self.load_wav_from_file_as_pcm(StringIO(string))

    def load_wav_from_file_as_pcm(self, path):
        return self.convert_wav_to_pcm(self.load_wav(path))

    def load_wav(self, path):
        wav = wave.open(path, 'r')
        if wav.getnchannels() != 1:
            raise Exception('Input wave is not in mono')
        if wav.getsampwidth() != self.default_sample_width:
            raise Exception('Input wave is not in %d Bytes' % def_sample_width)

        return wav

    def convert_wav_to_pcm(self, wav):
        try:
            chunk = 1024
            pcm = b''
            pcmPart = wav.readframes(chunk)

            while pcmPart:
                pcm += str(pcmPart)
                pcmPart = wav.readframes(chunk)

            return self.resample_to_default_sample_rate(pcm, wav.getframerate())
        except EOFError:
            raise Exception('Input PCM is corrupted: End of file.')

    def resample_to_default_sample_rate(self, pcm, sample_rate):
        if sample_rate != self.default_sample_rate:
            pcm, state = audioop.ratecv(pcm, 2, 1, sample_rate, self.default_sample_rate, None)

        return pcm
