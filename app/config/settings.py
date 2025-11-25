from concurrent.futures import ThreadPoolExecutor

# Global variables
analyzer = None
executor = ThreadPoolExecutor(max_workers=4)
