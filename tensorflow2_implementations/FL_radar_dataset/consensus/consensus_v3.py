from __future__ import absolute_import, division, print_function, unicode_literals
import numpy as np
import tensorflow as tf
import datetime
import scipy.io as sio
import math
import time
from matplotlib.pyplot import pause
import os
import glob
from tensorflow.keras import layers
from tensorflow.keras import models
import warnings

class CFA_process:

    def __init__(self, devices, ii_saved_local, neighbors, federated=True, graph=0):
        self.federated = federated # true for federation active
        self.devices = devices # number of devices
        self.ii_saved_local = ii_saved_local # device index
        self.neighbors = neighbors # neighbors number (given the network topology)
        self.graph = graph
        self.training_end = False
        if graph == 0:  # use k-degree network
            self.neighbor_vec = self.get_connectivity(ii_saved_local, neighbors, devices) # neighbor list
        else:
            mat_content = self.getMobileNetwork_connectivity(self.ii_saved_local, self.neighbors, self.devices, 0)
            self.neighbor_vec = np.asarray(mat_content[0], dtype=int)

    def getMobileNetwork_connectivity(self, ii_saved_local, neighbors, devices, epoch):
        graph_index = sio.loadmat('consensus/vGraph.mat')
        dev = np.arange(1, devices + 1)
        graph_mobile = graph_index['graph']
        set = graph_mobile[ii_saved_local, :, epoch]
        tot_neighbors = np.sum(set, dtype=np.uint8)
        sets_neighbors_final = np.zeros(tot_neighbors, dtype=np.uint8)
        counter = 0
        for kk in range(devices):
            if set[kk] == 1:
                sets_neighbors_final[counter] = kk
                counter = counter + 1
        return sets_neighbors_final

    def get_connectivity(self, ii_saved_local, neighbors, devices):
        saved_neighbors = neighbors
        if neighbors < 2:
            neighbors = 2  # set minimum to 2 neighbors
        if (ii_saved_local == 0):
            sets_neighbors_final = np.arange(ii_saved_local + 1, ii_saved_local + neighbors + 1)
        elif (ii_saved_local == devices - 1):
            sets_neighbors_final = np.arange(ii_saved_local - neighbors, ii_saved_local)
        elif (ii_saved_local >= math.ceil(neighbors / 2)) and (
                ii_saved_local <= devices - math.ceil(neighbors / 2) - 1):
            sets_neighbors = np.arange(ii_saved_local - math.floor(neighbors / 2),
                                       ii_saved_local + math.floor(neighbors / 2) + 1)
            index_ii = np.where(sets_neighbors == ii_saved_local)
            sets_neighbors_final = np.delete(sets_neighbors, index_ii)
        else:
            if (ii_saved_local - math.ceil(neighbors / 2) < 0):
                sets_neighbors = np.arange(0, neighbors + 1)
            else:
                sets_neighbors = np.arange(devices - neighbors - 1, devices)
            index_ii = np.where(sets_neighbors == ii_saved_local)
            sets_neighbors_final = np.delete(sets_neighbors, index_ii)

        if saved_neighbors < 2:
            if ii_saved_local > 0:
                neighbors_final = ii_saved_local - 1
            else:
                neighbors_final = devices - 1
        else:
            neighbors_final = sets_neighbors_final

        return neighbors_final


    def federated_weights_computing(self, neighbor, neighbors, epoch_count, eps_t_control, epoch=0, max_lag=30):
        warnings.filterwarnings("ignore")
        # max_lag = 30 # default 30
        stop_federation = False
        old_weights = self.local_weights

        neighbor_weights = []
        # seqc = random.sample(range(self.devices), self.active)

        for q in range(neighbors):
            # neighbor model and stats (train variables)
            outfile_models = 'results/dump_train_model{}.npy'.format(neighbor[q])
            outfile = 'results/dump_train_variables{}.npz'.format(neighbor[q])

            while not os.path.isfile(outfile):
                print("waiting for variables")
                pause(1)

            try:
                dump_vars = np.load(outfile, allow_pickle=True)
                neighbor_epoch_count = dump_vars['epoch_count']
                self.training_end = dump_vars['training_end']
            except:
                pause(5)
                print("retrying opening variables")
                try:
                    dump_vars = np.load(outfile, allow_pickle=True)
                    neighbor_epoch_count = dump_vars['epoch_count']
                    self.training_end = dump_vars['training_end']
                except:
                    print("halting federation")
                    stop_federation = True
                    break

            pause(round(np.random.random(), 2))
            # check file and updated neighbor frame count, max lag
            if not stop_federation:
                while not os.path.isfile(outfile_models) or neighbor_epoch_count < epoch_count - max_lag and not self.training_end:
                    # implementing consensus
                    # print("neighbor frame {} local frame {}, device {} neighbor {}".format(neighbor_frame_count, frame_count, self.ii_saved_local, neighbor[q]))
                    pause(1)
                    try:
                        dump_vars = np.load(outfile, allow_pickle=True)
                        neighbor_epoch_count = dump_vars['epoch_count']
                        self.training_end = dump_vars['training_end']
                    except:
                        pause(2)
                        print("retrying opening variables")
                        try:
                            dump_vars = np.load(outfile, allow_pickle=True)
                            neighbor_epoch_count = dump_vars['epoch_count']
                            self.training_end = dump_vars['training_end']
                        except:
                            print("problems loading variables")

                # load neighbor model
                try:
                    neighbor_weights.append(np.load(outfile_models, allow_pickle=True))
                except:
                    pause(5)
                    print("retrying opening model")
                    try:
                        neighbor_weights.append(np.load(outfile_models, allow_pickle=True))
                    except:
                        print("failed to load model federation")

                if self.training_end and len(neighbor_weights) > 0:
                    # one of the neighbors solved the optimization, apply transfer learning
                    break


        if len(neighbor_weights) > 0:
            eps_t_control = 1 / (len(neighbor_weights) + 1) # overwrite
            for q in range(len(neighbor_weights)):
                if self.training_end:
                    print("detected training end")
                    # it is reasonable to replace local model with the received one as succesful, stop model averaging with other neighbors
                    for k in range(self.layers):
                        self.local_weights[k] = neighbor_weights[-1][k]
                    break
                else: # apply model averaging
                    for k in range(self.layers):
                        self.local_weights[k] = self.local_weights[k] + eps_t_control*(neighbor_weights[q][k]-self.local_weights[k])
                        # self.local_weights[k] = self.local_weights[k] + eps_t_control * (neighbor_weights[k] - self.local_weights[k])
            del neighbor_weights

        return self.local_weights.tolist()

    def getTrainingStatusFromNeightbor(self):
        return self.training_end

    def update_local_target_model(self, model):
        self.local_weights = model
        self.layers = self.local_weights.size

    def update_local_model(self, model):
        self.local_weights = model
        self.layers = self.local_weights.size