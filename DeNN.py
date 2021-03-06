# -*- coding: utf-8 -*-
"""
Created on Thu Aug 09 17:30:34 2018
compared to v1: the first dense layer is changed to size 16
@author: Admin
"""
import os
os.environ["CUDA_VISIBLE_DEVICES"]="1"
from keras.layers import Conv1D,Input,LSTM,TimeDistributed,concatenate,Dense
from keras.models import Model
from keras.optimizers import Adam
import keras.backend as T
import sys
import scipy.io as si
import numpy
from keras.constraints import non_neg,Constraint
dense_size = 128
import h5py        
def readMatVars(filepath,varname):
    """
    varname: a tuple of variables to load
    return:
        a list of ndarray
    """
    A = h5py.File(filepath,'r')
    var = list()
    for i in range(len(varname)):
        temp = A[varname[i]].value #[()]
        var.append(temp)
    return var

def denoise_model(tdim):
    input_fMRI = [Input(shape=(1,1)) for i in range(tdim)]
    input_dwt = [Input(shape=(1,1)) for i in range(tdim)]
    shared_denseset1 = [Dense(dense_size,activation='linear') for i in range(tdim)]
    
    shared_conv1D1 = Conv1D(32,5,padding='same')
    shared_conv1D2 = Conv1D(16,5,padding='same')
    shared_tdense1 = TimeDistributed(Dense(8,activation='linear'))
    shared_tdense2 = TimeDistributed(Dense(4,activation='linear'))
    shared_tdense3 = TimeDistributed(Dense(1,activation='linear'))   
    
    denseset1_fMRI = [shared_denseset1[i](input_fMRI[i]) for i in range(tdim)]
    denseset1_dwt = [shared_denseset1[i](input_dwt[i]) for i in range(tdim)]
    merge1_fMRI = concatenate(denseset1_fMRI,axis=1)
    merge1_dwt = concatenate(denseset1_dwt,axis=1)
    
    conv1D1_fMRI = shared_conv1D1(merge1_fMRI)
    conv1D1_dwt  = shared_conv1D1(merge1_dwt)
    conv1D2_fMRI = shared_conv1D2(conv1D1_fMRI)
    conv1D2_dwt  = shared_conv1D2(conv1D1_dwt)    
    
    tdense1_fMRI = shared_tdense1(conv1D2_fMRI)
    tdense1_dwt  = shared_tdense1(conv1D2_dwt)
    
    tdense2_fMRI = shared_tdense2(tdense1_fMRI)
    tdense2_dwt  = shared_tdense2(tdense1_dwt)
    tdense3_fMRI = shared_tdense3(tdense2_fMRI)
    tdense3_dwt  = shared_tdense3(tdense2_dwt)    
    merged_data = concatenate([tdense3_fMRI,tdense3_dwt],axis = -1)
    model = Model(inputs = input_fMRI+input_dwt,outputs = merged_data)
    return model

def denoise_model_general(tdim,layers_type=["tden","tdis","tdis","conv","conv","conv"],layers_size=[128,32,16,8,4,1]):
    """
        denoise_model_general(tdim,layers_type,layers_size):
            Time-dependent fully-connected layers are required to be before all the other layers. Multiple time-dependent layers can be specified.
            layers_type: list, with element value as "tden","tdis","conv",e.g. ["tden","tdis","tdis","conv","conv","conv"]
            layers_size: list, e.g. [128,32,16,8,4,1]
    """
    input_fMRI = [Input(shape=(1,1)) for i in range(tdim)]
    input_dwt = [Input(shape=(1,1)) for i in range(tdim)]
    output_fMRI = input_fMRI
    output_dwt = input_dwt
    if len(layers_type)!=len(layers_size):
        print("error: the size for layers_type and layers_size do not match")
        return 0
    elif layers_size[-1]!=1:
        print("error: the size for the last layer has to be 1")
        return 0
    else:
        for layer_ind,layer_name in enumerate(layers_type):
            if layer_name=="tden":
                layer = [Dense(layers_size[layer_ind],activation='linear') for i in range(tdim)]
                output_fMRI = [layer[i](output_fMRI[i]) for i in range(tdim)]
                output_dwt = [layer[i](output_dwt[i]) for i in range(tdim)]
                if layer_ind==len(layers_type)-1 or layers_type[layer_ind+1]!="tden":
                    output_fMRI = concatenate(output_fMRI,axis=1)
                    output_dwt = concatenate(output_dwt,axis=1)
            elif layer_name=="conv":
                if layer_ind==0:
                    output_fMRI = concatenate(output_fMRI,axis=1)
                    output_dwt = concatenate(output_dwt,axis=1)
                layer = Conv1D(layers_size[layer_ind],5,padding='same')
                output_fMRI = layer(output_fMRI)
                output_dwt = layer(output_dwt)
            elif layer_name == "tdis":
                if layer_ind==0:
                    output_fMRI = concatenate(output_fMRI,axis=1)
                    output_dwt = concatenate(output_dwt,axis=1)
                layer = TimeDistributed(Dense(layers_size[layer_ind],activation='linear'))
                output_fMRI = layer(output_fMRI)
                output_dwt = layer(output_dwt)
        merged_data = concatenate([output_fMRI,output_dwt],axis=-1)
        model = Model(inputs = input_fMRI+input_dwt,outputs = merged_data)
        return model

def correlation_coefficient_loss(y_true, y_pred):
    xm = y_true
    y = y_pred
    my = T.mean(y,axis=-1,keepdims=True)
    ym = y-my
    r_num = T.sum(xm*ym,axis=-1)
    r_den = T.sqrt(T.sum(T.square(xm),axis=-1)* T.sum(T.square(ym),axis = -1))
    r = T.reshape(T.abs(r_num / r_den),(-1,1))
    return r

def denoise_loss(y_true,y_pred):
    output_fMRI = y_pred[:,:,0]
#    output_dwt = y_true[:,:,0]
    output_dwt  = y_pred[:,:,1]
    tdim = output_fMRI.shape[1]
    output_fMRI = output_fMRI - T.mean(output_fMRI,axis=-1,keepdims=True)
    output_dwt  = output_dwt - T.mean(output_dwt,axis = -1,keepdims=True)
    output_fMRI = output_fMRI/T.std(output_fMRI,axis=-1,keepdims=True)
    output_dwt  = output_dwt/T.std(output_dwt,axis=-1,keepdims=True)
    corr_mat = T.dot(output_fMRI,T.transpose(output_fMRI))/tdim
    corr_fMRI = T.mean(T.abs(corr_mat))/2
    corr_mat = T.dot(output_dwt,T.transpose(output_dwt))/tdim
    corr_dwt = T.mean(T.abs(corr_mat))/2    
    corr_mat = T.dot(output_fMRI,T.transpose(output_dwt))/tdim
    corr_fMRIdwt = T.mean(T.abs(corr_mat))
    return corr_fMRIdwt #corr_dwt - corr_fMRI 

def denoise_corr(y_pred):
    output_fMRI = y_pred[:,:,0]
    output_dwt  = y_pred[:,:,1]
    tdim = output_dwt.shape[1]
    output_fMRI = output_fMRI - numpy.mean(output_fMRI,axis=-1,keepdims=True)
    output_dwt  = output_dwt - numpy.mean(output_dwt,axis = -1,keepdims=True)
    output_fMRI = output_fMRI/numpy.std(output_fMRI,axis=-1,keepdims=True)
    output_dwt  = output_dwt/numpy.std(output_dwt,axis=-1,keepdims=True)
    corr_fMRI = numpy.dot(output_fMRI,output_fMRI.T)/tdim
    corr_dwt = numpy.dot(output_dwt,output_dwt.T)/tdim
    return corr_dwt,corr_fMRI
