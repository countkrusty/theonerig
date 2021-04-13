# AUTOGENERATED! DO NOT EDIT! File to edit: 11_synchro.extracting.ipynb (unless otherwise specified).

__all__ = ['get_QDSpy_logs', 'QDSpy_log', 'Stimulus', 'get_synced_file', 'unpack_stim_npy',
           'extract_spyking_circus_results', 'extract_best_pupil', 'stack_len_extraction']

# Cell
import numpy as np
import datetime
import os, glob
import csv
import re

from .io import *
from ..utils import *

def get_QDSpy_logs(log_dir):
    """Factory function to generate QDSpy_log objects from all the QDSpy logs of the folder `log_dir`"""
    log_names = glob.glob(os.path.join(log_dir,'[0-9]*.log'))
    qdspy_logs = [QDSpy_log(log_name) for log_name in log_names]
    for qdspy_log in qdspy_logs:
        qdspy_log.find_stimuli()
    return qdspy_logs

class QDSpy_log:
    """Class defining a QDSpy log.
    It reads the log it represent and extract the stimuli information from it:
      - Start and end time
      - Parameters like the md5 key
      - Frame delays
    """
    def __init__(self, log_path):
        self.log_path = log_path
        self.stimuli = []
        self.comments = []

    def _extract_data(self, data_line):
        data = data_line[data_line.find('{')+1:data_line.find('}')]
        data_splitted = data.split(',')
        data_dict = {}
        for data in data_splitted:
            ind = data.find("'")
            if type(data[data.find(":")+2:]) is str:
                data_dict[data[ind+1:data.find("'",ind+1)]] = data[data.find(":")+2:][1:-1]
            else:
                data_dict[data[ind+1:data.find("'",ind+1)]] = data[data.find(":")+2:]
        return data_dict

    def _extract_time(self,data_line):
        return datetime.datetime.strptime(data_line.split()[0], '%Y%m%d_%H%M%S')

    def _extract_delay(self,data_line):
        ind = data_line.find('#')
        index_frame = int(data_line[ind+1:data_line.find(' ',ind)])
        ind = data_line.find('was')
        delay = float(data_line[ind:].split(" ")[1])
        return (index_frame, delay)

    def _extract_name_description(self, data_line):
        return data_line[data_line.find(':')+1:].strip()

    def __repr__(self):
        return "\n".join([str(stim) for stim in self.stimuli])

    @property
    def n_stim(self):
        return len(self.stimuli)

    @property
    def stim_names(self):
        return [stim.name for stim in self.stimuli]

    def find_stimuli(self):
        """Find the stimuli in the log file and return the list of the stimuli
        found by this object."""
        with open(self.log_path, 'r', encoding="ISO-8859-1") as log_file:
            for line in log_file:
                if "Name       :" in line:
                    stim_params = {"name": self._extract_name_description(line)}
                elif "Description:" in line:
                    stim_params.update({"description": self._extract_name_description(line)})
                if "DATA" in line:
                    data_juice = self._extract_data(line)
                    if 'stimState' in data_juice.keys():
                        if data_juice['stimState'] == "STARTED" :
                            curr_stim = Stimulus(self._extract_time(line))
                            stim_params.update(data_juice)
                            curr_stim.set_parameters(stim_params)
                            self.stimuli.append(curr_stim)
                            stimulus_ON = True
                        elif data_juice['stimState'] == "FINISHED" or data_juice['stimState'] == "ABORTED":
                            curr_stim.is_aborted = data_juice['stimState'] == "ABORTED"
                            curr_stim.stop_time = self._extract_time(line)
                            stimulus_ON = False

                    elif 'userComment' in data_juice.keys():
                        pass
                        #print("userComment, use it to bind logs to records")
                    elif stimulus_ON: #Information on stimulus parameters
                        curr_stim.set_parameters(data_juice)
    #                elif 'probeX' in data_juice.keys():
            #            print("Probe center not implemented yet")
                if "WARNING" in line and "dt of frame" and stimulus_ON:
                    curr_stim.frame_delay.append(self._extract_delay(line))
                    if curr_stim.frame_delay[-1][1] > 2000/60: #if longer than 2 frames could be bad
                        print(curr_stim.name, " ".join(line.split()[1:])[:-1])
        return self.stimuli

class Stimulus:
    """Stimulus object containing information about it's presentation.
        - start_time : a datetime object)
        - stop_time : a datetime object)
        - parameters : Parameters extracted from the QDSpy
        - md5 : The md5 hash of that compiled version of the stimulus
        - name : The name of the stimulus
    """
    def __init__(self,start):
        self.start_time = start
        self.stop_time = None
        self.parameters = {}
        self.md5 = None
        self.name = "NoName"
        self.filename = ""

        self.frame_delay = []
        self.is_aborted = False

    def set_parameters(self, parameters):
        self.parameters.update(parameters)
        if "_sName" in parameters.keys():
            self.name = parameters["_sName"]
        elif "name" in parameters.keys():
            self.name = parameters["name"]
        if "stimMD5" in parameters.keys():
            self.md5 = parameters["stimMD5"]
        if "stimFileName" in parameters.keys():
            self.filename = parameters["stimFileName"].split('\\')[-1]

    def __str__(self):
        return "%s %s at %s" %(self.filename+" "*(24-len(self.filename)),self.md5,self.start_time)

    def __repr__(self):
        return self.__str__()

# Cell
def get_synced_file(stim_list_dir, stim_id):
    ''' Find the stimulus in the stimulus list directory that is temporally closest to the stimulus in the log.
        Works based on the modification time of the stimulus (i.e. expects stimulus to be compiled shortly
        before display).
        Input:
            - stim_list_dir: fullpath to stimuli, string
            - stim_id: stimulus read from QDSpy log, theonerig.synchro.extracting.Stimulus object
        Output:
            - stim: filename of the stimulus that needs loading, str
    '''
    stims = {"stim_name": [], "stim_delta": []}
    for stim_list in os.listdir(stim_list_dir):
        stim_load = datetime.datetime.fromtimestamp(int(os.path.getmtime(os.path.join(stim_list_dir, stim_list))))
        stim_present = stim_id.start_time
        # If the stimulus was compiled before display calculate difference, otherwise set to max
        stim_delta = stim_present - stim_load if stim_present > stim_load else datetime.timedelta.max
        stims["stim_name"].append(stim_list)
        stims["stim_delta"].append(stim_delta)
    # Obtain the index of the compiletime closest to the stimulus display time
    closest_stim_idx = stims["stim_delta"].index(min(stims["stim_delta"]))
    stim_fn = stims["stim_name"][closest_stim_idx]
    stim_path = os.path.join(stim_list_dir, stim_fn)
    # Sanity check
    if not stim_id.filename in stim_path:
        print("Compiled stimulus file not matching this name")
        print("stim_id: {}".format(stim_id.filename))
        print("stimulus file: {}".format(os.path.basename(stim_path)))
#         stim = [-5] # Needs to be int like all frame labels
        stim_path = os.path.join(stim_list_dir, os.path.basename(stim_path))
        stim = np.load(stim_path)
    else:
        stim = np.load(stim_path)

    # Some of the stimuli have a shape of repetition_number x stim_onset:
    if len(stim.shape) > 1:
        stim = stim.flatten()
    return stim, stim_path

# Cell
def unpack_stim_npy(npy_dir, md5_hash):
    """Find the stimuli of a given hash key in the npy stimulus folder. The stimuli are in a compressed version
    comprising three files. inten for the stimulus values on the screen, marker for the values of the marker
    read by a photodiode to get the stimulus timing during a record, and an optional shader that is used to
    specify informations about a shader when used, like for the moving gratings."""

    #Stimuli can be either npy or npz (useful when working remotely)
    def find_file(ftype):
        flist = glob.glob(os.path.join(npy_dir, "*_"+ftype+"_"+md5_hash+".npy"))
        if len(flist)==0:
            flist = glob.glob(os.path.join(npy_dir, "*_"+ftype+"_"+md5_hash+".npz"))
            res = np.load(flist[0])["arr_0"]
        else:
            res = np.load(flist[0])
        return res

    inten  = find_file("intensities")
    marker = find_file("marker")

    shader, unpack_shader = None, None
    if len(glob.glob(os.path.join(npy_dir, "*_shader_"+md5_hash+".np*")))>0:
        shader        = find_file("shader")
        unpack_shader = np.empty((np.sum(marker[:,0]), *shader.shape[1:]))

    #The latter unpacks the arrays
    unpack_inten  = np.empty((np.sum(marker[:,0]), *inten.shape[1:]))
    unpack_marker = np.empty(np.sum(marker[:,0]))

    cursor = 0
    for i, n_frame in enumerate(marker[:,0]):
        unpack_inten[cursor:cursor+n_frame] = inten[i]
        unpack_marker[cursor:cursor+n_frame] = marker[i, 1]
        if shader is not None:
            unpack_shader[cursor:cursor+n_frame] = shader[i]
        cursor += n_frame

    return unpack_inten, unpack_marker, unpack_shader

# Cell
def extract_spyking_circus_results(dir_, record_basename):
    """Extract the good cells of a record. Overlap with phy_results_dict."""
    phy_dir  = os.path.join(dir_,record_basename+"/"+record_basename+".GUI")
    phy_dict = phy_results_dict(phy_dir)

    good_clusters = []
    with open(os.path.join(phy_dir,'cluster_group.tsv'), 'r') as tsvfile:
        spamreader = csv.reader(tsvfile, delimiter='\t', quotechar='|')
        for i,row in enumerate(spamreader):
            if row[1] == "good":
                good_clusters.append(int(row[0]))
    good_clusters = np.array(good_clusters)

    phy_dict["good_clusters"] = good_clusters

    return phy_dict

# Cell
def extract_best_pupil(fn):
    """From results of MaskRCNN, go over all or None pupil detected and select the best pupil.
    Each pupil returned is (x,y,width,height,angle,probability)"""
    pupil = np.load(fn, allow_pickle=True)
    filtered_pupil = np.empty((len(pupil), 6))
    for i, detected in enumerate(pupil):
        if len(detected)>0:
            best = detected[0]
            for detect in detected[1:]:
                if detect[5]>best[5]:
                    best = detect
            filtered_pupil[i] = np.array(best)
        else:
            filtered_pupil[i] = np.array([0,0,0,0,0,0])
    return filtered_pupil

# Cell
def stack_len_extraction(stack_info_dir):
    """Extract from ImageJ macro directives the size of the stacks acquired."""
    ptrn_nFrame = r".*number=(\d*) .*"
    l_epochs = []
    for fn in glob.glob(os.path.join(stack_info_dir, "*.txt")):
        with open(fn) as f:
            line = f.readline()
            l_epochs.append(int(re.findall(ptrn_nFrame, line)[0]))
    return l_epochs