# -*- coding: utf-8 -*-
# @Time    : 2019/5/26 13:54
# @Author  : LegenDong
# @User    : legendong
# @File    : demo_train_perceptron.py
# @Software: PyCharm
import argparse
import os
import random

import numpy as np
import torch
from torch import optim
from torch.utils.data import DataLoader

from datasets import IQiYiVidDataset
from models import FocalLoss, ArcMarginProduct, ArcFaceSubModel
from utils import check_exists, save_model, sep_cat_qds_vid_transforms


def main(args):
    if not check_exists(args.save_dir):
        os.makedirs(args.save_dir)

    dataset = IQiYiVidDataset(args.data_root, 'train', 'face', transform=sep_cat_qds_vid_transforms,
                              num_frame=args.num_frame)
    data_loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=4)

    log_step = len(data_loader) // 10 if len(data_loader) > 10 else 1

    model = ArcFaceSubModel(args.feat_dim, args.num_classes, num_attn=args.num_attn, middle_ratio=args.middle_ratio,
                            drop_prob=args.drop_prob, prelu_init=args.prelu_init, block_num=args.block_num)
    metric_func = ArcMarginProduct()
    loss_func = FocalLoss(gamma=2.)

    optimizer = optim.SGD(model.parameters(), lr=args.learning_rate, momentum=0.9, weight_decay=1e-5)
    lr_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, args.epoch)

    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)

    for epoch_idx in range(args.epoch):
        total_loss = .0
        for batch_idx, (feats, labels, _) in enumerate(data_loader):
            feats = feats.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()

            outputs = model(feats)
            outputs_metric = metric_func(outputs, labels)
            local_loss = loss_func(outputs_metric, labels)

            local_loss.backward()
            optimizer.step()

            total_loss += local_loss.item()

            if batch_idx % log_step == 0 and batch_idx != 0:
                print('Epoch: {} [{}/{} ({:.0f}%)] Loss: {:.6f}'
                      .format(epoch_idx, batch_idx * args.batch_size, len(dataset),
                              100.0 * batch_idx / len(data_loader), local_loss.item()))
        log = {'epoch': epoch_idx,
               'lr': optimizer.param_groups[0]['lr'],
               'loss': total_loss / len(data_loader)}

        for key, value in sorted(log.items(), key=lambda item: item[0]):
            print('    {:20s}: {:6f}'.format(str(key), value))

        lr_scheduler.step()

    save_model(model, args.save_dir,
               'demo_arcface_sub_{}_{}_{}_model'.format(args.num_attn, args.middle_ratio, args.block_num), args.epoch)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PyTorch Template')
    parser.add_argument('--data_root', default='/data/materials', type=str,
                        help='path to load data (default: /data/materials/)')
    parser.add_argument('--save_dir', default='./checkpoints/sub_models/', type=str,
                        help='path to save model (default: ./checkpoints/sub_models/)')
    parser.add_argument('--epoch', type=int, default=100, help="the epoch num for train (default: 100)")
    parser.add_argument('--device', default=None, type=str, help='indices of GPUs to enable (default: all)')
    parser.add_argument('--num_classes', default=10035, type=int, help='number of classes (default: 10035)')
    parser.add_argument('--batch_size', default=4096, type=int, help='dim of feature (default: 4096)')
    parser.add_argument('--feat_dim', default=512 + 2, type=int, help='dim of feature (default: 512 + 2)')
    parser.add_argument('--learning_rate', type=float, default=0.1, help="learning rate for model (default: 0.1)")
    parser.add_argument('--num_frame', default=40, type=int, help='size of video length (default: 40)')
    parser.add_argument('--num_attn', default=1, type=int, help='number of attention block in NAN (default: 1)')
    parser.add_argument('--middle_ratio', default=2, type=int, help='ratio of middle layer (default:)')
    parser.add_argument('--drop_prob', default=.5, type=float, help='prob of dropout (default: .5)')
    parser.add_argument('--prelu_init', default=.25, type=float, help='init value for a in prelu (default: .25)')
    parser.add_argument('--block_num', default=1, type=int, help='number of perceptron block use (default: 1)')
    parser.add_argument('--seed', default=0, type=int, help='random seed for all random func (default: 0)')

    args = parser.parse_args()

    if args.device:
        os.environ["CUDA_VISIBLE_DEVICES"] = args.device

    SEED = args.seed
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)

    main(args)