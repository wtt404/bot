import os

def cleanup(files):
    for file in files:
        try:
            path = file.fp.name
            file.close()
            os.remove(path)
        except Exception:
            pass