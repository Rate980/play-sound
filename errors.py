class VoiceClientDisconnectedError(Exception):
    pass


class AudioSourceNotFoundError(Exception):
    pass


class AudioExtensionError(AudioSourceNotFoundError):
    pass
