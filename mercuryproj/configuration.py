from configparser import ConfigParser
import os
import platformdirs

config_path = os.path.join(platformdirs.user_config_dir(appname=__package__), "config.ini")
configuration = ConfigParser()
configuration.read(config_path)
