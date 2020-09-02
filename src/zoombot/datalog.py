######################################################################
#
# zoombot/datalog.py
# 
# Written for ENGR 028/CPSC 082: Mobile Robotics, Summer 2020
# Copyright (C) Matt Zucker 2020
#
######################################################################
#
# Class to log data and a function to read logged data from saved
# files. Underlying file format is the numpy compressed storage format
# .npz.
#
######################################################################

import sys, datetime
from collections import namedtuple

import numpy
import glfw

######################################################################

_DataLogGroup = namedtuple('DataLogGroup',
                         'names, array, idx0, idx1')

######################################################################

class DataLog:
    """Class to log data to a compressed .npz file for later plotting and
    analysis. The log can record a set of named numeric variables
    determined before logging begins. Each time the append_log_row()
    method is called, the current values of each log variable will be
    appended to the log.

    The plotter submodule expects variable names to be of the form

       plot_title.unique_id
       plot_title.extended.unique.id

    The plot_title is all of the variable name up to the first '.'
    character.  All variables with the same plot_title are grouped
    into the same plot. "Singleton variable" names of the form 

       unique_id

    are also allowed, and each will appear in its own plot. By
    convention, sets of variables whose unique identifiers are the
    same, but whose plot titles include pos_x and pos_y (and
    optionally pos_angle) are recognized as poses, and are plotted
    separately by the plotter, for example:

       pos_x.my_special_pose
       pos_y.my_special_pose
       pos_angle.my_special_pose
    """
    
    """Numpy data type mnemonics stored numerically."""
    NUMERIC_TYPES = set('bufic')

    """Number of rows of initial log file."""
    INITIAL_LOG_SIZE = 8000
    
    def __init__(self, dt=None):

        """Initialize this DataLog. The dt parameter can be a floating-point
        number or an object of type datetime.timedelta indicating the
        timestep between log rows. Or set dt to None and make sure to
        add a log variable named "time" to make sure plotting works.
        """

        self.groups = []
        self.total_variables = 0

        self.variables = dict()

        if isinstance(dt, datetime.timedelta):
            dt = dt.total_seconds()

        self.dt = dt

        self.have_time = False

        self.current_filename = None
        self.current_log = None
        self.log_rows = 0

        if dt is not None:
            self.total_variables += 1

    def add_variables(self, names, array):

        """Add a set of variables to be plotted. This method should not be
        called in between calls to begin_log() and finish(), but you
        can call it multiple times as long as logging is not active.
        Parameters:

          * names: A list of strings naming each variable. Variable
            names should be unique across the entire log, so adding
            the same name twice, even in seperate calls to
            add_variables(), is prohibited.

          * array: A flat numeric numpy.ndarray with the same length
            as names.

        In order to update the log variables, you should always assign
        to the elements of the array variable you pass to
        add_variables, not to overwrite it. For example, the following
        code will not write any non-zero data to the log:

            myarray = numpy.zeros(3)
            names = ['a', 'b', 'c']

            datalog.add_variables(names, myarray)
            datalog.begin_log()
        
            # don't do this!
            myarray = [1, 2, 3]

            datalog.append_log_row()
            datalog.write_log()

        Instead of re-assigning myarray, access its elements. Either
        of these access patterns is fine:

            myarray[:] = [1, 2, 3]

            myarray[0] = 1
            myarray[1] = 2
            myarray[2] = 3

        """

        assert isinstance(array, numpy.ndarray)
        assert array.dtype.kind in self.NUMERIC_TYPES
        assert len(array.shape) == 1
        assert len(names) == array.size
        assert not any([(name in self.variables) for name in names])
        
        nvars = len(names)
        
        idx0 = self.total_variables
        idx1 = idx0 + nvars

        group_idx = len(self.groups)

        for var_idx, name in enumerate(names):
            self.variables[name] = (group_idx, var_idx)
        
        self.groups.append(_DataLogGroup(names, array, idx0, idx1))

        self.total_variables += nvars

        if self.current_log:
            
            print('WARNING: adding variables after logging started!')
            print('  this is inefficient :(')
            print('  previous logged values for {}'.format(names[0]))
            print('  and other variables in this group will be zero.')

            self.current_log.resize(self.current_log.shape[0],
                                    self.total_variables)

    def begin_log(self):

        """Starts logging. Returns the filename of the logfile that will be
        written when write_log() is called. Note that the file will
        always be created in the current working directory where
        write_log() is called, and will be named according to the date
        and time when begin_log() is called.

        """

        assert self.current_log is None and self.log_rows == 0

        self.current_filename = datetime.datetime.now().strftime(
            'log_%Y%m%d_%H%M%S.npz')
        
        self.current_log = numpy.zeros((self.INITIAL_LOG_SIZE,
                                        self.total_variables),
                                       dtype=numpy.float32)

        return self.current_filename
            
    def append_log_row(self):

        """Appends a row to the current log by copying variables from all
        variable sets added. This method should only be called after a
        call to begin_log() and before a subsequent call to
        write_log().
        """
        
        assert self.current_log is not None

        if self.current_log.shape[0] == self.log_rows:
            self.current_log.resize(2*self.current_log.shape[0],
                                    self.total_variables)

        for g in self.groups:
            self.current_log[self.log_rows, g.idx0:g.idx1] = g.array

        self.log_rows += 1

    def write_log(self):

        """Writes the current log and returns the filename of the file that
        was written. See begin_log() for documentation on file naming
        and location.
        """

        assert self.current_log is not None

        log_names = []
        
        written_portion = self.current_log[:self.log_rows]

        if self.dt is not None:
            written_portion[:, 0] = numpy.arange(self.log_rows,
                                                 dtype=numpy.float32)*self.dt
            log_names.append('time')
        
        for g in self.groups:
            log_names.extend(g.names)

        log_names = numpy.array(log_names, dtype='U')

        numpy.savez_compressed(self.current_filename,
                               dt=self.dt,
                               names=log_names,
                               data=written_portion)

        filename_written = self.current_filename

        self.current_filename = None
        self.current_log = None
        self.log_rows = 0

        return filename_written

    def is_logging(self):
        """Returns True if begin_log() has been called without a subsequent
        write_log()."""
        return self.current_log is not None

    def finish(self):

        """Put the DataLog into a known state by calling write_log() if
        logging is active. Returns the written log filename if logging
        had been active, or None if not.
        """
        if self.current_log is not None:
            return self.write_log()
        else:
            return None

    def lookup_variable(self, name):
        """Returns the group index and the array index of the named variable,
        or None if the variable was not added to this log."""
        if name not in self.variables:
            return None
        return self.variables[name]

    def timer(self, name, denom=1.0, display=None):
        """Returns a timer object that can be used inside a Python "with"
        statement to do some basic profiling and write the result to
        the log. Example usage:

            array = numpy.zeros(1)
            datalog.add_variables(['expensive_operation_time'], array)

            datalog.begin_log()
        
            with datalog.timer('expensive_operation_time'):
               do_expensive_operation()

            datalog.append_log_row()
            datalog.write_log()

        Parameters:

          * name: the name of the previously added log variable

          * denom: a divisor (floating-point seconds) to divide the
            measured time by, useful for expressing times relative to
            a given budget duration in seconds

        """
        group_idx, var_idx = self.lookup_variable(name)
        group = self.groups[group_idx]
        return _LogTimer(group.array, var_idx, denom)

######################################################################

class _LogTimer:

    def __init__(self, array, idx, denom):
        assert idx < len(array) 
        if isinstance(denom, datetime.timedelta):
            denom = denom.total_seconds()
        self.array = array
        self.idx = idx
        self.denom = denom

    def __enter__(self):
        self.start = glfw.get_time()

    def __exit__(self, type, value, traceback):
        elapsed = glfw.get_time() - self.start
        self.array[self.idx] = elapsed / self.denom

######################################################################            

def read_log(filename, as_dict=True):

    """Read information written to a DataLog from a .npz file. Parameters:

      * filename: the filename of the log file to read.
    
      * as_dict: controls output, default is True, see below.

    The return values of this function depend on the as_dict
    parameter. 

    If as_dict is True, the function returns (dt, lookup) where dt is
    the timestep specified at log creation time (or None if not
    specified), and lookup is a dictionary mapping variable names to
    flat numpy arrays of data per timestep.

    If as_dict is False, the function returns (dt, names, data) where
    dt is the same as above, names is a list of variable names of
    length nvars, and data is a numpy array of shape (nrows, nvars).
    """
    
    npzfile = numpy.load(filename)
    
    dt = npzfile['dt']
    names = npzfile['names']
    data = npzfile['data']

    if not as_dict:
        return dt, names, data
    else:
        lookup = dict([(str(name), data[:,col]) for col, name in enumerate(names)])
        return dt, lookup
