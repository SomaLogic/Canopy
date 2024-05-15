import os

import somadata

path = os.path.dirname(somadata.__file__)

example_data = somadata.read_adat(f'{path}/data/example_data.adat')
