import logging
import os

FORMAT_STRING = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
logging.basicConfig(level=logging.INFO,
                    format=FORMAT_STRING)
root_path = os.path.dirname(__file__)
log_file = os.path.join(root_path, 'activity.log')
activity_handler = logging.FileHandler(log_file)
formatter = logging.Formatter(
    fmt=FORMAT_STRING,
    datefmt='%Y-%m-%d %H:%M')
activity_handler.setFormatter(formatter)
activity_handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
print('Log file iniciado')
logger.addHandler(activity_handler)
