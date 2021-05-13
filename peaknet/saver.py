import numpy as np

class Saver():
    def __init__(self, saver_type, params):
        self.saver_type = saver_type
        if saver_type == "precision_recall":
            print("Precision and recall will be saved in saved_outputs directory.")
            self.content = {"params": params, "precision": [], "recall": [], "loss": []}
        elif saver_type == "precision_recall_evaluation":
            print("Precision and recall will be saved in saved_outputs directory.")
            self.content = {"precision": [], "recall": []}
        elif saver_type is None:
            print("Data will not be save in saved_outputs directory.")

    def upload(self, metrics):
        if self.saver_type == "precision_recall":
            self.content["precision"].append(float(metrics["precision"]))
            self.content["recall"].append(float(metrics["recall"]))
            self.content["loss"].append(float(metrics["loss"].data.cpu()))
        elif self.saver_type == "precision_recall_evaluation":
            self.content["precision"].append(float(metrics["precision"]))
            self.content["recall"].append(float(metrics["recall"]))

    def save(self, save_name):
        if self.saver_type is not None:
            filename = 'saved_outputs/' + save_name + '.npy'
            print("Saving at " + filename)
            np.save(filename, self.content)
            print("Saved!")