"""
geoplot.py
----------

This visualization renders a 3-D plot of the data given the state
trajectory of a simulation, and the path of the property to render.

It generates an HTML file that contains code to render the plot
using Cesium Ion, and the GeoJSON file of data provided to the plot.

An example of its usage is as follows:
...
"""

import re
import json
import pandas as pd
import numpy as np
from string import Template
from agent_torch.core.helpers import get_by_path

# Template for generating the final HTML page with CesiumJS code embedded
geoplot_template = """ 
<!doctype html>
<html lang="en">
...
</html>
"""

# Helper function to extract a variable from a nested dictionary using a '/' separated path
def read_var(state, var):
    return get_by_path(state, re.split("/", var))


class GeoPlot:
    def __init__(self, config, options):
        # Initialize the GeoPlot engine with simulation config and visualization options
        self.config = config
        (
            self.cesium_token,
            self.step_time,
            self.entity_position,
            self.entity_property,
            self.visualization_type,
        ) = (
            options["cesium_token"],
            options["step_time"],
            options["coordinates"],
            options["feature"],
            options["visualization_type"],
        )

    def render(self, state_trajectory):
        coords, values = [], []
        
        # Extract simulation name and define output filenames
        name = self.config["simulation_metadata"]["name"]
        geodata_path, geoplot_path = f"{name}.geojson", f"{name}.html"

        # Process the state trajectory to extract final step coordinates and property values
        for i in range(0, len(state_trajectory) - 1):
            final_state = state_trajectory[i][-1]
            
            # Extract coordinates for agents
            coords = np.array(read_var(final_state, self.entity_position)).tolist()
            # Extract property/feature values for agents
            values.append(
                np.array(read_var(final_state, self.entity_property)).flatten().tolist()
            )

        # Generate timestamps for each step based on step_time interval
        start_time = pd.Timestamp.utcnow()
        timestamps = [
            start_time + pd.Timedelta(seconds=i * self.step_time)
            for i in range(
                self.config["simulation_metadata"]["num_episodes"]
                * self.config["simulation_metadata"]["num_steps_per_episode"]
            )
        ]

        # Assemble GeoJSON data: one feature per timestamp per agent
        geojsons = []
        for i, coord in enumerate(coords):
            features = []
            for time, value_list in zip(timestamps, values):
                features.append(
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [coord[1], coord[0]],  # Note: (longitude, latitude) format
                        },
                        "properties": {
                            "value": value_list[i],
                            "time": time.isoformat(),
                        },
                    }
                )
            geojsons.append({"type": "FeatureCollection", "features": features})

        # Write the assembled GeoJSON data to a file
        with open(geodata_path, "w", encoding="utf-8") as f:
            json.dump(geojsons, f, ensure_ascii=False, indent=2)

        # Render the final CesiumJS-based HTML file using the template
        tmpl = Template(geoplot_template)
        with open(geoplot_path, "w", encoding="utf-8") as f:
            f.write(
                tmpl.substitute(
                    {
                        "accessToken": self.cesium_token,
                        "startTime": timestamps[0].isoformat(),
                        "stopTime": timestamps[-1].isoformat(),
                        "data": json.dumps(geojsons),
                        "visualType": self.visualization_type,
                    }
                )
            )
