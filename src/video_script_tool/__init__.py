# We do not import `core` here because this significantly slows down
# response-time on the command line for all commands which live outside core

from .release import __version__
