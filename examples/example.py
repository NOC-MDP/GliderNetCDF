import numpy as np

import HZGnetcdf

conf = HZGnetcdf.ncHZG.get_default_conf()
conf['title']='example'
conf['source']='example.py'
conf['description']='Example description'
nc = HZGnetcdf.ncHZG('example.nc', mode='w', **conf)

t = np.arange(100)
lat = np.linspace(54, 55, 100)

nc.add_parameter("latitude", "degree north", t, lat)

nc.close()
