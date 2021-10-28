class Search:
    def __init__(self, base_url: str = "https://www.google.com/", safe: bool = True):
        self.url = base_url
        self.safe = "images" if not safe else "enabled"