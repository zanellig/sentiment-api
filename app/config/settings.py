from concurrent.futures import ThreadPoolExecutor

# Global variables
analyzer = {}
executor = ThreadPoolExecutor(max_workers=4)
LANG = "es"