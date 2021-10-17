from datetime import datetime


QUALITY_TRESHOLD = 1.0

# w niedziele przepuszczaj wszystkie newsy
if datetime.now().weekday() == 6:
    QUALITY_TRESHOLD = 10000.0
