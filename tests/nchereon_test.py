import sys
sys.path.insert(0, '../')

import os

import pytest
import numpy as np
import arrow

import GliderNetCDF

NCFILENAME = 'test%02d.nc'
CreatedFiles = []

@pytest.fixture
def generate_data():
    # Create some data
    t_base = arrow.get("2014-08-12T12:00").timestamp()
    t_long = np.arange(1000, dtype='float') + t_base
    t_short = np.arange(100, dtype='float') + t_base

    z = np.arange(0, 50, 0.1)

    v_long_1d = np.ones_like(t_long)
    v_short_1d = np.ones_like(t_short)
    
    v_short_2d = np.ones((t_short.shape[0], z.shape[0]), dtype=float)
    for i, _t in enumerate(t_short):
        v_short_2d[i,:] *= i
    data = dict(t_long=t_long, t_short=t_short, v_long_1d=v_long_1d, v_short_1d=v_short_1d, v_short_2d=v_short_2d, z=z)
    return data


@pytest.fixture
def read_nc_file():
    def _read_nc_file(i):
        filename = NCFILENAME%(i)
        nc = GliderNetCDF.ncHereon(filename, mode='r')
        yield nc
        nc.close()
    return _read_nc_file
    

def test_create_file_00(generate_data):
    data = generate_data
    filename = NCFILENAME%(0)
    conf = GliderNetCDF.ncHereon.get_default_conf()
    conf['title']='test file'
    conf['source']='nchereon_test.py'
    conf['description']='Some test data'

    nc = GliderNetCDF.ncHereon(filename, mode='w', **conf)
    nc.add_parameter("v_long_1d", "-", data["t_long"], data["v_long_1d"],
                     standard_name="1D parameter (long time series).")
    nc.close()
    CreatedFiles.append(filename)
    
def test_create_file_01(generate_data):
    data = generate_data
    filename = NCFILENAME%(1)
    conf = GliderNetCDF.ncHereon.get_default_conf()
    conf['title']='test file'
    conf['source']='nchereon_test.py'
    conf['description']='Some test data'

    with GliderNetCDF.ncHereon(filename, mode='w', **conf) as nc:
        nc.add_parameter("v_long_1d", "-", data["t_long"], data["v_long_1d"],
                         standard_name="1D parameter (long time series).")
        nc.add_parameter("short_timeseries/v_short_1d", "-", data["t_short"], data["v_short_1d"],
                         standard_name="1D parameter (short time series).")
    CreatedFiles.append(filename)
    
def test_create_file_02(generate_data):
    data = generate_data
    filename = NCFILENAME%(2)
    conf = GliderNetCDF.ncHereon.get_default_conf()
    conf['title']='test file'
    conf['source']='nchereon_test.py'
    conf['description']='Some test data'

    with GliderNetCDF.ncHereon(filename, mode='w', **conf) as nc:
        nc.add_parameter("v_long_1d", "-", data["t_long"], data["v_long_1d"],
                         standard_name="1D parameter (long time series).")
        nc.add_parameter("short_timeseries/v_short_1d", "-", data["t_short"], data["v_short_1d"],
                         standard_name="1D parameter (short time series).")
        nc.add_parameter("short_timeseries/v_short_2d", "-", data["t_short"], data['z'], data["v_short_2d"],
                         standard_name="1D parameter (short time series).")
    CreatedFiles.append(filename)

def test_read_file_root_parameter(read_nc_file):
    for nc in read_nc_file(0): # reads the second nc file using the pytest.fixture factory using a generator.
        t, v = nc.get("v_long_1d")
        assert t.shape[0] == 1000
        assert t.shape[0] == v.shape[0]

        
def test_read_file_group_parameter(read_nc_file):
    for nc in read_nc_file(1): # reads the second nc file using the pytest.fixture factory using a generator.
        t, v = nc.get("short_timeseries/v_short_1d")
        assert t.shape[0] == 100
        assert t.shape[0] == v.shape[0]

def test_read_file_group_parameter_2d(read_nc_file):
    for nc in read_nc_file(2): # reads the second nc file using the pytest.fixture factory using a generator.
        t, z, v = nc.get("short_timeseries/v_short_2d")
        assert t.shape[0] == 100
        assert z.shape[0] == 500
        assert v.shape == (t.shape[0], z.shape[0])

def test_read_file_multi_parameters(read_nc_file):
    for nc in read_nc_file(2): # reads the second nc file using the pytest.fixture factory using a generator.
        p1, p2 = nc.get("v_long_1d", "short_timeseries/v_short_2d")
        assert p1[0].shape[0] == 1000
        assert p1[0].shape[0] == p1[1].shape[0]
        assert p2[0].shape[0] == 100
        assert p2[1].shape[0] == 500
        assert p2[2].shape == (p2[0].shape[0], p2[1].shape[0])



# Removes all test files. Should be run LAST!        
def test_delete_files():
    while CreatedFiles:
        os.unlink(CreatedFiles.pop())
    
if __name__ == "__main__":
    pytest.main(["--pdb", "-s"])
