from itertools import chain
import os
import numpy as np
from netCDF4 import Dataset
import arrow



class ncHereon(object):
    ''' Minimal implementation of NetCDF file adhering to Hereon specs

    Parameters
    ----------
    filename : string
         name of netcdf file
    title : string
         title attribute
    source : string
         source attribute
    originator : string
         originator attribute
    contact : string
         contact attribute
    crs : string ('WSG84')
         coordinate system attribute
    **meta_data : additional config parameters, optional
         additional keyword/value pairs that are added to the global attributes
         list of the NetCDF file.
    
    Note
    ----
    This class can (should) be used using a context manager.

    Example
    -------
    >>> with ncHereon("test.nc", **conf) as nc:
    >>>     nc.add_parameter("latitude", "degree north", velocity.t, velocity.lat)
    >>>     nc.add_parameter("longitude", "degree east", velocity.t, velocity.lon)
    >>>     nc.add_parameter("eastward current", "m/s" , velocity.t, velocity.z, velocity.u)
    >>>     nc.add_parameter("northward current", "m/s" , velocity.t, velocity.z, velocity.v)
    >>>     nc.add_parameter("upward current", "m/s" , velocity.t, velocity.z, velocity.w)
    '''
    def __init__(self, filename, mode='r', title="", source="", originator="", contact="", crs='WGS84', **meta_data):
        self.dataset = Dataset(filename, mode=mode)
        self.groups = dict(root = self.dataset)
        self.dims = dict(root = {})
        if mode=='w':
            self.initialise_dataset(title, source, originator, contact, crs, **meta_data)
            
    def initialise_dataset(self, title="", source="", originator="", contact="", crs='WGS84', **meta_data):
        self.dataset.conventions = "CF-1.8"
        self.dataset.institution = "Helmholtz-Zentrum Hereon, Institute of Coastal Systems, Germany"
        self.dataset.title = title
        self.dataset.source = source
        self.dataset.originator = originator
        self.dataset.contact = contact
        self.dataset.creation_date=arrow.utcnow().format("YYYY-MM-DDTHH:MM:SS")
        for k, v in meta_data.items():
            if isinstance(v, (bool, int)):
                v = np.int32(v)
            elif isinstance(v, float):
                v = np.float(v)
            self.dataset.__setattr__(k, v)

    @staticmethod
    def get_default_conf():
        ''' Returns a prefilled configuration dictionary '''
        conf = dict(title="tbd",
                    source="tbd",
                    originator="Lucas Merckelbach",
                    contact="lucas.merckelbach@hzg.de")
        return conf
        
    def add_meta_variable(self, name, unit, value, dtype='f4'):
        ''' Add a meta variable

        Add a meta variable to the netCDF file. 

        A name can have a path-like structure to mimic groups. For example:
        
        name="gps/lat" 
        
        to create a group with its own time base.
        
        Parameters
        ----------
        name : str
            name of variable
        unit : str
            unit of variable
        value : float
            variable's value
        '''
        v = self.dataset.createVariable(name, dtype, dimensions=())
        v.unit = unit
        v[...] = value
            
    def add_parameter(self, name, unit, *v, standard_name=None, time_dimension=None):
        ''' Add a parameter
        
        Parameters
        ----------
        name : string 
            name of variable
        unit : string
            unit of variable
        *v : list of arrays, length 2 or 3
             (time, values), or (time, z, values)
        standard_name : str, optional
            standard name or long descriptive name of variable.
        time_dimension : {None, str}, optional (None)
            specify time dimension to use. If not set "T" will be used.
        '''
        time_dimension = time_dimension or "T"
        grp_name, param_name = self._get_group_and_parameter_name(name)
        grp = self._check_for_group(grp_name)
        if len(v) == 2:
            self._check_for_time_dimension(v[0], name, time_dimension)
            var = grp.createVariable(param_name, "f8", dimensions=(time_dimension,))
            var.units = unit
            var[:] = v[1]
        elif len(v) == 3:
            self._check_for_time_dimension(v[0], name, time_dimension)
            self._check_for_z_dimension(v[1], name)
            var = grp.createVariable(param_name, "f8", dimensions=(time_dimension, "Z"))
            var.units = unit
            var[...] = v[2]
        else:
            raise ValueError("Variable type not supported.")
        if not standard_name is None:
            var.standard_name = standard_name

    
    def close(self):
        ''' Closes netcdf file'''
        self.dataset.close()

    def get(self, parameter, *p):
        r = []
        for _p in chain([parameter], p):
            r.append(self._get(_p))
        if len(r)==1:
            return r[0]
        else:
            return r

    def _get(self, parameter):
        grp_name, param_name = self._get_group_and_parameter_name(parameter)
        if grp_name == "root":
            grp = self.dataset
        else:
            grp = self.dataset[grp_name]
        v = grp.variables[param_name]
        if v.dimensions == ('T',):
            r = (grp.variables['time'][...],
                 v[...])
        elif v.dimensions == ('T','Z'):
            r = (grp.variables['time'][...],
                 grp.variables['z'][...],
                 v[...])
        return r
    
    def __enter__(self, *p):
        return self

    def __exit__(self, *p):
        self.dataset.close()
        
            
    def _check_for_time_dimension(self,t, name, time_dimension):
        grp_name, _ = self._get_group_and_parameter_name(name)
        grp = self.groups[grp_name]
        if not time_dimension in self.dims[grp_name].keys():
            dim = grp.createDimension(time_dimension, size=None)
            self.dims[grp_name][time_dimension] = dim
            var = grp.createVariable("time", "f8", dimensions=(time_dimension,))
            var.units = 'seconds since 1-1 1970 00:00:00'
            var.standard_name = 'time'
            var[:] = t

    def _check_for_z_dimension(self, z, name):
        grp_name, _ = self._get_group_and_parameter_name(name)
        grp = self.groups[grp_name]
        if not "Z" in self.dims[grp_name].keys():
            dim = grp.createDimension("Z", size=len(z))
            self.dims[grp_name]["Z"] = dim
            var = grp.createVariable('z', "f8", dimensions=("Z",))
            var.units = 'm'
            var.standard_name = 'depth'
            var.long_name = 'water depth relative to sea surface'
            var.positive='down'
            var[:] = z

    def _check_for_group(self, groupname):
        if groupname not in self.groups:
            group = self.groups['root'].createGroup(groupname)
            self.groups[groupname] = group
            self.dims[groupname] = {}
        return self.groups[groupname]
        
    def _get_group_and_parameter_name(self, name):
        grp, param = os.path.split(name)
        grp = grp or 'root'
        return grp, param
    
class ncGliderFlight(ncHereon):
    ''' Minimal implementation of NetCDF file adhering to Hereon specs
        specialised to store GliderFlight data.

    Parameters
    ----------
    filename : string
         name of netcdf file
    title : string
         title attribute
    source : string
         source attribute
    originator : string
         originator attribute
    contact : string
         contact attribute
    crs : string ('WSG84')
         coordinate system attribute
    **meta_data : additional config parameters, optional
         additional keyword/value pairs that are added to the global attributes
         list of the NetCDF file.
    
    Note
    ----
    This class can (should) be used using a context manager.
    '''
    def __init__(self, filename, mode='w', title="", source="", originator="", contact="", crs='WGS84', **meta_data):
        super().__init__(filename, mode, title, source, originator, contact, crs, **meta_data)

    def write_glider_flight_parameters(self, GM, calibration_result):
        '''
        '''
        group = 'glider_flight'
        tdim = 'Tgf'
        for p in GM.parameters:
            if p in calibration_result.keys():
                continue # need to write this as time variable.
            unit = GM.parameter_units[p]
            value = GM.__dict__[p]
            self.add_meta_variable(f"{group}/{p}", unit, value)
        for p in calibration_result.keys():
            if p == 't':
                continue
            unit = GM.parameter_units[p]
            self.add_parameter(f"{group}/{p}", unit, calibration_result['t'], calibration_result[p], time_dimension=tdim)
        
    def write_thermal_lag_coefs(self, thermal_lag_coefs):
        group="thermal_lag_coefs"
        units = ["-", "s", "s"]
        names = ["alpha", "beta", "tau"]
        for p, v, u in zip(names, thermal_lag_coefs, units):
            self.add_meta_variable(f"{group}/{p}", u, v)

    def write_model_results(self, model_result):
        parameters = "u w U alpha pitch ww heading depth lat lon density SA CT pot_density buoyancy_change".split()
        units = ["m s^{-1}", "m s^{-1}", "m s^{-1}","rad", "rad", "m s^{-1}", "rad", "m", "decimal degree", "decimal degree", 
                 "kg m^{-3}", "kg kg^{-1}","degree Celcius", "kg m^{-3}", "cc"]
        long_names = ["horizontal velocity relative to water (in flight direction)",
                      "vertical velocity relative to water",
                      "speed through water", 
                      "angle of attack",
                      "pitch angle",
                      "vertical water velocity",
                      "heading angle",
                      "depth", 
                      "latitude",
                      "longitude",
                      "in-situ density",
                      "absolute salinity",
                      "conservative temperature",
                      "potential density",
                      "buoyancy_change"]
        t = model_result.t
        for p, u, ln, v in zip(parameters, units, long_names, model_result[1:]):
            self.add_parameter(p, u, t, v, standard_name=ln)
