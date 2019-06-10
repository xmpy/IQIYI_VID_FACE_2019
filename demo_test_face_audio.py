# -*- coding: utf-8 -*-
# @Time    : 2019/6/10 12:23
# @Author  : LegenDong
# @User    : legendong
# @File    : demo_test_face_audio.py
# @Software: PyCharm
import argparse
import logging
import os
import random

import numpy as np
import torch
from torch.utils.data import DataLoader

from datasets import IQiYiFaceAudioDataset
from models import ArcFaceAudioModel
from utils import check_exists, init_logging

logger = logging.getLogger(__name__)


def main(face_root, scene_root):
    load_path = './checkpoints/demo_arcface_face+audio_nan_model_0100.pth'
    assert check_exists(load_path)

    dataset = IQiYiFaceAudioDataset(face_root, scene_root, 'test', num_frame=40, )
    data_loader = DataLoader(dataset, batch_size=16384, shuffle=False, num_workers=0)

    model = ArcFaceAudioModel(512 + 2, 512, 10034 + 1, )
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
        for batch_idx, (feats1, feats2, _, video_names) in enumerate(data_loader):
            logger.info('Test Model: {}/{}'.format(batch_idx, len(data_loader)))

            feats1 = feats1.to(device)
            feats2 = feats2.to(device)
            output = model(feats1, feats2)
            output = metric_func(output)
            all_outputs.append(output.cpu())
            all_video_names += video_names

    all_outputs = torch.cat(all_outputs, dim=0)
    return all_outputs, all_video_names


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PyTorch Template')
    parser.add_argument('--face_root', default='/data/materials', type=str,
                        help='path to load data (default: /data/materials/)')
    parser.add_argument('--scene_root', default='./scene_feat', type=str,
                        help='path to load data (default: /data/materials/)')
    parser.add_argument('--save_dir', default='./checkpoints/', type=str,
                        help='path to save model (default: ./checkpoints/)')
    parser.add_argument('--log_root', default='/data/logs/', type=str,
                        help='path to save log (default: /data/logs/)')
    parser.add_argument('--result_root', default='/data/result/', type=str,
                        help='path to save result (default: /data/result/)')
    parser.add_argument('--device', default=None, type=str, help='indices of GPUs to enable (default: all)')

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

    init_logging(log_path)

    all_outputs, all_video_names = main(args.face_root, args.scene_root)

    top100_value, top100_idxes = torch.topk(all_outputs, 100, dim=0)
    with open(result_log_path, 'w', encoding='utf-8') as f_result_log:
        with open(result_path, 'w', encoding='utf-8') as f_result:
            for label_idx in range(1, 10034 + 1):
                video_names_list = ['{}.mp4'.format(all_video_names[idx]) for idx in top100_idxes[:, label_idx]]
                video_names_str = ' '.join(video_names_list)
                f_result.write('{} {}\n'.format(label_idx, video_names_str))
                f_result_log.write('{} {}\n'.format(label_idx, video_names_str))