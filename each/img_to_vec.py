import torch
import torchvision.models as models
import torchvision.transforms as transforms


class Img2Vec:

    def __init__(self):

        self.model = models.resnet18(pretrained=True)
        self.layer = self.model._modules.get('avgpool')

        self.model.eval()

        self.scaler = transforms.Resize((224, 224))
        self.normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                              std=[0.229, 0.224, 0.225])
        self.to_tensor = transforms.ToTensor()

    def get_vec(self, img):
        t_img = self.normalize(self.to_tensor(self.scaler(img))).unsqueeze(0)

        embedding = torch.zeros(1, 512, 1, 1)

        def copy_data(m, i, o):
            embedding.copy_(o.data)

        h = self.layer.register_forward_hook(copy_data)
        self.model(t_img)
        h.remove()

        return embedding[0, :, 0, 0]
