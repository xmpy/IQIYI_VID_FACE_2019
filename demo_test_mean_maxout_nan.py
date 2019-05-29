# -*- coding: utf-8 -*-
# @Time    : 2019/5/27 10:19
# @Author  : LegenDong
# @User    : legendong
# @File    : demo_test_maxout_nan.py
# @Software: PyCharm
import argparse
import logging
import os
import random

import numpy as np
import torch
from torch.utils.data import DataLoader

from datasets import IQiYiVidDataset
from models import ArcFaceNanMaxOutModel
from utils import check_exists, init_logging, sep_cat_qds_vid_transforms

logger = logging.getLogger(__name__)


def main(data_root, num_frame, num_attn, moda, stuff_labels_list, epoch):
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    logger.info('test model on {}'.format(device))

    model_list = []
    for stuff_labels in stuff_labels_list:
        load_path = './checkpoints/sub_models/demo_arcface_{}_{:0>6d}_nan_maxout_model_{:0>4d}.pth' \
            .format(moda, stuff_labels, epoch)
        assert check_exists(load_path)

        model = ArcFaceNanMaxOutModel(512 + 2, 10034 + 1, num_attn=num_attn, stuff_labels=stuff_labels)
        logger.info('load model from {}'.format(load_path))
        state_dict = torch.load(load_path, map_location='cpu')

        model.load_state_dict(state_dict)
        model = model.to(device)
        model.eval()

        model_list.append(model)

    dataset = IQiYiVidDataset(data_root, 'test', moda, transform=sep_cat_qds_vid_transforms, num_frame=num_frame)
    data_loader = DataLoader(dataset, batch_size=2048, shuffle=False, num_workers=0)

    metric_func = torch.nn.Softmax(-1)

    all_outputs = []
    all_video_names = []
    with torch.no_grad():
        for batch_idx, (feats, _, video_names) in enumerate(data_loader):
            logger.info('Test Model: {}/{}'.format(batch_idx, len(data_loader)))

            feats = feats.to(device)
            output = 0.
            for model in model_list:
                temp_output = model(feats)
                temp_output = metric_func(temp_output).cpu()
                output += temp_output
            all_outputs.append(output / len(model_list))
            all_video_names += video_names

    all_outputs = torch.cat(all_outputs, dim=0)
    return all_outputs, all_video_names


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PyTorch Template')
    parser.add_argument('--data_root', default='/data/materials/', type=str,
                        help='path to load data (default: /data/materials/)')
    parser.add_argument('--device', default=None, type=str, help='indices of GPUs to enable (default: all)')
    parser.add_argument('--log_root', default='/data/logs/', type=str,
                        help='path to save log (default: /data/logs/)')
    parser.add_argument('--result_root', default='/data/result/', type=str,
                        help='path to save result (default: /data/result/)')
    parser.add_argument('--num_frame', default=40, type=int, help='size of video length (default: 40)')
    parser.add_argument('--num_attn', default=1, type=int, help='number of attention block in NAN')
    parser.add_argument('--moda', default='face', type=str, help='modal[face, head] of model train, (default: face)')
    parser.add_argument('--epoch', type=int, default=100, help="the epoch num for train (default: 100)")

    args = parser.parse_args()

    if args.device:
        os.environ["CUDA_VISIBLE_DEVICES"] = args.device

    SEED = 0
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed(SEED)

    log_root = args.log_root
    result_root = args.result_root

    result_log_path = os.path.join(log_root, 'result_log.txt')
    result_path = os.path.join(result_root, 'result.txt')
    log_path = os.path.join(log_root, 'log.txt')

    if check_exists(result_log_path):
        os.remove(result_log_path)
    if check_exists(result_path):
        os.remove(result_path)
    if check_exists(log_path):
        os.remove(log_path)

    init_logging(log_path)

    all_outputs, all_video_names = main(args.data_root, args.num_frame, args.num_attn, args.moda,
                                        (10000, 11000, 12000, 13000, 14000, 15000, 16000, 17000, 18000, 19000),
                                        args.epoch)

    top100_value, top100_idxes = torch.topk(all_outputs, 100, dim=0)
    with open(result_log_path, 'w', encoding='utf-8') as f_result_log:
        with open(result_path, 'w', encoding='utf-8') as f_result:
            for label_idx in range(1, 10034):
                video_names_list = ['{}.mp4'.format(all_video_names[idx]) for idx in top100_idxes[:, label_idx]]
                video_names_str = ' '.join(video_names_list)
                f_result.write('{} {}\n'.format(label_idx, video_names_str))
                f_result_log.write('{} {}\n'.format(label_idx, video_names_str))