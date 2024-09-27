from importlib.resources import files
import json
import logging
import logging.config
import logging.handlers
import os
from configparser import ConfigParser
from platformdirs import user_config_dir, user_log_dir

config_fn = "config.ini"
config_dir = user_config_dir(appname=__package__)
logging_dir = user_log_dir(appname=__package__)
logging_configs = str(files("mercuryproj.logging_configs").joinpath("configs.json"))


def setup_logger():
    with open(str(files("mercuryproj.logging_configs").joinpath("configs.json")), mode='r') as f:
        config = json.load(f)
    logger = logging.getLogger("mercury")
    logging.config.dictConfig(config)


if not os.path.exists(config_dir):
    logging.warning(f"Configuration dir {config_dir} does not exist. Creating it now.")
    os.makedirs(config_dir)

config_path = os.path.join(config_dir, config_fn)

if not os.path.exists(config_path):
    logging.error("No configuration file found! Initializing from sample...")
    sample_config_fn = "config_sample.ini"
    sample_config_path = str(files("mercuryproj.samples").joinpath(sample_config_fn))
    import shutil
    shutil.copy(sample_config_path, config_path)
    logging.info(f"Blank configuration file initialized at {config_path}. Exiting.")
    import sys
    sys.exit(1)

configuration = ConfigParser()
paths_read = configuration.read(config_path)

if paths_read:
    logging.info(f"Read configuration from {config_path}")
else:
    logging.error(f"No configuration contente parsed: {config_path}")
    import sys
    sys.exit(1)

setup_logger()
