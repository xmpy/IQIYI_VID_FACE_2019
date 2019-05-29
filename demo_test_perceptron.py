# -*- coding: utf-8 -*-
# @Time    : 2019/5/26 13:54
# @Author  : LegenDong
# @User    : legendong
# @File    : demo_train_perceptron.py
# @Software: PyCharm
import argparse
import logging
import os
import random

import numpy as np
import torch
from torch.utils.data import DataLoader

from datasets import IQiYiVidDataset
from models import ArcFaceSubModel
from utils import check_exists, init_logging, sep_cat_qds_vid_transforms

logger = logging.getLogger(__name__)


def main(data_root, num_frame, num_attn, middle_ratio, block_num, epoch):
    load_path = './checkpoints/sub_models/demo_arcface_sub_{}_{}_{}_model_{:0>4d}.pth' \
        .format(num_attn, middle_ratio, block_num, epoch)
    assert check_exists(load_path)

    dataset = IQiYiVidDataset(data_root, 'test', 'face', transform=sep_cat_qds_vid_transforms, num_frame=num_frame)
    data_loader = DataLoader(dataset, batch_size=2048, shuffle=False, num_workers=0)

    model = ArcFaceSubModel(512 + 2, 10034 + 1, num_attn=num_attn, middle_ratio=middle_ratio, block_num=block_num)
    metric_func = torch.nn.Softmax(-1)

    logger.info('load model from {}'.format(load_path))
    state_dict = torch.load(load_path, map_location='cpu')
    model.load_state_dict(state_dict)

    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)

    logger.info('test model on {}'.format(device))

    model.eval()

    all_outputs = []
    all_video_names = []
    with torch.no_grad():
        for batch_idx, (feats, _, video_names) in enumerate(data_loader):
            logger.info('Test Model: {}/{}'.format(batch_idx, len(data_loader)))

            feats = feats.to(device)
            output = model(feats)
            output = metric_func(output)
            all_outputs.append(output.cpu())
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
    parser.add_argument('--epoch', type=int, default=100, help="the epoch num for train (default: 100)")
    parser.add_argument('--num_attn', default=1, type=int, help='number of attention block in NAN (default: 1)')
    parser.add_argument('--middle_ratio', default=2, type=int, help='ratio of middle layer (default:)')
    parser.add_argument('--block_num', default=1, type=int, help='number of perceptron block use (default: 1)')
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

    all_outputs, all_video_names = main(args.data_root, args.num_frame, args.num_attn, args.middle_ratio,
                                        args.block_num, args.epoch, )

    top100_value, top100_idxes = torch.topk(all_outputs, 100, dim=0)
    with open(result_log_path, 'w', encoding='utf-8') as f_result_log:
        with open(result_path, 'w', encoding='utf-8') as f_result:
            for label_idx in range(1, 10034):
                video_names_list = ['{}.mp4'.format(all_video_names[idx]) for idx in top100_idxes[:, label_idx]]
                video_names_str = ' '.join(video_names_list)
                f_result.write('{} {}\n'.format(label_idx, video_names_str))
                f_result_log.write('{} {}\n'.format(label_idx, video_names_str))