#AUTOGENERATED! DO NOT EDIT! File to edit: dev/04_plotting.ipynb (unless otherwise specified).

__all__ = ['plot_2d_sta', 'plot_cross_correlation', 'plot_2d_fit']

#Cell
import matplotlib.pyplot as plt
from matplotlib import gridspec
import numpy as np

from .core import *
from .processing import *
from .utils import *
from .modelling import *

#Cell
def plot_2d_sta(sta):
    sta = np.array(sta)
    if len(sta.shape) == 2:
        sta = [sta]
    fig = plt.figure(figsize=(20,4+len(sta)//8*2))
    gs = gridspec.GridSpec(len(sta)//8 + 1, 8)
    for i, frame in enumerate(sta):
        ax1 = plt.subplot(gs[i//8, i%8])
        ax1.imshow(frame, cmap='gray',vmin=-1, vmax=1)

#Cell
def plot_cross_correlation(correlation_array, threshold=.1  ,two_sided=True, figsize=None):
    if figsize is None:
        figsize = (len(correlation_array), len(correlation_array))
    n_cell = correlation_array.shape[0]
    _min,_max = np.min(correlation_array), np.max(correlation_array)
    thresh = (_max-_min) * threshold
    fig = plt.figure(figsize=figsize)
    for i in range(n_cell):
        for j in range(i, n_cell):
            c = "#1f77b4"
            if np.max(correlation_array[i,j])-np.min(correlation_array[i,j]) > thresh:
                c = "red"
            for k in range(2 if two_sided else 1):
                if k==0:
                    ax = fig.add_subplot(n_cell,n_cell,i*n_cell+j+1, ylim=(_min,_max), label=str(i*n_cell+j+1))
                else:
                    ax = fig.add_subplot(n_cell,n_cell,j*n_cell+i+1, ylim=(_min,_max), label="b"+str(i*n_cell+j+1))
                plt.plot(correlation_array[i,j], c=c)
                plt.axis('off')
                if i == 0 and k==0:
                    ax.set_title(str(j))
                elif i == 0 and k==1:
                    ax.set_title(str(j), pad =-50, loc="left")
                elif i == j:
                    ax.set_title(str(j), pad =-50, loc="center")

#Cell
def plot_2d_fit(sta, param_d, figsize=None):
    if figsize is None:
        figsize = (4,8)
    fig = plt.figure(figsize=figsize)
    plt.subplot(1,2,1)
    plt.imshow(sta, vmin=-1,vmax=1, cmap="gray")
    plt.subplot(1,2,2)
    y_, x_ = sta.shape
    xy = np.meshgrid(range(x_), range(y_))
    plt.imshow(sum_of_2D_gaussian(xy, **param_d).reshape(y_,x_), vmin=-1,vmax=1, cmap="gray")