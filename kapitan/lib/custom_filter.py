import base64

def custom_filter(string):
    return base64.b64encode(string.encode("UTF-8")).decode("UTF-8")