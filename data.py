# -*- coding: utf-8 -*-
"""
Created on Tue Nov 27 14:11:07 2018

@author: tinyAdapter
"""
#%%
from PIL import Image
import os
import numpy as np
import random

g_rand = random.Random(17134)

def get_file_paths(dir_name):
    return [f for f in os.listdir(dir_name)]

def pick_random_paths(paths, num):
    pick = []
    for i in range(num):
        pick_index = g_rand.randint(0, len(paths)-i-1)
        pick.append(paths[pick_index])
        paths.remove(pick[i])
    return pick

def get_numpy_data(dir_name, paths):
    result = []
    for path in paths:
        print("processing %s" % path
        , end="\r")
        im = Image.open(os.path.join(dir_name, path))
        in_data = np.asarray(im, dtype=np.int32)
        result.append(in_data)
    result = np.array(result)
    print("")
    return result


if __name__ == "__main__":
    np.set_printoptions(threshold=np.inf)

    # dir_name = "C:\\AI\\baogaojieshu"
    # paths = get_file_paths(dir_name)
    # pick_paths = pick_random_paths(paths, 10000)
    # remain_paths = paths
    # data = get_numpy_data(dir_name, pick_paths)
    # np.save("%s_train.npy" % dir_name, data)

    # data = get_numpy_data(dir_name, remain_paths)
    # np.save("%s_test.npy" % dir_name, data)

    # dir_name = "C:\\AI\\y"
    # data = get_numpy_data(dir_name, pick_paths)
    # np.save("%s_train.npy" % dir_name, data)

    # data = get_numpy_data(dir_name, remain_paths)
    # np.save("%s_test.npy" % dir_name, data)

    dir_name = "C:\\AI\\baogaojieshu"
    paths = get_file_paths(dir_name)
    data = get_numpy_data(dir_name, paths)
    np.save("%s_test.npy" % dir_name, data)
