#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  7 10:09:17 2018

waveform.py

Waveform anaylsis tools

14 Jun: Moved segmentation code from Wavelt to Waveform
        added wfdb integration for features
        added plotting of sample waveforms (segments) with annotations

Major dependencies:
    matlab engine
    


To implement:
    Include segment start times in the waveform/wavelet objects


Classes:
    
    ABP_class: superclass with ABP range specified
    CVP_class
    ECG_class
    
    Waveform
        Methods:
            
    CVPWaveform (subclass of Waveform)
    
    Summary
        Methods:
    
    ABPWavelet
    
    CVPWavelet
    
    
    Segment
    
    
    
    


"""

import pandas as pd
import numpy as np
import pywt
import glob
from sklearn.preprocessing import MinMaxScaler

import os.path

from sys import platform

#if 'linux' not in platform:
#    import matplotlib.pyplot as plt
#    from matplotlib.backends.backend_pdf import PdfPages
#    import seaborn as sns
#else:
#    import matplotlib
#    matplotlib.use('Agg')

import matplotlib as plt
from matplotlib.backends.backend_pdf import PdfPages
import seaborn as sns
import biosppy.signals.ecg as ecg
import matlab.engine
#if 'linux' in platform:
#    plt.use('Agg')
    
    
#%matplotlib notebook 

class ABP_class:
    ABP_hi = 300
    ABP_lo = -10
    pass

    # include wfdb code for PPV, SQI
    # include ABP specific wavelet code here too - or possibly in a separate class?

class CVP_class:
    CVP_hi = 40
    CVP_lo = -10

    # include a-wave identification
    # include wavelet based filtering
    pass

class ECG_class:
    ECG_hi = 1
    ECG_lo = -1
    
    # functions for R-peak location, HR and HRV
    

class Waveform(ABP_class, CVP_class, ECG_class):
    ABP_cols = ['AR1','AR2','AR3']
    CVP_cols = ['CVP1','CVP2']
    ECG_cols = ['I','II','III','V']
#    SQI_threshold = 0.6  # SQI below this will not be converted to wavelets
    
    def __init__(self, filename=None, start=0, duration=0, end=0, process=False, level=8, seg_channel = 'ABP'):
    # if information is supplied on initialization, read the waveform and vitals from the given file
        if filename is not None:
            print ('Initializing and reading from file {}'.format(filename))
            self.read(filename, start, duration, end)
            
        
        self.segments = {} 
        self.features = {}   # wfdb generated features for each segment
        self.seg_SQI = {}    # segment signal quality (array) - use to supress bad data before classification
        self.bad_segments = []
        self.Fs = 240 # default sample rate- should also set time constant
        self.seg_level = level
        self.seg_start_time = {}
        self.section_size = 0
        self.seg_channel = seg_channel
        
        if process:
        # automate pre-processing, segmentation, etc
            #self.rename_wfs()
            self.segmenter()
            self.check_times()
            self.wf_features()
    
    def read (self, filename, start=0, duration=0, end=0):
        # read a waveform from hdf5 file and store in self.data
        # if duration is non-zero then read from start to duration in seconds, otherwise read start->end
        # once read, drop all empty columns
        # figure out which AR and CVP columns have data and rename to ABP and CVP
        # how to specify start time?? read as date_time
        # if start is blank - read whole file
        # if duration and end are blank, read from start to the end of the file
        if start != 0:
            start_time = pd.to_datetime(start)
            if duration != 0:
                print ('Reading from {} for {} s'.format(start_time, duration))
                end_time = start_time + pd.to_timedelta(duration, 'S')
                self.waves = pd.read_hdf(filename,'Waveforms',where='index>start_time & index<end_time')
                self.vitals = pd.read_hdf(filename,'Vitals',where='index>start_time & index<end_time')
            elif end != 0:
                end_time = pd.to_datetime(end)
                print ('Reading from {} to {}'.format(start_time, end_time))
                self.waves = pd.read_hdf(filename,'Waveforms',where='index>start_time & index<end_time')
                self.vitals = pd.read_hdf(filename,'Vitals',where='index>start_time & index<end_time')
            else: 
                print ('Reading from {} to end'.format(start_time))
                self.waves = pd.read_hdf(filename,'Waveforms',where='index>start_time')
                self.vitals = pd.read_hdf(filename,'Vitals',where='index>start_time')
        else:
            print ('Reading entire file')
            self.waves = pd.read_hdf(filename,'Waveforms')
            self.vitals = pd.read_hdf(filename,'Vitals')
        
        self.waves = self.waves.dropna(axis=1,how='all')
        self.vitals = self.vitals.dropna(axis=1,how='all')
        self.clean_wfs()
    
    def wf_clean (self, channel, high, low):
        # drop rows from the dataframe if ABP in channel is out of range
        print ('Clean channel {}, drop below {} and above {}'.format(channel, low, high))
        df = self.waves
        mask = ~((df[channel]<high) & (df[channel]>low))        # boolean mask for values NOT beween High and Low
        df.loc[mask, channel] = 0 # if NaN this blows up the classifier
        self.waves = df
        self.waves.fillna(0,inplace=True)  # may want to delete the rows entirely but this will support the classifier
        
    def clean_wfs (self):
        # clean all CVP and ABP channels of out of range values
        # right now deleting all the data... maybe should just delete the ABP and CVP... or replace by NaN
        #mask = df.my_channel > 20000
        #column_name = 'my_channel'
        #df.loc[mask, column_name] = 0
        
        for x in self.waves.columns:
            if x in Waveform.ABP_cols:
#                print ('Cleaning {}'.format(x))
                self.wf_clean(x, ABP_class.ABP_hi, ABP_class.ABP_lo)
                
            elif x in Waveform.CVP_cols:
#                print ('Cleaning {}'.format(x))
                self.wf_clean(x, CVP_class.CVP_hi, CVP_class.CVP_lo)
                
            elif x in Waveform.ECG_cols:
#                print ('Cleaning {}'.format(x))
                self.wf_clean(x, ECG_class.ECG_hi, ECG_class.ECG_lo)
    
    def plot (self, channels, size):
        # plot the specified channels
        # set ranges to appropriate values
        pass
    
    def rename_wfs (self):
        # after blank columns are dropped at import, if only one ABP channel is left, rename it to ABP
        # do same for CVP
        if ('AR2' not in self.waves.columns) & ('AR3' not in self.waves.columns):
            if 'AR1' in self.waves.columns:
                print ('AR1 is ABP channel, renaming')
                self.waves.rename(columns={'AR1':'ABP'},inplace=True)
        elif ('AR1' not in self.waves.columns) & ('AR2' in self.waves.columns):
            print ('AR2 is ABP channel, renaming')
            self.waves.rename(columns={'AR2':'ABP'},inplace=True)
        elif ('AR1' not in self.waves.columns) & ('AR3' in self.waves.columns):
            print ('AR3 is ABP channel, renaming')
            self.waves.rename(columns={'AR3':'ABP'},inplace=True)
                
        if ('CVP2' not in self.waves.columns) & ('CVP1' in self.waves.columns):
            print ('CVP1 is CVP channel, renaming')
            self.waves.rename(columns={'CVP1':'CVP'},inplace=True)
        elif('CVP2' in self.waves.columns) & ('CVP1' not in self.waves.columns):
            print ('CVP2 is CVP channel, renaming')
            self.waves.rename(columns={'CVP2':'CVP'},inplace=True)
            
            
    def segmenter (self, window_multiplier=1):
        # need to adapt this to account for possibly different sampling rates
        waveform = self.waves
        level = self.seg_level
        
#        DATA_TIME_CONST = 0.004166747   #will need to adjust for MIMIC data
#        section_size = math.ceil(13.5 / DATA_TIME_CONST)
        self.section_size = int((100*2**level / 4)) * window_multiplier
        print('Segmenting waveform. Level = {}, section size = {}'.format(level, self.section_size))
        seg_idx = np.arange(0, len(waveform), self.section_size)
        self.segments = {}
        self.seg_start_time = {}
        for i in range(1, len(seg_idx)):
            try: signal = waveform.iloc[seg_idx[i-1]:seg_idx[i]][[self.seg_channel,'II']]
            except KeyError: 
                self.seg_channel = self.seg_channel.split('-')[0] 
                signal = waveform.iloc[seg_idx[i-1]:seg_idx[i]][[self.seg_channel,'II']]
            self.segments[i]=signal
            self.seg_start_time[i] = waveform.index[seg_idx[i]].round('s')
 
    def wf_features (self, SQI_threshold = 0.5):
        # use MATLAB and wfdb code to generate features df and signal quality
        feats_cols=['Sys_t','SBP','Dia_t','DBP','PP','MAP','Beat_P','mean_dyneg','End_sys_t','AUS','End_sys_t2','AUS2']
        
        eng = matlab.engine.start_matlab()
        eng.addpath(r'/.');
        eng.addpath(r'./WFDB'); 
        
        for i in range(1, len(self.segments)+1):
            seg = self.segments[i][self.seg_channel]
            seglist = seg.values.tolist()
#            print ('Processing segment {}'.format(i))
            try:
                (onsets,feats, R, QF) = eng.wabp_wrap(seglist, nargout=4)
                df = pd.DataFrame(data=np.asarray(feats),columns=feats_cols)
                self.features[i] = df
                if isinstance(QF, float): 
                    self.seg_SQI[i] = (QF)
                else: 
                     self.seg_SQI[i] = 0.0
            except:
                print('Error processing wfdb features on segment {}'.format(i))
#                print(seglist)
                self.features[i] = []
                self.seg_SQI[i] = 0.0
                
        self.bad_segments = [key for key, value in self.seg_SQI.items() if value < SQI_threshold]
        print ('Waveform processed, {} segments total \n {} segments are below the quality threshold for analysis' \
               .format(len(self.seg_SQI),len(self.bad_segments)))
        
        self.MAP = {}
        self.PPV = {}
        self.PP = {}
        self.PVI = {} # pleth variability index
        self.HR = {}
        for i in range (1, len(self.segments)+1):
            if i not in self.bad_segments:
                self.MAP[i] = self.features[i]['MAP'].mean()
                self.PPV[i] = (self.features[i]['PP'].max()-self.features[i]['PP'].min())/self.features[i]['PP'].mean()
                self.PP[i] = self.features[i]['PP'].mean()
                if 'SPO2' in self.waves.columns:
                    spo2 = self.chan_slice('SPO2', i)
                    self.PVI[i]=( spo2.max()-spo2.min() )/ spo2.max()
                    
            else:
                self.MAP[i] = 0
                self.PPV[i] = 0
                self.PP[i] = 0
                self.PVI[i]= 0
            try:
                lead1 = self.chan_slice('I',i)
                self.HR[i] = ecg.ecg(lead1.values, sampling_rate = self.Fs, show = False)[6].mean()  
            except:
                print ('Error with HR on segment {}'.format(i))
                self.HR[i] = 0
                
                
    def check_times (self):
        # look at segemnts and see if there are abnormal lengths ( longer than the mode)
        # store the result in self.bad_times
        from scipy import stats
        seg_dur = []
        
        for i in range(1, len(self.segments)+1):
            seg_dur.append(self.segments[i].index[-1]-self.segments[i].index[1])

        norm_segment = stats.mode(seg_dur)[0][0]+pd.Timedelta(np.timedelta64(10, 'ms'))
        
        self.bad_times = []
        for i in range(0, len(self.segments)):
            if seg_dur[i] > norm_segment:
                self.bad_times.append(i+1)
                print('Bad segment {} duration {}'.format(i, seg_dur[i]))
        pass
    
    def chan_slice (self, chan, seg, window_multiplier=1):
        # need to adapt this to accound for possibly different sampling rates
        # return start and end indices for the segment
        
        waveform = self.waves
        level = self.seg_level
    
#        DATA_TIME_CONST = 0.004166747   #will need to adjust for MIMIC data
#        section_size = math.ceil(13.5 / DATA_TIME_CONST)
#       print('Segmenting waveform. Level = {}, section size = {}'.format(level, section_size))
        section_size = int((100*2**level / 4)) * window_multiplier
    
        seg_idx = np.arange(0, len(waveform), section_size)
    #    start = seg_idx[seg-1]
        signal = waveform.iloc[seg_idx[seg-1]:seg_idx[seg]][chan]
    
        return signal


    def plot_seg (self, seg, chans=['ABP','CVP','II','SPO2']):
        """ plot specified segment and channels 
        channel format = ['ABP', 'CVP', 'II', 'SPO2']
        
        To do: 
            allow for range of segments: start, stop or start, number
            
        """
        
        chan_plots = []
        for chan in chans:
            if chan in self.waves.columns:
                print ('{} is available'.format(chan))
                chan_plots.append(chan)
            else:
                print ('{} is NOT available'.format(chan))
        print ('\nWe have {} channels to plot'.format(len(chan_plots)))
        
        ABP = self.segments[seg]['ABP']
        feats_df = self.features[seg]
        sys_idx = (feats_df['Sys_t'].values * 240/125).round().astype(int).transpose().tolist()
        sys_idx = (feats_df['Sys_t'].values * 240/125).round().astype(int).transpose().tolist()
        dia_idx = (feats_df['Dia_t'].values * 240/125).round().astype(int).transpose().tolist()
        
        fig, axes = plt.subplots(len(chan_plots), 1, figsize=(10,10)) # change height based on number of channels...
        fig.suptitle('Segment {0:d} with SQI {1:0.1f} Segment MAP: {2:0.1f} mmHg, PPV: {3:0.1f} % PVI: {4:0.1f}'.format(seg,     
            self.seg_SQI[seg], self.MAP[seg], self.PPV[seg]*100, self.PVI[seg]))
    
        for i, chan in enumerate (chan_plots, 1):
    #        print ('Plotting channel {} which is {}'.format(i, chan))
    #        ax = axes[i]
            if chan == 'ABP':
                ax = plt.subplot(len(chan_plots), 1, i, label=chan)
                ax.plot(ABP.index, ABP.values,'b-')
                ax.plot(ABP[sys_idx].index, feats_df['SBP'],'rv', label='SBP')
                ax.plot(ABP[dia_idx].index, feats_df['DBP'],'g^', label='DBP')
                self.segments[seg]['ABP'].plot(ax=ax)
                ax.xaxis.set_visible(False)
                ax.set_ylabel('mmHg')
                ax.legend(loc='upper right')
                ax1=ax
            elif chan in ['I','II','III','V']:
                # ECG lead so find R-peaks
                ECG_sig = self.chan_slice(chan, seg)
                R_peaks = np.array(ecg.christov_segmenter(signal=ECG_sig.values, sampling_rate=240.))[0]
    #            R_plot = pd.Series(index = lead1.index[R_peaks], data = lead1.values[R_peaks])
                R_ts = ECG_sig.index[R_peaks]
                
                ax = plt.subplot(len(chan_plots), 1, i, sharex=ax1)
                ax.plot(ECG_sig, label=chan)
                ax.plot(R_ts, ECG_sig.values[R_peaks],'r.',label='R-peak')
                ax.legend(loc='upper right')
                
            else:
                ax = plt.subplot(len(chan_plots), 1, i, sharex=ax1)
                signal = self.chan_slice (chan, seg)
                ax.plot(signal, label=chan)
                ax.legend(loc='upper right')
    #            ax.set_title(chan)


class Summary:
    
    def __init__ (self, filename=None):
        if filename is not None:
            print ('Initializing and reading from file {}'.format(filename))
            self.read(filename) 
        
    def read (self, filename):
        if os.path.isfile(filename.split('.')[0] + '.sum'):
            print('Reading .sum summary file')
            df = pd.read_hdf(filename.split('.')[0] + '.sum', key = '/Vitals_summary')
        else:
            print('No .sum summary file. Sampling vitals.')
            df = pd.read_hdf(filename, '/Vitals')
            df = df.resample('1T').mean()
        self.data = df.dropna(axis='columns',how='all').drop(['NBP-S', 'NBP-D'],axis = 'columns',errors='ignore')
        #self.rename_wfs()
        
    def plot (self):
        self.data.plot(subplots=True,figsize=(10,10))
        plt.show()
        
    def rename_wfs (self):
        # after blank columns are dropped at import, if only one ABP channel is left, rename it to ABP
        # do same for CVP
        if ('AR2-M' not in self.data.columns) & ('AR3-M' not in self.data.columns):
            if 'AR1-M' in self.data.columns:
                print ('AR1-M is ABP channel, renaming')
                self.data.rename(columns={'AR1-M':'ABP'},inplace=True)
        elif ('AR1-M' not in self.data.columns) & ('AR2-M' in self.data.columns):
            print ('AR2-M is ABP channel, renaming')
            self.data.rename(columns={'AR2-M':'ABP'},inplace=True)
        elif ('AR1-M' not in self.data.columns) & ('AR3-M' in self.data.columns):
            print ('AR3-M is ABP channel, renaming')
            self.data.rename(columns={'AR3-M':'ABP'},inplace=True)
                
        if ('CVP2' not in self.data.columns) & ('CVP1' in self.data.columns):
            print ('CVP1 is CVP channel, renaming')
            self.data.rename(columns={'CVP1':'CVP'},inplace=True)
        elif('CVP2' in self.data.columns) & ('CVP1' not in self.data.columns):
            print ('CVP2 is CVP channel, renaming')
            self.data.rename(columns={'CVP2':'CVP'},inplace=True)

class CVPWaveform(Waveform):
    def wf_features (self):
        # use MATLAB and wfdb code to generate features df and signal quality
        
        eng = matlab.engine.start_matlab()
        eng.addpath(r'/.');
        eng.addpath(r'./WFDB'); 
        
        self.PVI = {} # pleth variability index
        self.HR = {}
        for i in range (1, len(self.segments)+1):
            if i not in self.bad_segments:
                if 'SPO2' in self.waves.columns:
                    spo2 = self.chan_slice('SPO2', i)
                    self.PVI[i]=( spo2.max()-spo2.min() )/ spo2.max()
            else:
                self.PVI[i]= 0
            try:
                lead1 = self.chan_slice('I',i)
                self.HR[i] = ecg.ecg(lead1.values, sampling_rate = self.Fs, show = False)[6].mean()  
            except:
                print ('Error with HR on segment {}'.format(i))
                self.HR[i] = 0
            
class ABPWavelet (Waveform):
# ABPWavelet Class
#Contains the original wave as well as segments of the ABP waveform
# ( note: could extend this to include ECG segments if necessary)
# Also contains the transformed data in the form of energy coeffs for the WT
# Methods include transformation and clustering 

    waves = [] # dataframe

    wavelets = [] 
    
    def __init__ (self, waveform, process=True):
        self.waves = waveform.waves
        self.vitals = waveform.vitals  
        self.seg_SQI = waveform.seg_SQI    # segment signal quality (array) - use to supress bad data before classification
        self.bad_segments = waveform.bad_segments
        self.Fs = waveform.Fs
        self.seg_level = waveform.seg_level
        self.MAP = waveform.MAP
        self.HR = waveform.HR
        self.seg_start_time = waveform.seg_start_time
        self.seg_channel = waveform.seg_channel
        
        if process:
            self.processWaveform()
            self.generateFeatures()
            self.clean_bad_segs()

    @staticmethod    
    def listCreator(levels):
        new_list = []
        for i in range(levels, 0, -1):
            new_list.append(["cA{0}".format(i),"cD{0}".format(i)])
        return new_list
    
    @staticmethod
    def generateSWTCoeffs(waveform, level=7):

        db4 = pywt.Wavelet('db4')
        return pywt.swt(waveform, db4, level=level)
        #return (cA5a, cD5a), (cA4a, cD4a), (cA3a, cD3a), (cA2a, cD2a), (cA1a, cD1a) = pywt.swt(abp__signal_swt, db4, level=5)
    
    @staticmethod    
    def calcEnergy(coeff):
        return np.sqrt(np.sum(np.array(coeff ** 2)) / len(coeff))
   
    def processWaveform(self, window_multiplier=1, normalize=True):
        energy = {}
        level = self.seg_level
#        waveform = self.waves
    
        for label in self.listCreator(level):
            energy[label[0]] = []
            energy[label[1]] = []
    
        self.segmenter()
        scaler = MinMaxScaler(copy=True, feature_range=(0,1))
#       print (len(self.segments))
        for i in range(1, len(self.segments)+1):
            #signal1 = waveform.head(3200)['AR1'] should just use the segments here *****
            #signal = waveform.iloc[segments[i-1]:segments[i]]['ABP']
            signal = self.segments[i][self.seg_channel]
            if normalize:
                signal = pd.DataFrame(scaler.fit_transform(signal.to_frame()) )[0]
    
            for coeff, label in zip(self.generateSWTCoeffs(signal, level), self.listCreator(level)):
                for single_coeff, single_label in zip(coeff, label):
                    nrgCoeff = self.calcEnergy(single_coeff)
                    energy[single_label].append(nrgCoeff)
        
        
        self.wavelets = pd.DataFrame(data=energy, index = np.arange(1,len(self.segments)+1)) # fix this
        self.wavelets = self.wavelets.drop(['cA1', 'cA2', 'cA3', 'cA4', 'cA5', 'cA6', 'cA7', 'cD1', 'cD2'], axis=1)
#        return self.wavelets

#def wf_features (waveform):
    @staticmethod   
    def pre_process_mms(df):
        mms = MinMaxScaler()
#        if df is None:
#            df = self.wavelets
            
        df[df.columns] = mms.fit_transform(df[df.columns])
        
        return df
    
    def _drop_bad (self, bad_list):
        
        self.wavelets = self.wavelets.drop(bad_list)
    
    def clean_bad_segs (self):
        
        self.check_times()
        self._drop_bad(self.bad_times)
        self._drop_bad(self.bad_segments)
        
    def generateFeatures (self):
        # generate the wavelet feature dataframe (including MAP and HR)
 #       self.processWaveform()
        MAP = pd.Series(self.MAP,name='MAP')
        HR = pd.Series(self.HR,name='HR')
        
        df = self.wavelets
        df = df.join(MAP)
        df = df.join(HR)
        
        self.wltFeatures = df
        
    def plot_heatmap (self):
        # should apply some kind of scaling first
        fig, ax = plt.subplots(figsize=(10,5)) 
        sns.heatmap(self.wltFeatures.transpose(),cmap = 'jet', cbar = None)
        plt.yticks(rotation = 0)
        plt.show()
        
class CVPWavelet (Waveform):
# ABPWavelet Class
#Contains the original wave as well as segments of the ABP waveform
# ( note: could extend this to include ECG segments if necessary)
# Also contains the transformed data in the form of energy coeffs for the WT
# Methods include transformation and clustering 

    waves = [] # dataframe

    wavelets = [] 
    
    def __init__ (self, waveform, process=True):
        self.waves = waveform.waves
        self.vitals = waveform.vitals  
        self.seg_SQI = waveform.seg_SQI    # segment signal quality (array) - use to supress bad data before classification
        self.bad_segments = waveform.bad_segments
        self.Fs = waveform.Fs
        self.seg_level = waveform.seg_level
        self.HR = waveform.HR
        self.seg_start_time = waveform.seg_start_time
        self.seg_channel = waveform.seg_channel
        
        if process:
            self.processWaveform()
            self.generateFeatures()
            #self.clean_bad_segs()

    @staticmethod    
    def listCreator(levels):
        new_list = []
        for i in range(levels, 0, -1):
            new_list.append(["cA{0}".format(i),"cD{0}".format(i)])
        return new_list
    
    @staticmethod
    def generateSWTCoeffs(waveform, level=7):

        db4 = pywt.Wavelet('db4')
        return pywt.swt(waveform, db4, level=level)
        #return (cA5a, cD5a), (cA4a, cD4a), (cA3a, cD3a), (cA2a, cD2a), (cA1a, cD1a) = pywt.swt(abp__signal_swt, db4, level=5)
    
    @staticmethod    
    def calcEnergy(coeff):
        return np.sqrt(np.sum(np.array(coeff ** 2)) / len(coeff))
   
    def processWaveform(self, window_multiplier=1, normalize=True):
        energy = {}
        level = self.seg_level
#        waveform = self.waves
    
        for label in self.listCreator(level):
            energy[label[0]] = []
            energy[label[1]] = []
    
        self.segmenter()
        scaler = MinMaxScaler(copy=True, feature_range=(0,1))
#       print (len(self.segments))
    
        for i in range(1, len(self.segments)+1):
            #signal1 = waveform.head(3200)['AR1'] should just use the segments here *****
            #signal = waveform.iloc[segments[i-1]:segments[i]]['ABP']
            signal = self.segments[i][self.seg_channel]
            if normalize:
                signal = pd.DataFrame(scaler.fit_transform(signal.to_frame()) )[0]
    
            for coeff, label in zip(self.generateSWTCoeffs(signal, level), self.listCreator(level)):
                for single_coeff, single_label in zip(coeff, label):
                    nrgCoeff = self.calcEnergy(single_coeff)
                    energy[single_label].append(nrgCoeff)
        
        
        self.wavelets = pd.DataFrame(data=energy, index = np.arange(1,len(self.segments)+1)) # fix this
        self.wavelets = self.wavelets.drop(['cA1', 'cA2', 'cA3', 'cA4', 'cA5', 'cA6', 'cA7', 'cD1', 'cD2'], axis=1)
#        return self.wavelets

#def wf_features (waveform):
    @staticmethod   
    def pre_process_mms(df):
        mms = MinMaxScaler()
#        if df is None:
#            df = self.wavelets
            
        df[df.columns] = mms.fit_transform(df[df.columns])
        
        return df
    
    def _drop_bad (self, bad_list):
        
        self.wavelets = self.wavelets.drop(bad_list)
    
    def clean_bad_segs (self):
        
        self.check_times()
        self._drop_bad(self.bad_times)
        self._drop_bad(self.bad_segments)
        
    def generateFeatures (self):
        # generate the wavelet feature dataframe (including MAP and HR)
 #       self.processWaveform()
        HR = pd.Series(self.HR,name='HR')
        
        df = self.wavelets
        df = df.join(HR)
        
        self.wltFeatures = df
        
    def plot_heatmap (self):
        # should apply some kind of scaling first
        fig, ax = plt.subplots(figsize=(10,5)) 
        sns.heatmap(self.wltFeatures.transpose(),cmap = 'jet', cbar = None)
        plt.yticks(rotation = 0)
        plt.show()
 
class Segment (Waveform):

    def __init__(self, filename=None, start=0, chunksize=6400, process=False, level=8, seg_channel = 'ABP'):
    # if information is supplied on initialization, read the waveform and vitals from the given file
        self.segments = {} 
        self.features = {}   # wfdb generated features for each segment
        self.seg_SQI = {}    # segment signal quality (array) - use to supress bad data before classification
#        self.bad_segments = []
        self.Fs = 240 # default sample rate- should also set time constant
        self.seg_level = level
        self.seg_start_time = {}
        self.section_size = 0
        self.seg_channel = seg_channel
        self.ABP_chan = 'ABP'

        if filename is not None:
#            print ('Initializing and reading from file {}'.format(filename))
            self.read(filename, start, chunksize)
                         
        if process:
        # automate pre-processing, segmentation, etc
            #self.rename_wfs()
            self.wf_features()
    
    def read (self, filename, start=0, chunksize=6400):
        # read a waveform from hdf5 file and store in self.data
        # if duration is non-zero then read from start to duration in seconds, otherwise read start->end
        # once read, drop all empty columnss
        # how to specify start time?? read as date_time
        # if start is blank - read whole file
        # if duration and end are blank, read from start to the end of the file
        duration = chunksize/self.Fs
        
        if start != 0:
            start_time = pd.to_datetime(start)
            df = pd.DataFrame()
#            print ('Reading from {} for {} s'.format(start_time, duration))
#            end_time = start_time + pd.to_timedelta(duration, 'S')
            stop_time = pd.to_datetime(start_time) + pd.to_timedelta(duration, 'S')
            for chunk in pd.read_hdf(filename, '/Waveforms', chunksize=chunksize, where='index > start_time & index < stop_time'):
                df = pd.concat([df, chunk], ignore_index=False)
                
            self.waves = df[0:chunksize]
           
#            self.vitals = pd.read_hdf(filename,'Vitals',where='index>start_time & index<end_time')
        else:
            #read first segment
            pass
        
        self.waves = self.waves.dropna(axis=1,how='all')
        self.rename_wfs()
#        self.vitals = self.vitals.dropna(axis=1,how='all')
#        self.clean_wfs()
        # rename

    def rename_wfs (self):
        # after blank columns are dropped at import, if only one ABP channel is left, rename it to ABP
        # do same for CVP
        if ('AR2' not in self.waves.columns) & ('AR3' not in self.waves.columns):
            if 'AR1' in self.waves.columns:
#                print ('AR1 is ABP channel, renaming')
                self.waves.rename(columns={'AR1':'ABP'},inplace=True)
        elif ('AR1' not in self.waves.columns) & ('AR2' in self.waves.columns):
#            print ('AR2 is ABP channel, renaming')
            self.waves.rename(columns={'AR2':'ABP'},inplace=True)
        elif ('AR1' not in self.waves.columns) & ('AR3' in self.waves.columns):
#            print ('AR3 is ABP channel, renaming')
            self.waves.rename(columns={'AR3':'ABP'},inplace=True)
        
    def seg_templates (self, wave_chan='ABP', ECG_chan='II'):
        # note - need to adjust before and after to optimize this for PPG
        if wave_chan == 'ABP':
            Bstep = 0.1
            Astep = 0.7
        else:
            Bstep = 0.1
            Astep = 0.7
        
        df = self.waves
        wave = df[wave_chan]
        ecg_s = df[ECG_chan].values.reshape(1,6400)[0]
        (ts, filtered, rpeaks, templates_ts, templates, HR_ts, HR)=ecg.ecg(ecg_s, sampling_rate=240., show=False)
        templates = extract_heartbeats(signal=wave, rpeaks=rpeaks, sampling_rate=240., before=Bstep, after=Astep)
        ts = np.linspace(0,(wave.index[-1]-wave.index[0]).total_seconds()/len(templates[0]),num=len(templates[1]))
    
        return templates, ts
    
    def ABP_correlate (self):
        cor = []

        if 'ABP' in self.waves.columns:
            wave_chan = 'ABP'
            templates, ts = self.seg_templates()
            self.ABP_chan = 'ABP'
        else:
            for chan in ['AR1','AR2','AR3']:
                if chan in self.waves.columns:
                    Mean = self.waves[chan].mean()
                    if (Mean > 20) and (Mean < 200):
                        wave_chan = chan
                        self.ABP_chan = wave_chan
                        templates, ts = self.seg_templates(wave_chan)

        if len(templates) < 2:
            return 0.0

        else:
            for template in templates:
                cc=np.corrcoef(templates[0], template)[0][1]
                cor.append(cc)
            cor_arr = np.array(cor)
            self.ABP_cor_coeff = cor_arr.mean()
            return cor_arr.mean()
        
        # def correlate (array):
        # return array of correlation coefficients for each peak - option to specify peak
        # show templates
        # drop templates with low correlation values...
        
        
    def wf_features (self, SQI_threshold = 0.5):
        # use MATLAB and wfdb code to generate features df and signal quality
        feats_cols=['Sys_t','SBP','Dia_t','DBP','PP','MAP','Beat_P','mean_dyneg','End_sys_t','AUS','End_sys_t2','AUS2']
        
        eng = matlab.engine.start_matlab()
        eng.addpath(r'/.');
        eng.addpath(r'./WFDB'); 
        
        seg = self.waves[self.ABP_chan]
        seglist = seg.values.tolist()
#            print ('Processing segment {}'.format(i))
        try:
            (onsets,feats, R, QF) = eng.wabp_wrap(seglist, nargout=4)
            df = pd.DataFrame(data=np.asarray(feats),columns=feats_cols)
            self.features = df
            self.MAP = df['MAP'].mean()
            self.PP = df['PP'].mean()
            self.PPV = (self.features['PP'].max()-self.features['PP'].min())/self.features['PP'].mean()
             
            if isinstance(QF, float): 
                self.seg_SQI = (QF)
            else: 
                 self.seg_SQI = 0.0
        except:
            print('Error processing wfdb features on segment')
#                print(seglist)
            self.features = []
            self.seg_SQI = 0.0
            self.MAP = 0
            self.PP = 0
            self.PPV = 0
            
        
class Wavelet (Segment):

    waves = [] # dataframe
    wavelets = [] 
#    ABP_chan = 'ABP'
    
    def __init__ (self, waveform = [], process=True):
#        self.waves = waveform.waves
#        self.seg_start_time = waveform.seg_start_time
#        self.seg_channel = waveform.seg_channel
        self.seg_level = 8
        self.waves = waveform.waves
        self.ABP_chan = waveform.ABP_chan
        if process:
            self.processWaveform()
        
    @staticmethod    
    def listCreator(levels):
        new_list = []
        for i in range(levels, 0, -1):
            new_list.append(["cA{0}".format(i),"cD{0}".format(i)])
        return new_list
    
    @staticmethod
    def generateSWTCoeffs(waveform, level=7):

        db4 = pywt.Wavelet('db4')
        return pywt.swt(waveform, db4, level=level)
        #return (cA5a, cD5a), (cA4a, cD4a), (cA3a, cD3a), (cA2a, cD2a), (cA1a, cD1a) = pywt.swt(abp__signal_swt, db4, level=5)
    
    @staticmethod    
    def calcEnergy(coeff):
        return np.sqrt(np.sum(np.array(coeff ** 2)) / len(coeff))
   
    def processWaveform(self, window_multiplier=1, normalize=True):
        energy = {}
        level = self.seg_level
#        waveform = self.waves
    
        for label in self.listCreator(level):
            energy[label[0]] = []
            energy[label[1]] = []
    
        scaler = MinMaxScaler(copy=True, feature_range=(0,1))
#       print (len(self.segments))
        #signal1 = waveform.head(3200)['AR1'] should just use the segments here *****
        #signal = waveform.iloc[segments[i-1]:segments[i]]['ABP']
        signal = self.waves[self.ABP_chan]

        
        if normalize:
            signal = pd.DataFrame(scaler.fit_transform(signal.to_frame()) )[0]

        for coeff, label in zip(self.generateSWTCoeffs(signal, level), self.listCreator(level)):
            for single_coeff, single_label in zip(coeff, label):
                nrgCoeff = self.calcEnergy(single_coeff)
                energy[single_label].append(nrgCoeff)
        
        
        self.wavelets = pd.DataFrame(data=energy) 
        self.wavelets = self.wavelets.drop(['cA1', 'cA2', 'cA3', 'cA4', 'cA5', 'cA6', 'cA7', 'cD1', 'cD2'], axis=1)
#        return self.wavelets

#def wf_features (waveform):
    @staticmethod   
    def pre_process_mms(df):
        mms = MinMaxScaler()
#        if df is None:
#            df = self.wavelets
            
        df[df.columns] = mms.fit_transform(df[df.columns])
        
        return df        
        
def plot_summary_to_pdf(outfile, spath='./*.sum'):       
    files = glob.glob(spath)
    with PdfPages(outfile) as pdf:
        for f in files:
            print (f)
            sum_f = Summary()
            sum_f.read(f)
            sum_f.data.plot(subplots=True,figsize=(10,10),title=str(f))
            
            pdf.savefig()  # saves the current figure into a pdf page
            plt.close()

def _extract_heartbeats(signal=None, rpeaks=None, before=200, after=400):
    """Extract heartbeat templates from an ECG signal, given a list of
    R-peak locations.
    Parameters
    ----------
    signal : array
        Input ECG signal.
    rpeaks : array
        R-peak location indices.
    before : int, optional
        Number of samples to include before the R peak.
    after : int, optional
        Number of samples to include after the R peak.
    Returns
    -------
    templates : array
        Extracted heartbeat templates.
    rpeaks : array
        Corresponding R-peak location indices of the extracted heartbeat
        templates.
    """

    R = np.sort(rpeaks)
    length = len(signal)
    templates = []
    newR = []

    for r in R:
        a = r - before
        if a < 0:
            continue
        b = r + after
        if b > length:
            break
        templates.append(signal[a:b])
        newR.append(r)

    templates = np.array(templates)
    newR = np.array(newR, dtype='int')

    return templates, newR

def extract_heartbeats(signal=None, rpeaks=None, sampling_rate=240.,
                       before=0.2, after=0.4):
    """Extract heartbeat templates from an ECG signal, given a list of
    R-peak locations.
    Parameters
    ----------
    signal : array
        Input ECG signal.
    rpeaks : array
        R-peak location indices.
    sampling_rate : int, float, optional
        Sampling frequency (Hz).
    before : float, optional
        Window size to include before the R peak (seconds).
    after : int, optional
        Window size to include after the R peak (seconds).
    Returns
    -------
    templates : array
        Extracted heartbeat templates.
    rpeaks : array
        Corresponding R-peak location indices of the extracted heartbeat
        templates.
    """

    # check inputs
    if signal is None:
        raise TypeError("Please specify an input signal.")

    if rpeaks is None:
        raise TypeError("Please specify the input R-peak locations.")

    if before < 0:
        raise ValueError("Please specify a non-negative 'before' value.")
    if after < 0:
        raise ValueError("Please specify a non-negative 'after' value.")

    # convert delimiters to samples
    before = int(before * sampling_rate)
    after = int(after * sampling_rate)

    # get heartbeats
    templates, newR = _extract_heartbeats(signal=signal,
                                          rpeaks=rpeaks,
                                          before=before,
                                          after=after)

    return templates

def wave_templates (seg, wave_chan, ECG_chan='II'):
    df = seg.waves
    wave = df[wave_chan]
    ecg_s = df[ECG_chan].values.reshape(1,6400)[0]
    (ts, filtered, rpeaks, templates_ts, templates, HR_ts, HR)=ecg.ecg(ecg_s, sampling_rate=240., show=False)
    templates = extract_heartbeats(signal=wave, rpeaks=rpeaks, sampling_rate=240., before=0.1, after=0.7)
    ts = np.linspace(0,(wave.index[-1]-wave.index[0]).total_seconds()/len(templates[0]),num=len(templates[1]))

    return templates, ts