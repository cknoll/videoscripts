
class TextExtractor:

    def __init__(self, args):
        self.url = args.url

    def perform_text_extraction(self):
        print("mockup", self.url)


def extract_text(args):

    te = TextExtractor(args)
    te.perform_text_extraction()
