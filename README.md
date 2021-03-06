# DeNN
A deep neural network framework for denosing functional MRI(fMRI) data

===============================================================
### Instruction

### 1. Purpose of DeNN
- DeNN is a non-regression based deep learning technique for de-noising fMRI data, which is applicable for both resting state and task fMRI data.

### 2. Preprocessing
* Purpose of preprocessing

  This is a step to save a .mat file for each individual subject, which is the input data for DeNN denoising. Technically it should not be called as preprocessing. :)
* Required input files

  4D fMRI data, structural MRI data, and segmented MRI images (gray matter, white matter and cerebrospinal fluid). These images should be in the same space, either the native space or the template space.
  
  4D fMRI data should have been preprocessed with slice-timing correction, realignment. Any other preprocessing steps are optional.
* preprocessing script

  We have shared the preprocessing script (ADNI_extractsegdata.m), which we have used for ADNI data. Researchers can change the directory to their own data
### 3. DeNN denoising
Once you obtain the output file from ADNI_extractsegdata.m, DeNN can now be used for fMRI denoising. The example code how to run DeNN is test.py. 
### 3.1 Required libraries
- [Python](https://www.python.org/downloads/): Python 3 by default, the script is compiled with Python 3.5 under Windows system environment.
- [Keras](https://keras.io/): the script is compiled with Keras 2.2.4
- [Theano](http://deeplearning.net/software/theano/): the script is compiled with Theano 1.0.4
### 3.2 Functions in DeNN
*```denoise_model(tdim)```: The model used in our study to denoise ADNI data and HCP data.

*```denoise_model_general(tdim,layers_type=["tden","tdis","tdis","conv","conv","conv"],layers_size=[128,32,16,8,4,1])```: A more general framework to design DeNN denoising model, the users can flexibly specify different layers and sizes. "tden": Time-dependent fully-connected layer, "tdis": time-distributed fully-connected layer, "conv": 1-dimentional temporal convolutional layer.

*```denoise_loss(y_true,y_pred)```: The loss function designed to disentangle gray matter and non-gray matter time series. y_true is a dummy variable in our case.
### 3.3 Key code snippet in test.py
```python
import os,sys
os.environ["CUDA_VISIBLE_DEVICES"]="0"
```
Specify which GPU card to use, in case there are multiple GPU cards in the workstation.

```python
fMRIdata,c1T1,c2T1_erode,c3T1_erode = readMat.readMatVars(tempdatadir,varname=('fMRIdata','c1T1','c2T1_erode',
                                                                               'c3T1_erode'))
```
Read the .mat file from preprocessing script.

```python
from DeNN import denoise_model,denoise_loss
```
From the DeNN library import the denoise model and the loss function.

```python
model = denoise_model(tdim)
opt = Adam(lr=0.05,beta_1=0.9, beta_2 = 0.999, decay = 0.05)
model.compile(optimizer=opt,loss=denoise_loss)
```
Setup the denoising model, optimizer and compile the model.

```python
y_true = numpy.ones((nvoxel_train,tdim,2))
```
Dummy true data (True signal in fMRI data is unknown), any array with dimension matched should be fine.

```python
history = model.fit([train_c1[:,[i],:] for i in range(tdim)]+
                    [train_c23[:,[i],:] for i in range(tdim)],
                    y=y_true,batch_size = 500,validation_split=0.1,epochs = epochs)  
```
Model fitting, early stopping criteria can be specified here.

```python
fMRIdata_q_output = model.predict([fMRIdata_q[:,[i],:] for i in range(tdim)]+
                                    [fMRIdata_q[:,[i],:] for i in range(tdim)]
                                    ,batch_size=500)
```
Output the denoised fMRI data.

```matlab
load(DeNNsub,'fMRIdata_q','mask');
denoiseddata = zeros(size(fMRIdata_q,2),91,109,91);
denoisedmask = permute(mask,[3,2,1]);
denoiseddata(:,denoisedmask>0) = fMRIdata_q';
```
Transform the denoised data into 4-D using MATLAB.

### 4. Available de-noised data
We have successfully applied DeNN to de-noise 665 ADNI resting-state fMRI sessions, all the ADNI2 fMRI sessions and a small fraction of ADNI3 fMRI sessions should be covered in this de-noised dataset. If you have interest in ADNI data, we are happy to share the functional connectivity maps and graph theoretical measures (using AAL atlas). The de-noised time series would be more difficult to share because of the data size.

### 5. Questions
If you have any questions about DeNN or have difficulty to setup DeNN for your own data, please have no hesitation to contact Zhengshi Yang (yzhengshi@gmail.com).

If you have interest to the source code, please write a short description about the project and send it to Zhengshi Yang (yzhengshi@gmail.com).

### 6. Reference
Please cite the following reference if you use DeNN in your research.
* Yang et al., Disentangling time series between brain tissues improves fMRI data quality using a time-dependent deep neural network. Under review.

Other two references you may have interest:

Deep neural network for task fMRI denoising
* Yang et al., (2020) A robust deep neural network for denoising task-based fMRI data: An application to working memory and episodic memory. Medical Image Analysis, https://doi.org/10.1016/j.media.2019.101622.

Regression based deep neural network for resting state fMRI denoising
* Yang et al., (2019) Robust Motion Regression of Resting-State Data Using a Convolutional Neural Network Model. Front. Neurosci., 28 February 2019 | https://doi.org/10.3389/fnins.2019.00169.

