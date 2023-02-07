class VoiceClientDisconnectedError(Exception):
    pass


class AudioSourceNotFoundError(Exception):
    pass


class AudioExtensionError(AudioSourceNotFoundError):
    pass


class AudioUrlError(Exception):
    pass


class UserNotInVoiceChannel(Exception):
    pass
