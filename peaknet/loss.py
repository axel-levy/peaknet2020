import torch
import torch.nn as nn


class PeaknetBCELoss(nn.Module):

    def __init__(self, coor_scale=1, pos_weight=1.0):
        super(PeaknetBCELoss, self).__init__()
        self.coor_scale = coor_scale
        self.mseloss = nn.MSELoss()
        self.bceloss = None
        self.pos_weight = torch.Tensor([pos_weight])

    def forward(self, scores, targets, cutoff=0.1, verbose=False):
        if verbose:
            print("scores", scores.size())
            print("targets", targets.size())
        scores_c = scores[:, 0, :, :].reshape(-1)
        targets_c = targets[:, 0, :, :].reshape(-1)
        gt_mask = targets_c > 0
        scores_x = nn.Sigmoid()(scores[:, 2, :, :].reshape(-1)[gt_mask])
        scores_y = nn.Sigmoid()(scores[:, 1, :, :].reshape(-1)[gt_mask])
        targets_x = targets[:, 2, :, :].reshape(-1)[gt_mask]
        targets_y = targets[:, 1, :, :].reshape(-1)[gt_mask]

        pos_weight = self.pos_weight * (~gt_mask).sum().double() / gt_mask.sum().double() # p_c = negative_GT / positive_GT

        self.bceloss = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        loss_conf = self.bceloss(scores_c, targets_c)
        # loss_x = self.coor_scale * self.mseloss(scores_x, targets_x)
        # loss_y = self.coor_scale * self.mseloss(scores_y, targets_y)
        loss_x = self.mseloss(scores_x, targets_x)
        loss_y = self.mseloss(scores_y, targets_y)
        loss_coor = loss_x + loss_y
        loss = loss_conf + self.coor_scale * loss_coor # why re-multiply by coor_scale?
        with torch.no_grad():
            n_gt = targets_c.sum()
            positives = (scores_c > cutoff)
            n_p = positives.sum()
            n_tp = (positives[gt_mask]).sum()
            recall = float(n_tp) / max(1, int(n_gt))
            precision = float(n_tp) / max(1, int(n_p))
            rmsd = torch.sqrt(torch.mean((targets_x - scores_x).pow(2) + (targets_y - scores_y).pow(2)))
            if verbose:
                print("nGT", int(n_gt), "recall", int(n_tp), "nP", int(n_p), "rmsd", float(rmsd),
                      "loss", float(loss.data), "conf", float(loss_conf.data), "coor", float(loss_coor.data))
        metrics = {"loss": loss, "loss_conf": loss_conf, "loss_coor": loss_coor, "recall": recall,
                   "precision": precision, "rmsd": rmsd}
        return metrics

class PeakNetBCE1ChannelLoss(nn.Module):

    def __init__(self, coor_scale=1, pos_weight=1.0, kernel_MaxPool=3):
        super(PeakNetBCE1ChannelLoss, self).__init__()
        self.coor_scale = coor_scale
        self.bceloss = None
        padding = (kernel_MaxPool - 1)//2
        self.maxpool = nn.MaxPool2d(kernel_MaxPool, stride=kernel_MaxPool, padding=padding)
        self.pos_weight = torch.Tensor([pos_weight])

    def forward(self, scores, targets, cutoff=0.5, verbose=False, maxpool=False):
        if maxpool:
            scores = self.maxpool(scores)
            targets = self.maxpool(targets)
        scores_c = scores[:, 0, :, :].reshape(-1)
        targets_c = targets[:, 0, :, :].reshape(-1)
        gt_mask = targets_c > 0

        pos_weight = self.pos_weight * (~gt_mask).sum().double() / gt_mask.sum().double()
        self.bceloss = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        loss = self.bceloss(scores_c, targets_c)

        with torch.no_grad():
            n_gt = targets_c.sum()
            positives = (scores_c > cutoff)
            n_p = positives.sum()
            n_tp = (positives[gt_mask]).sum()
            recall = float(n_tp) / max(1, int(n_gt))
            precision = float(n_tp) / max(1, int(n_p))
            if verbose:
                print("nGT", int(n_gt), "recall", int(n_tp), "nP", int(n_p), "loss", float(loss.data))
        metrics = {"loss": loss, "recall": recall, "precision": precision}
        return metrics

class PeaknetMSELoss(nn.Module):
    
    def __init__(self, coor_scale=1, obj_scale=5, noobj_scale=1):
        super(PeaknetMSELoss, self).__init__()
        self.coor_scale = coor_scale
        self.obj_scale = obj_scale
        self.noobj_scale = noobj_scale
        
    def forward(self, scores, targets, cutoff=0.1, verbose=False):
        n = scores.size(0)
        m = scores.size(1)
        h = scores.size(2)
        w = scores.size(3)
        scores_c = nn.Sigmoid()(scores[:, 0, :, :].reshape(-1))
        targets_c = targets[:, 0, :, :].reshape(-1)
        if m > 1:
            scores_x = nn.Sigmoid()(scores[:, 2, :, :].reshape(-1))
            scores_y = nn.Sigmoid()(scores[:, 1, :, :].reshape(-1))
            targets_x = targets[:, 2, :, :].reshape(-1)
            targets_y = targets[:, 1, :, :].reshape(-1)
        loss_obj = self.obj_scale * nn.MSELoss()(scores_c[targets_c > 0.5], targets_c[targets_c > 0.5])
        loss_noobj = self.noobj_scale * nn.MSELoss()(scores_c[targets_c < 0.5], targets_c[targets_c < 0.5])
        if m > 1:
            loss_x = self.coor_scale * nn.MSELoss()(scores_x[targets_c > 0], targets_x[targets_c > 0])
            loss_y = self.coor_scale * nn.MSELoss()(scores_y[targets_c > 0], targets_y[targets_c > 0])
            loss = self.obj_scale * loss_obj + self.noobj_scale * loss_noobj + self.coor_scale * (loss_x + loss_y)
        else:
            loss = self.obj_scale * loss_obj + self.noobj_scale * loss_noobj
        with torch.no_grad():
            n_gt = targets_c.sum()
            mask = torch.zeros_like(scores_c)
            mask[scores_c > cutoff] = 1
            n_p = mask.sum()
            tp = torch.zeros_like(scores_c)
            tp[mask*targets_c > 0.5] = 1
            n_tp = tp.sum()
            recall = float(n_tp/n_gt)
            precision = float(n_tp/n_p)
            if verbose:
                if m > 1:
                    print("nGT", float(n_gt.data), "recall", float(n_tp.data), "loss", float(loss.data),
                          "x", float(loss_x.data), "y", float(loss_y.data),
                          "obj", float(loss_obj.data), "noobj", float(loss_noobj.data))
                else:
                    print("nGT", float(n_gt.data), "recall", float(n_tp.data), "loss", float(loss.data),
                          "obj", float(loss_obj.data), "noobj", float(loss_noobj.data))
        return loss, recall, precision
