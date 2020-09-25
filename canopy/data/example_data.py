import canopy
import os
path = os.path.dirname(canopy.__file__)

example_data = canopy.read_file(f'{path}/data/example_data.adat')
