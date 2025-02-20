""" User interface for the MQTT plugin in the Car Connectivity application. """
from __future__ import annotations
from typing import TYPE_CHECKING

import os
from datetime import datetime, timedelta
import time

import flask
from flask_login import login_required

from carconnectivity_plugins.base.plugin import BasePlugin
from carconnectivity_plugins.base.ui.plugin_ui import BasePluginUI

if TYPE_CHECKING:
    from typing import Optional, List, Dict, Union, Literal


class PluginUI(BasePluginUI):
    """
    A user interface class for the MQTT plugin in the Car Connectivity application.
    """
    def __init__(self, plugin: BasePlugin):
        blueprint: Optional[flask.Blueprint] = flask.Blueprint(name='mqtt', import_name='carconnectivity-plugin-mqtt', url_prefix='/mqtt',
                                                                    template_folder=os.path.dirname(__file__) + '/templates')
        super().__init__(plugin, blueprint=blueprint)

        @self.blueprint.route('/', methods=['GET'])
        def root():
            return flask.redirect(flask.url_for('plugins.mqtt.status'))

        @self.blueprint.route('/status', methods=['GET'])
        @login_required
        def status():
            return flask.render_template('mqtt/status.html', current_app=flask.current_app, plugin=self.plugin,
                                         monotonic_zero=datetime.now()-timedelta(seconds=time.monotonic()))

    def get_nav_items(self) -> List[Dict[Literal['text', 'url', 'sublinks', 'divider'], Union[str, List]]]:
        """
        Generates a list of navigation items for the MQTT plugin UI.
        """
        return super().get_nav_items() + [{"text": "Status", "url": flask.url_for('plugins.mqtt.status')}]

    def get_title(self) -> str:
        """
        Returns the title of the plugin.

        Returns:
            str: The title of the plugin, which is "MQTT".
        """
        return "MQTT"
